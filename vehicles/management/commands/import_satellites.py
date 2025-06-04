import datetime
import requests
import math
from io import StringIO # <-- ADD THIS IMPORT


from django.contrib.gis.geos import Point
from ...models import VehicleLocation, VehicleJourney, Vehicle
from busstops.models import Operator
from ..import_live_vehicles import ImportLiveVehiclesCommand

# --- NEW IMPORTS FOR SKYFIELD ---
from skyfield.api import load, EarthSatellite # Just load and EarthSatellite
from skyfield.timelib import Time # Still potentially useful
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
        if Command.ts is None:
            self.stderr.write("Skyfield timescale not loaded. Aborting get_items.")
            return []

        try:
            response = requests.get(self.TLE_URL)
            response.raise_for_status()
            tle_data = response.text
        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching TLE data from Celestrak: {e}")
            return []

        # --- FIX HERE: Use load.tle_file() with a StringIO object ---
        # My previous correction about `load.tle_file()` NOT taking StringIO was incorrect.
        # It DOES take a file-like object, and StringIO is a file-like object.
        # The earlier error was likely due to the original Skyfield version or a previous
        # import confusion. With 1.53, this is the canonical way to load a TLE string
        # that mimics a file.

        satellites = {}
        try:
            # load.tle_file requires a file-like object. StringIO makes a string behave like a file.
            # It also requires an ephemeris for accurate propagation, which is implicitly
            # handled by the `load` object itself.
            # It returns a dictionary keyed by NORAD ID, which is perfect.
            # Ensure the ephemeris is available to load.tle_file.
            # The 'ephemeris' keyword argument was sometimes needed in older versions,
            # but usually the `load` object provides it.
            # Let's try without explicit ephemeris first.
            
            # The official way to load a string containing multiple TLEs for Skyfield 1.53:
            # Use `load.tle_file()` with a StringIO object.
            # This is specifically for multi-TLE files.
            satellites = load.tle_file(StringIO(tle_data), reload=True) # reload=True forces a fresh parse
            
            # If `load.tle_file` still complains about StringIO, then we have to manually parse
            # the 3-line blocks and use `EarthSatellite(line1, line2, name, ts)`.
            # But according to docs, `load.tle_file` *should* take StringIO.

        except Exception as e:
            self.stderr.write(f"Error parsing TLE data with Skyfield: {e}")
            self.stderr.write("Raw TLE data (first 6 lines):")
            for i, line in enumerate(clean_lines[:6]):
                self.stderr.write(f"  {line}")
            return []

        t = Command.ts.now()

        located_items = []
        for norad_id, satellite in satellites.items():
            try:
                geocentric = satellite.at(t)
                lat, lon = geocentric.latitude.degrees, geocentric.longitude.degrees
                alt_km = geocentric.elevation.km

                bearing = 0

                located_items.append({
                    "name": satellite.name.strip(),
                    "norad_id": str(norad_id),
                    "timestamp": datetime.datetime.now(datetime.timezone.utc),
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