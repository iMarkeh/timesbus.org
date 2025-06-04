import datetime
import requests
import math

from django.contrib.gis.geos import Point
from ...models import VehicleLocation, VehicleJourney, Vehicle
from busstops.models import Operator
from ..import_live_vehicles import ImportLiveVehiclesCommand

# --- NEW IMPORTS FOR SKYFIELD ---
from skyfield.api import load, EarthSatellite
from skyfield.timelib import Time
# --------------------------------

import math # Make sure this is also imported if not already, for latitude/longitude conversion

class Command(ImportLiveVehiclesCommand):
    source_name = "Celestrak" # More accurate name now
    nasa_operator = None
    # Changed the URL for Celestrak TLEs
    TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
    ts = None # Initialize to None when the class is defined

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

        # Initialize Skyfield timescale ONLY if it hasn't been loaded yet
        if Command.ts is None: # Use `is None` for clarity with None checks
            self.stdout.write("Loading Skyfield timescale data...")
            try:
                Command.ts = load.timescale()
                self.stdout.write("Skyfield timescale loaded.")
            except Exception as e:
                self.stderr.write(f"Error loading Skyfield timescale: {e}")
                # You might want to raise an exception or handle this more robustly
                # if timescale is critical, for now, returning empty list in get_items
                # is the fallback.
                return super().do_source() # Continue the super() call to allow cleanup/other tasks
        return super().do_source()

    @staticmethod
    def get_datetime(item):
        # This function is not strictly needed anymore if we calculate position for 'now'
        # but leaving it as a placeholder if you need to calculate for a specific time.
        # For real-time tracking, the 'timestamp' will be `datetime.datetime.now(datetime.timezone.utc)`.
        return item["timestamp"] # Assumed to be a datetime object directly from `get_items`

    def get_vehicle(self, item) -> tuple[Vehicle, bool]:
        # `item` will now contain 'name' and 'norad_id'
        vehicle_code = item["norad_id"]
        defaults = {
            "operator": self.nasa_operator,
            "source": self.source,
            "fleet_code": item["name"],
        }
        return Vehicle.objects.get_or_create(code=vehicle_code, defaults=defaults)

    def get_items(self):
        """
        Fetches TLE data from Celestrak, parses it using Skyfield,
        and calculates the current position for each satellite.
        """
        if not Command.ts:
            self.stderr.write("Skyfield timescale not loaded. Aborting get_items.")
            return []

        try:
            response = requests.get(self.TLE_URL)
            response.raise_for_status()
            tle_data = response.text
        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching TLE data from Celestrak: {e}")
            return []

        lines = tle_data.strip().split('\n')
        # Skyfield's load.tle_file takes a file-like object or a string with multiple TLEs
        # We'll put it into a stringIO object for convenience.
        from io import StringIO
        tle_io = StringIO(tle_data)

        try:
            # Load all satellites from the TLE data using Skyfield
            satellites = load.tle_file(tle_io)
            # satellites will be a dictionary where keys are NORAD IDs
        except Exception as e:
            self.stderr.write(f"Error parsing TLE data with Skyfield: {e}")
            return []

        # Get the current time in Skyfield's timescale
        t = Command.ts.now()

        located_items = []
        for norad_id, satellite in satellites.items():
            try:
                # Get the geographic position (lat, lon, elevation)
                geocentric = satellite.at(t)
                lat, lon = geocentric.latitude.degrees, geocentric.longitude.degrees
                alt_km = geocentric.elevation.km

                # Skyfield's methods for velocity can be used to calculate bearing.
                # For simplicity, let's keep bearing 0 for now unless crucial.
                bearing = 0 # Placeholder: Skyfield can compute this more accurately

                located_items.append({
                    "name": satellite.name.strip(), # Skyfield's satellite object has a name
                    "norad_id": str(norad_id), # Ensure NORAD ID is a string for your model
                    "timestamp": datetime.datetime.now(datetime.timezone.utc), # Use actual capture time
                    "lat": lat,
                    "lon": lon,
                    "altitude_km": alt_km,
                    "line": f"{satellite.name.strip()} Orbital Path",
                    "direction": "ORBITAL",
                    "bearing": bearing,
                })

            except Exception as e:
                self.stderr.write(
                    f"Error calculating position for {satellite.name} (NORAD ID: {norad_id}): {e}"
                )
                continue
        return located_items


    def get_journey(self, item, vehicle):
        journey_datetime = self.get_datetime(item)

        total_seconds_since_epoch = int(journey_datetime.timestamp())
        interval_seconds = 6 * 3600
        block_start_timestamp = (
            total_seconds_since_epoch // interval_seconds
        ) * interval_seconds
        block_start_datetime = datetime.datetime.fromtimestamp(
            block_start_timestamp, datetime.timezone.utc
        )

        route_name = item.get("line", f"{item['name']} Orbit")
        journey_code_prefix = f"SAT-{item['norad_id']}"
        journey_code = f"{journey_code_prefix}-{block_start_datetime.strftime('%Y%m%d%H%M%S')}"

        try:
            journey = VehicleJourney.objects.get(
                vehicle=vehicle,
                datetime=block_start_datetime,
                route_name=route_name,
                code=journey_code
            )
            self.stdout.write(
                f"Reusing existing journey for {item['name']} (NORAD ID: {item['norad_id']}) "
                f"block: {block_start_datetime}"
            )
            return journey
        except VehicleJourney.DoesNotExist:
            journey = VehicleJourney(
                vehicle=vehicle,
                route_name=route_name,
                direction=item.get("direction", "Planetary"),
                datetime=block_start_datetime,
                code=journey_code,
            )
            self.stdout.write(
                f"Creating new journey for {item['name']} (NORAD ID: {item['norad_id']}) "
                f"block: {block_start_datetime}"
            )
            return journey

    def create_vehicle_location(self, item):
        return VehicleLocation(
            latlong=Point(float(item["lon"]), float(item["lat"])),
            heading=item["bearing"],
            # altitude=item.get("altitude_km"), # Uncomment if your model has altitude field
        )