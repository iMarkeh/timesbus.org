import datetime
import requests
from django.contrib.gis.geos import Point
from ...models import VehicleLocation, VehicleJourney, Vehicle
from busstops.models import Operator
from ..import_live_vehicles import ImportLiveVehiclesCommand

# example data returned from eden.apilogic.uk
#{"info":{"satelliteId":25544,"satelliteName":"ISS (ZARYA)"},"positions":[{"latitude":9.238993805727212,"longitude":141.73927582227083,"altitude":415.679606809703,"azimuth":0.0,"elevation":0.0,"ra":172.12053711758603,"dec":9.323420018196797,"timestamp":1755490541}]}

class Command(ImportLiveVehiclesCommand):
    source_name = "APILogic - ISS"
    nasa_operator = None

    def do_source(self):
        self.nasa_operator, created = Operator.objects.get_or_create(
            name="NASA",
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
            response = requests.get("https://eden.apilogic.uk/satellite/25544/positions?api_key=timesbus-vm", timeout=20)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching ISS data: {e}")
            return []

        iss_item = {
            "fn": "ISS",
            "timestamp": data["positions"][0]["timestamp"],
            "lat": data["positions"][0]["latitude"],
            "lon": data["positions"][0]["longitude"],
            "line": "Orbital Path",
            "direction": "Earth",
            "bearing": 0,
        }
        return [iss_item]

    def get_journey(self, item, vehicle):
        journey_datetime = self.get_datetime(item)

        # Calculate the start of the current 6-hour block
        # Normalize the datetime to the nearest 6-hour interval
        # (e.g., 00:00, 06:00, 12:00, 18:00 UTC)
        total_seconds_since_epoch = int(journey_datetime.timestamp())
        # Seconds in 6 hours
        interval_seconds = 24 * 3600
        # Floor to the nearest 24-hour interval
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
            journey.code = f"ISS-{block_start_datetime.strftime('%Y%m%d')}"
            self.stdout.write(
                f"Creating new journey for block: {block_start_datetime}"
            )
            return journey

    def create_vehicle_location(self, item):
        return VehicleLocation(
            latlong=Point(float(item["lon"]), float(item["lat"])),
            heading=item["bearing"],
        )
