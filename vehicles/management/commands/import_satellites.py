from datetime import datetime, timezone

from django.contrib.gis.geos import Point
from django.contrib.gis.geos import GEOSGeometry

from busstops.models import Operator

from ...models import Vehicle, VehicleJourney, VehicleLocation
from ..import_live_vehicles import ImportLiveVehiclesCommand

# Satellites JSON structure:
# [
#   {
#     "info": {
#       "satelliteId": 64881,
#       "satelliteName": "239ALFEROV (RS61S)"
#     },
#     "position": {
#       "latitude": -26.0101812663403,
#       "longitude": 110.982326764123,
#       "altitude": 504.399517339751,
#       "azimuth": 0,
#       "elevation": 0,
#       "ra": 10.8077086979108,
#       "dec": -26.0109030581651,
#       "timestamp": 1755459290
#     }
#   }
# ]


def parse_timestamp(timestamp):
    if timestamp:
        return datetime.fromtimestamp(int(timestamp), timezone.utc)


class Command(ImportLiveVehiclesCommand):
    source_name = "Satellites"
    previous_locations = {}

    def do_source(self):
        # Get the DataSource named "Satellites" - it should already exist
        try:
            from busstops.models import DataSource
            self.source = DataSource.objects.get(name=self.source_name)
            if self.source.url:
                self.url = self.source.url
        except DataSource.DoesNotExist:
            raise Exception(f'DataSource named "{self.source_name}" does not exist. Please create it first.')

        self.operator, created = Operator.objects.get_or_create(
            noc="NASA",
            defaults={
                "name": "NASA"
            }
        )
        if created:
            self.stdout.write(f"Created operator: {self.operator}")

        return self

    @staticmethod
    def get_datetime(item):
        return parse_timestamp(item["position"]["timestamp"])

    def prefetch_vehicles(self, vehicle_codes):
        vehicles = self.vehicles.filter(
            operator=self.operator, code__in=vehicle_codes
        )
        self.vehicle_cache = {vehicle.code: vehicle for vehicle in vehicles}

    def get_items(self):
        items = []
        vehicle_codes = []

        try:
            # Get the raw satellite data (should be a list)
            raw_data = super().get_items()

            # Handle case where data might be wrapped in an object
            if isinstance(raw_data, dict) and 'satellites' in raw_data:
                satellite_list = raw_data['satellites']
            elif isinstance(raw_data, list):
                satellite_list = raw_data
            else:
                self.stderr.write(f"Unexpected data format: {type(raw_data)}")
                return []

            # Build list of satellites that have moved
            for item in satellite_list:
                if not isinstance(item, dict) or 'info' not in item or 'position' not in item:
                    self.stderr.write(f"Skipping invalid satellite item: {item}")
                    continue

                try:
                    satellite_id = str(item["info"]["satelliteId"])
                    position = item["position"]

                    # Validate required position fields
                    required_fields = ["timestamp", "latitude", "longitude"]
                    if not all(field in position for field in required_fields):
                        self.stderr.write(f"Skipping satellite {satellite_id}: missing position fields")
                        continue

                    # Create a unique key for tracking movement
                    key = satellite_id
                    value = (
                        position["timestamp"],
                        round(position["latitude"], 6),  # Round to avoid tiny movements
                        round(position["longitude"], 6),
                        round(position.get("altitude", 0), 1)
                    )

                    if self.previous_locations.get(key) != value:
                        items.append(item)
                        vehicle_codes.append(satellite_id)
                        self.previous_locations[key] = value

                except (KeyError, ValueError, TypeError) as e:
                    self.stderr.write(f"Error processing satellite item: {e}")
                    continue

            self.prefetch_vehicles(vehicle_codes)

            if items:
                self.stdout.write(f"Processing {len(items)} satellite updates")

            return items

        except Exception as e:
            self.stderr.write(f"Error in get_items: {e}")
            return []

    def get_vehicle(self, item) -> tuple[Vehicle, bool]:
        try:
            satellite_id = str(item["info"]["satelliteId"])
            satellite_name = item["info"]["satelliteName"]

            # Check if vehicle exists in cache
            if satellite_id in self.vehicle_cache:
                vehicle = self.vehicle_cache[satellite_id]
                return vehicle, False

            # Try to find existing vehicle
            vehicle = Vehicle.objects.filter(
                operator=self.space_operator,
                code=satellite_id
            ).first()

            if vehicle:
                self.vehicle_cache[satellite_id] = vehicle
                # Update name if it has changed
                if vehicle.name != satellite_name:
                    vehicle.name = satellite_name
                    vehicle.notes = f"Satellite: {satellite_name}"
                    vehicle.save(update_fields=['name', 'notes'])
                return vehicle, False

            # Create new vehicle for this satellite
            vehicle = Vehicle.objects.create(
                operator=self.space_operator,
                source=self.source,
                code=satellite_id,
                fleet_code=satellite_id,
                name=satellite_name,
                notes=f"Satellite: {satellite_name}"
            )

            self.vehicle_cache[satellite_id] = vehicle
            self.stdout.write(f"Created satellite vehicle: {satellite_id} - {satellite_name}")
            return vehicle, True

        except (KeyError, ValueError) as e:
            self.stderr.write(f"Error getting vehicle from item: {e}")
            return None, False

    def get_journey(self, item, vehicle):
        try:
            journey_datetime = self.get_datetime(item)

            # For satellites, we'll create journeys based on orbital periods
            # Use a simplified approach: one journey per day
            journey_date = journey_datetime.date()

            # Try to find existing journey for this date
            existing_journey = vehicle.vehiclejourney_set.filter(
                datetime__date=journey_date
            ).first()

            if existing_journey:
                return existing_journey

            # Create new journey for this orbital period
            journey = VehicleJourney(
                datetime=journey_datetime.replace(hour=0, minute=0, second=0, microsecond=0),
                destination="Orbit",
                route_name="Orbit",
                code=f"{vehicle.code}_{journey_date.strftime('%Y%m%d')}"
            )

            return journey

        except Exception as e:
            self.stderr.write(f"Error creating journey for vehicle {vehicle.code}: {e}")
            # Return a basic journey as fallback
            return VehicleJourney(
                datetime=self.get_datetime(item),
                destination="Orbit",
                route_name="Orbit"
            )
    def create_vehicle_location(self, item):
        return VehicleLocation(
            latlong=GEOSGeometry(f"POINT({item['lo']} {item['la']})"),
            heading=item.get("hg"),
        )
    def create_vehicle_location(self, item):
        try:
            position = item["position"]

            # Validate coordinates
            longitude = float(position["longitude"])
            latitude = float(position["latitude"])

            if not (-180 <= longitude <= 180):
                self.stderr.write(f"Invalid longitude: {longitude}")
                return None

            if not (-90 <= latitude <= 90):
                self.stderr.write(f"Invalid latitude: {latitude}")
                return None

            return VehicleLocation(
                latlong=Point(longitude, latitude),
                heading=position.get("azimuth", 0),
                # Could store altitude in a custom field if available
                # altitude=position.get("altitude", 0)
            )

        except (KeyError, ValueError, TypeError) as e:
            self.stderr.write(f"Error creating vehicle location: {e}")
            return None
