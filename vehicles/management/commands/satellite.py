import datetime
from django.contrib.gis.geos import Point
from ...models import VehicleLocation, VehicleJourney, Vehicle
from busstops.models import Operator
from ..import_live_vehicles import ImportLiveVehiclesCommand
from vehicles.models import Vehicle
from skyfield.api import EarthSatellite, load
import requests
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db import IntegrityError

class Command(ImportLiveVehiclesCommand):
    help = "Import live satellite data from Celestrak"
    source_name = "NASA"
    tle_url = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"

    def get_items(self):
        response = requests.get(self.tle_url, timeout=20)
        response.raise_for_status()
        lines = response.text.strip().splitlines()

        ts = load.timescale()
        now = datetime.datetime.utcnow()
        sf_time = ts.utc(now.year, now.month, now.day, now.hour, now.minute, now.second)

        items = []

        for i in range(0, len(lines), 3):
            name = lines[i].strip()
            line1 = lines[i + 1].strip()
            line2 = lines[i + 2].strip()

            try:
                sat = EarthSatellite(line1, line2, name, ts)
                geocentric = sat.at(sf_time)
                subpoint = geocentric.subpoint()
                lat = subpoint.latitude.degrees
                lon = subpoint.longitude.degrees

                # extract NORAD catalog number from line1 positions 2-7
                etm_code = line1[2:7].strip()

                items.append({
                    "timestamp": now.timestamp(),
                    "lat": lat,
                    "lon": lon,
                    "fn": etm_code,  # use NORAD ID as fleet number
                    "name": name,
                    "line": "Orbit",
                    "direction": "Earth",
                    "bearing": 0,
                })
            except Exception as e:
                self.stderr.write(f"Error propagating {name}: {e}")
        return items

    def get_datetime(self, item):
        return datetime.datetime.fromtimestamp(item["timestamp"], datetime.timezone.utc)

    def get_vehicle(self, item):
        operator, _ = Operator.objects.get_or_create(
            name="NASA",
            defaults={"code": "NASA", "noc": "NASA"},
        )
        vehicle, created = Vehicle.objects.get_or_create(
            reg=item["fn"],
            defaults={
                "operator": operator,
                "code": item["fn"],  # NORAD ID as code too
            },
        )
        return vehicle, created

    def get_journey(self, item, vehicle):
        journey_datetime = self.get_datetime(item)
        satname = item.get("name")
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
                direction=item.get("direction", "Earth"),
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
            journey.code = f"{satname}-{block_start_datetime.strftime('%Y%m%d')}"
            self.stdout.write(
                f"Creating new journey for block: {block_start_datetime}"
            )
            return journey

    def create_vehicle_location(self, item):
        latitude = item.get("lat")
        longitude = item.get("lon")
        bearing = item.get("bearing")

        if latitude is None or longitude is None:
            self.stdout.write(f"Missing coordinates for item: {item}")
            return None

        return VehicleLocation(
            latlong=Point(float(longitude), float(latitude)),
            heading=item["bearing"],
        )
