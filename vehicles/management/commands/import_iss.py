import datetime
import requests
from django.contrib.gis.geos import Point
from ...models import VehicleLocation, VehicleJourney, Vehicle
from busstops.models import Operator, DataSource
from ..import_live_vehicles import ImportLiveVehiclesCommand


class Command(ImportLiveVehiclesCommand):
    self.source = DataSource.objects.get(name="APILogic - ISS")
    nasa_operator = None

    def do_source(self):
        self.nasa_operator, created = Operator.objects.get_or_create(
            name="NASA",
            source=self.source,
            defaults={
                "code": "NASA",
                "noc": "NASA",
            },
        )
        if created:
            self.stdout.write("Created Operator: NASA")
        else:
            self.stdout.write("Found Operator: NASA")

        return super().do_source()

    @staticmethod
    def get_datetime(item):
        return datetime.datetime.fromtimestamp(item["timestamp"], datetime.timezone.utc)

    def get_vehicle(self, item) -> tuple[Vehicle, bool]:
        vehicle_code = item["fn"]
        defaults = {
            "operator": self.nasa_operator,
            "source": self.source,
            "fleet_code": vehicle_code,
        }
        return Vehicle.objects.get_or_create(code=vehicle_code, defaults=defaults)
        self.stdout.write("Vehicle Fetched")

    def get_items(self):
        try:
            response = requests.get("https://tb.apilogic.uk/tracking/iss/position.asmx" headers=)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching ISS data: {e}")
            return []

        iss_item = {
            "fn": "ISS",
            "timestamp": data["timestamp"],
            "lat": data["latitude"],
            "lon": data["longitude"],
            "line": "Orbital Path",
            "direction": "Earth",
            "bearing": 0,
        }
        return [iss_item]

    def get_journey(self, item, vehicle):
        journey_datetime = self.get_datetime(item)

        # --- MODIFICATION START ---
        # Calculate the start of the current 6-hour block
        # Normalize the datetime to the nearest 6-hour interval
        # (e.g., 00:00, 06:00, 12:00, 18:00 UTC)
        total_seconds_since_epoch = int(journey_datetime.timestamp())
        # Seconds in 6 hours
        interval_seconds = 6 * 3600
        # Floor to the nearest 6-hour interval
        block_start_timestamp = (
            total_seconds_since_epoch // interval_seconds
        ) * interval_seconds
        block_start_datetime = datetime.datetime.fromtimestamp(
            block_start_timestamp, datetime.timezone.utc
        )

        # Try to find an existing journey for this exact 6-hour block start time
        # This acts as a unique identifier for each journey segment.
        try:
            journey = VehicleJourney.objects.get(
                vehicle=vehicle,
                datetime=block_start_datetime,
                route_name=item.get("line", "Orbit"),
            )
            self.stdout.write(
                f"Reusing existing journey for block: {block_start_datetime}"
            )
            return journey
        except VehicleJourney.DoesNotExist:
            # If no journey exists for this block, create a new one
            journey = VehicleJourney(
                vehicle=vehicle,
                route_name=item.get("line", "Orbit"),
                direction=item.get("direction", "Earth"),
                datetime=block_start_datetime,  # Use the block start time
            )
            # You might also want to set a unique code for the journey based on the block start
            journey.code = f"ISS-{block_start_datetime.strftime('%Y%m%d%H%M%S')}"
            self.stdout.write(
                f"Creating new journey for block: {block_start_datetime}"
            )
            return journey
        # --- MODIFICATION END ---

    def create_vehicle_location(self, item):
        return VehicleLocation(
            latlong=Point(float(item["lon"]), float(item["lat"])),
            heading=item["bearing"],
        )