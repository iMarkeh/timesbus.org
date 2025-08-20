import requests
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

    # API configuration - using the same API as import_iss.py
    API_BASE_URL = "https://kolas.apilogic.uk"
    API_KEY = "v1.public.03b5bq5obzueg2xfd5zw3ac"

    # Popular satellites to track (NORAD IDs)
    # This is a curated list of interesting satellites - you can expand this
    SATELLITE_IDS = [
        25544,  # ISS (ZARYA)
        20580,  # HUBBLE SPACE TELESCOPE
        43013,  # STARLINK-1007
        43070,  # STARLINK-1130
        43071,  # STARLINK-1131
        43072,  # STARLINK-1132
        43073,  # STARLINK-1133
        43074,  # STARLINK-1134
        43075,  # STARLINK-1135
        43076,  # STARLINK-1136
        43077,  # STARLINK-1137
        43078,  # STARLINK-1138
        43079,  # STARLINK-1139
        43080,  # STARLINK-1140
        43081,  # STARLINK-1141
        43082,  # STARLINK-1142
        43083,  # STARLINK-1143
        43084,  # STARLINK-1144
        43085,  # STARLINK-1145
        43086,  # STARLINK-1146
        43087,  # STARLINK-1147
        43088,  # STARLINK-1148
        43089,  # STARLINK-1149
        43090,  # STARLINK-1150
        43091,  # STARLINK-1151
        43092,  # STARLINK-1152
        43093,  # STARLINK-1153
        43094,  # STARLINK-1154
        43095,  # STARLINK-1155
        43096,  # STARLINK-1156
        43097,  # STARLINK-1157
        43098,  # STARLINK-1158
        43099,  # STARLINK-1159
        43100,  # STARLINK-1160
        # Add more satellite IDs as needed
        # You can get a full list from https://celestrak.com/NORAD/elements/
    ]

    @staticmethod
    def add_arguments(parser):
        parser.add_argument(
            '--fetch-catalog',
            action='store_true',
            help='Fetch satellite IDs from online catalog (gets 11k+ satellites)'
        )
        parser.add_argument(
            '--max-satellites',
            type=int,
            default=100,
            help='Maximum number of satellites to process (default: 100)'
        )
        ImportLiveVehiclesCommand.add_arguments(parser)

    def handle(self, **options):
        self.fetch_catalog = options.get('fetch_catalog', False)
        self.max_satellites = options.get('max_satellites', 100)

        if self.fetch_catalog:
            self.stdout.write("Fetching satellite catalog...")
            self.SATELLITE_IDS = self.get_satellite_catalog()

        # Limit the number of satellites to process
        if len(self.SATELLITE_IDS) > self.max_satellites:
            self.stdout.write(f"Limiting to {self.max_satellites} satellites (out of {len(self.SATELLITE_IDS)} available)")
            self.SATELLITE_IDS = self.SATELLITE_IDS[:self.max_satellites]

        super().handle(**options)

    def get_satellite_catalog(self):
        """Fetch a list of active satellites from Celestrak or similar source"""
        try:
            # Try to get active satellites from Celestrak
            catalog_urls = [
                "https://celestrak.com/NORAD/elements/gp.php?GROUP=stations&FORMAT=json",
                "https://celestrak.com/NORAD/elements/gp.php?GROUP=starlink&FORMAT=json",
                "https://celestrak.com/NORAD/elements/gp.php?GROUP=oneweb&FORMAT=json",
                "https://celestrak.com/NORAD/elements/gp.php?GROUP=kuiper&FORMAT=json",
                "https://celestrak.com/NORAD/elements/gp.php?GROUP=eutelsat&FORMAT=json",
                "https://celestrak.com/NORAD/elements/gp.php?GROUP=intelsat&FORMAT=json",
            ]

            all_satellite_ids = []

            for url in catalog_urls:
                try:
                    self.stdout.write(f"Fetching from {url}")
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    data = response.json()

                    if isinstance(data, list):
                        for sat in data:
                            if isinstance(sat, dict) and 'NORAD_CAT_ID' in sat:
                                all_satellite_ids.append(int(sat['NORAD_CAT_ID']))

                except requests.exceptions.RequestException as e:
                    self.stderr.write(f"Error fetching from {url}: {e}")
                    continue

            # Remove duplicates and sort
            unique_ids = sorted(list(set(all_satellite_ids)))
            self.stdout.write(f"Found {len(unique_ids)} satellites in catalog")

            return unique_ids if unique_ids else self.SATELLITE_IDS

        except Exception as e:
            self.stderr.write(f"Error fetching satellite catalog: {e}")
            self.stdout.write("Falling back to default satellite list")
            return self.SATELLITE_IDS

    def do_source(self):
        # Get the DataSource named "Satellites" - it should already exist
        try:
            from busstops.models import DataSource
            self.source = DataSource.objects.get(name=self.source_name)
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

        self.stdout.write(f"Fetching data for {len(self.SATELLITE_IDS)} satellites...")

        # Fetch data for each satellite individually using the same API as import_iss.py
        for satellite_id in self.SATELLITE_IDS:
            try:
                url = f"{self.API_BASE_URL}/satellite/{satellite_id}/positions?api_key={self.API_KEY}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()

                # Check if we got valid data
                if not data.get("positions") or len(data["positions"]) == 0:
                    self.stderr.write(f"No position data for satellite {satellite_id}")
                    continue

                # Get the latest position
                position = data["positions"][0]
                satellite_info = data.get("info", {})

                # Create a unique key for tracking movement
                key = str(satellite_id)
                value = (
                    position["timestamp"],
                    round(position["latitude"], 6),  # Round to avoid tiny movements
                    round(position["longitude"], 6),
                    round(position.get("altitude", 0), 1)
                )

                # Only process if satellite has moved
                if self.previous_locations.get(key) != value:
                    # Convert to the format expected by the rest of the code
                    item = {
                        "info": {
                            "satelliteId": satellite_id,
                            "satelliteName": satellite_info.get("satelliteName", f"SATELLITE-{satellite_id}")
                        },
                        "position": {
                            "timestamp": position["timestamp"],
                            "latitude": position["latitude"],
                            "longitude": position["longitude"],
                            "altitude": position.get("altitude", 0),
                            "azimuth": position.get("azimuth", 0),
                            "elevation": position.get("elevation", 0),
                            "ra": position.get("ra", 0),
                            "dec": position.get("dec", 0)
                        }
                    }

                    items.append(item)
                    vehicle_codes.append(str(satellite_id))
                    self.previous_locations[key] = value

            except requests.exceptions.RequestException as e:
                self.stderr.write(f"Error fetching data for satellite {satellite_id}: {e}")
                continue
            except (KeyError, ValueError, TypeError) as e:
                self.stderr.write(f"Error processing satellite {satellite_id}: {e}")
                continue

        self.prefetch_vehicles(vehicle_codes)

        if items:
            self.stdout.write(f"Processing {len(items)} satellite updates out of {len(self.SATELLITE_IDS)} satellites")
        else:
            self.stdout.write("No satellite updates to process")

        return items

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
                operator=self.operator,
                code=satellite_id
            ).first()

            if vehicle:
                self.vehicle_cache[satellite_id] = vehicle
                # Update name if it has changed
                if vehicle.name != satellite_name:
                    vehicle.name = satellite_name
                    vehicle.notes = f"NORAD ID: {satellite_name}"
                    vehicle.save(update_fields=['name', 'notes'])
                return vehicle, False

            # Create new vehicle for this satellite
            vehicle = Vehicle.objects.create(
                operator=self.operator,
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
        position = item["position"]
        return VehicleLocation(
            latlong=GEOSGeometry(f"POINT({position['longitude']} {position['latitude']})"),
            heading=position.get("azimuth"),
        )
