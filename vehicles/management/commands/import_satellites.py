import datetime
import requests
import math
from io import StringIO

from django.contrib.gis.geos import Point
from ...models import VehicleLocation, VehicleJourney, Vehicle
from busstops.models import Operator
from ..import_live_vehicles import ImportLiveVehiclesCommand

# --- NEW IMPORTS FOR SKYFIELD ---
from skyfield.api import load, EarthSatellite
from skyfield.timelib import Time
# --------------------------------

class Command(ImportLiveVehiclesCommand):
    source_name = "Space Station Group (Skyfield)"
    nasa_operator = None
    TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"

    # Initialize Skyfield's TimeScale as a class attribute
    ts = None

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
        if Command.ts is None:
            self.stdout.write("Loading Skyfield timescale data...")
            try:
                # Skyfield needs a timescale object, which loads data files.
                # This can take a moment the first time it runs and downloads.
                Command.ts = load.timescale()
                self.stdout.write("Skyfield timescale loaded.")
            except Exception as e:
                self.stderr.write(f"Error loading Skyfield timescale: {e}")
                # If timescale cannot be loaded, further operations will fail.
                # Returning from here will prevent get_items from being called.
                return super().do_source()

        # This calls the parent do_source which in turn calls self.update()
        # and then self.get_items() etc.
        return super().do_source()

    @staticmethod
    def get_datetime(item):
        """
        Returns the datetime object associated with the item's timestamp.
        Assumes item["timestamp"] is already a datetime object from get_items.
        """
        return item["timestamp"]

    def get_vehicle(self, item) -> tuple[Vehicle, bool]:
        """
        Retrieves or creates a Vehicle object based on the satellite's NORAD ID.
        """
        vehicle_code = str(item["norad_id"]) # Ensure NORAD ID is a string for code field
        defaults = {
            "operator": self.nasa_operator,
            "source": self.source,
            "fleet_code": item["name"], # Use satellite name for fleet_code
        }
        # Get or create the Vehicle, linking it to our 'NASA' operator
        return Vehicle.objects.get_or_create(code=vehicle_code, defaults=defaults)

    def get_items(self):
        """
        Fetches TLE data from Celestrak, parses it manually,
        and calculates the current position for each satellite using Skyfield.
        """
        # Ensure timescale is loaded before attempting satellite propagation
        if Command.ts is None:
            self.stderr.write("Skyfield timescale not loaded. Aborting get_items.")
            return []

        tle_data = "" # Initialize here to ensure it's defined for the except block
        try:
            # Fetch TLE data from Celestrak URL
            response = requests.get(self.TLE_URL)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            tle_data = response.text
        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching TLE data from Celestrak: {e}")
            return []

        # Split the raw TLE string into individual lines and clean them
        lines = tle_data.strip().split('\n')
        clean_lines = [line.strip() for line in lines if line.strip()]

        satellites = {}
        # TLE data is always in 3-line blocks: Satellite Name, TLE Line 1, TLE Line 2
        # We need to process these lines in chunks of 3.
        if len(clean_lines) % 3 != 0:
            self.stderr.write("Warning: TLE data does not have an even number of 3-line blocks. Some data might be incomplete or skipped.")
            self.stderr.write("Partial TLE data leading to the issue (last 6 lines):")
            for i, line in enumerate(clean_lines[-6:]): # Print last few lines for context
                self.stderr.write(f"  {line}")

        # Iterate through the cleaned lines, processing 3 lines at a time
        for i in range(0, len(clean_lines), 3):
            if i + 2 < len(clean_lines): # Ensure we have a full 3-line block (Name, Line1, Line2)
                name = clean_lines[i]
                line1 = clean_lines[i+1]
                line2 = clean_lines[i+2]

                try:
                    # Construct EarthSatellite object directly using its constructor
                    # EarthSatellite(line1, line2, name=None, ts=None)
                    satellite = EarthSatellite(line1, line2, name, Command.ts)
                    # Store the satellite object in a dictionary, keyed by its NORAD ID
                    # This ensures consistency with Skyfield's load.tle_file return format.
                    satellites[satellite.model.satnum] = satellite
                except Exception as e:
                    self.stderr.write(f"Error creating EarthSatellite for '{name}' (lines {i}-{i+2}): {e}")
                    # Print the problematic lines for easier debugging of TLE format issues
                    self.stderr.write(f"  Line1: {line1}")
                    self.stderr.write(f"  Line2: {line2}")
                    continue # Skip this satellite block and attempt to process the next one

        # If no satellites were successfully parsed, return an empty list
        if not satellites:
            self.stderr.write("No satellites successfully parsed from TLE data. Returning empty list.")
            return []

        # Get the current time in Skyfield's internal timescale for propagation
        t = Command.ts.now()
        # please?
        current_datetime_utc = datetime.datetime.now(datetime.timezone.utc)
        located_items = []
        # Iterate through the parsed satellite objects to get their current positions
        for norad_id, satellite in satellites.items():
            try:
                # Propagate the satellite to the current time 't'
                geocentric = satellite.at(t)
                
                # Convert the Geocentric (Earth-centered Cartesian) coordinates
                # to Geographic (latitude, longitude, elevation) coordinates.
                geographic = geocentric.subpoint()

                # Extract latitude and longitude in degrees from the geographic object
                lat, lon = geographic.latitude.degrees, geographic.longitude.degrees
                # Extract altitude in kilometers from the geographic object
                alt_km = geographic.elevation.km

                # Bearing calculation is complex with just position, typically requires
                # velocity vector or a second point. Setting to 0 for simplicity.
                bearing = 0 # Placeholder for bearing, consider adding advanced calculation if needed

                # Create a dictionary item formatted for your Django models
                located_items.append({
                    "name": satellite.name.strip(), # Get satellite name and clean whitespace
                    "norad_id": str(norad_id),     # Convert NORAD ID to string
                    "timestamp": current_datetime_utc.isoformat(), # Use actual capture time UTC
                    "lat": lat,
                    "lon": lon,
                    "altitude_km": alt_km,         # Include altitude if your VehicleLocation model supports it
                    "line": f"{satellite.name.strip()} Orbital Path", # Dynamic line name based on satellite name
                    "direction": "ORBITAL",        # Consistent direction
                    "bearing": bearing,            # Bearing
                })

            except Exception as e:
                self.stderr.write(
                    f"Error calculating position for {satellite.name} (NORAD ID: {norad_id}): {e}"
                )
                continue # Skip this satellite if position calculation fails

        return located_items

    def get_journey(self, item, vehicle):
        """
        Retrieves or creates a VehicleJourney object for the satellite's current 6-hour block.
        This groups continuous tracking data into logical journeys.
        """
        journey_datetime = self.get_datetime(item)

        # Calculate the start of the current 6-hour block in UTC
        # Normalize the datetime to the nearest 6-hour interval (e.g., 00:00, 06:00, 12:00, 18:00 UTC)
        total_seconds_since_epoch = int(journey_datetime.timestamp())
        interval_seconds = 6 * 3600 # Seconds in 6 hours
        # Floor to the nearest 6-hour interval
        block_start_timestamp = (
            total_seconds_since_epoch // interval_seconds
        ) * interval_seconds
        block_start_datetime = datetime.datetime.fromtimestamp(
            block_start_timestamp, datetime.timezone.utc
        )

        # Use the satellite's name and NORAD ID to create a unique route name and journey code
        route_name = item.get("line", f"{item['name']} Orbit")
        journey_code_prefix = f"SAT-{item['norad_id']}"
        journey_code = f"{journey_code_prefix}-{block_start_datetime.strftime('%Y%m%d%H%M%S')}"

        try:
            # Try to find an existing journey for this exact 6-hour block and vehicle
            journey = VehicleJourney.objects.get(
                vehicle=vehicle,
                datetime=block_start_datetime, # Using the block start time for lookup
                route_name=route_name,
                code=journey_code # Use the unique code for lookup
            )
            self.stdout.write(
                f"Reusing existing journey for {item['name']} (NORAD ID: {item['norad_id']}) "
                f"for block: {block_start_datetime}"
            )
            return journey
        except VehicleJourney.DoesNotExist:
            # If no journey exists for this block, create a new one
            journey = VehicleJourney(
                vehicle=vehicle,
                route_name=route_name,
                direction=item.get("direction", "Planetary"), # Default direction
                datetime=block_start_datetime, # Use the block start time as the journey's start time
                code=journey_code, # Set the unique journey code
            )
            self.stdout.write(
                f"Creating new journey for {item['name']} (NORAD ID: {item['norad_id']}) "
                f"for block: {block_start_datetime}"
            )
            return journey

    def create_vehicle_location(self, item):
        """
        Creates a VehicleLocation object from the item data.
        """
        # Create a Django Point object from longitude and latitude
        # --- FIX HERE: REMOVE THE TRAILING COMMA ---
        latlong_point = Point(float(item["lon"]), float(item["lat"]))
        # -------------------------------------------
        
        vehicle_location = VehicleLocation(
            latlong=latlong_point,
            heading=item["bearing"], # This will be 0 for now based on current logic
            # If your VehicleLocation model has an 'altitude' field (e.g., DecimalField or FloatField)
            # you can uncomment the line below. Make sure the model supports it.
            # altitude=item.get("altitude_km"),
        )
        return vehicle_location