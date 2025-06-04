import datetime
import requests
import math

from django.contrib.gis.geos import Point
from ...models import VehicleLocation, VehicleJourney, Vehicle
from busstops.models import Operator
from ..import_live_vehicles import ImportLiveVehiclesCommand

# Definitive SGP4 imports for sgp4 version 2.24
from sgp4.api import WGS72, jday # jday and WGS72 are stable here
from sgp4 import exporter # This is the key change for twoline2rv

import math # Make sure this is also imported if not already, for latitude/longitude conversion

class Command(ImportLiveVehiclesCommand):
    source_name = "Celestrak" # More accurate name now
    nasa_operator = None
    # Changed the URL for Celestrak TLEs
    TLE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"

    def do_source(self):
        # Operator handling remains the same
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
        # This function is not strictly needed anymore if we calculate position for 'now'
        # but leaving it as a placeholder if you need to calculate for a specific time.
        # For real-time tracking, the 'timestamp' will be `datetime.datetime.now(datetime.timezone.utc)`.
        return item["timestamp"] # Assumed to be a datetime object directly from `get_items`

    def get_vehicle(self, item) -> tuple[Vehicle, bool]:
        # `item` will now contain 'name' and 'norad_id'
        # Use a unique identifier for the vehicle code, NORAD ID is perfect.
        vehicle_code = item["norad_id"]
        defaults = {
            "operator": self.nasa_operator,
            "source": self.source,
            "fleet_code": item["name"], # Use satellite name for fleet_code
        }
        return Vehicle.objects.get_or_create(code=vehicle_code, defaults=defaults)

    def get_items(self):
        """
        Fetches TLE data from Celestrak, parses it, and calculates the current
        position for each satellite.
        """
        try:
            response = requests.get(self.TLE_URL)
            response.raise_for_status()
            tle_data = response.text
        except requests.exceptions.RequestException as e:
            self.stderr.write(f"Error fetching TLE data from Celestrak: {e}")
            return []

        # Parse the TLE data
        lines = tle_data.strip().split('\n')
        # TLEs come in blocks of 3 lines: Name, Line1, Line2
        # So we process them 3 lines at a time
        tle_records = []
        for i in range(0, len(lines), 3):
            if i + 2 < len(lines):
                name = lines[i].strip()
                line1 = lines[i+1].strip()
                line2 = lines[i+2].strip()

                try:
                    # Create a Satellite object from the TLE lines
                    satellite = exporter.twoline2rv(line1, line2)
                    tle_records.append({
                        "name": name,
                        "norad_id": satellite.satnum, # NORAD ID is part of the satrec object
                        "satellite": satellite
                    })
                except ValueError as e:
                    self.stderr.write(f"Error parsing TLE for {name}: {e}")
                    continue

        current_time_utc = datetime.datetime.now(datetime.timezone.utc)
        # Use jday directly, passing year, month, day, hour, minute, second
        jd, fr = jday(
            current_time_utc.year,
            current_time_utc.month,
            current_time_utc.day,
            current_time_utc.hour,
            current_time_utc.minute,
            current_time_utc.second + current_time_utc.microsecond / 1_000_000
        )

        located_items = []
        for record in tle_records:
            try:
                # Propagate the satellite to the current time
                e_val, r_val, v_val = record["satellite"].sgp4(jd, fr)

                # r_val contains x, y, z ECI coordinates in kilometers
                # Convert ECI to ECEF (latitude, longitude, altitude)
                # The WGS72 model gives geocentric latitude, SGP4 typically works with this.
                # If you need geodetic latitude, you'd need a more complex conversion.
                # For basic tracking and plotting, WGS72 lat/lon is often sufficient.
                lat_rad = WGS72.atime.radians(r_val[0], r_val[1], r_val[2], jd, fr)[0]
                lon_rad = WGS72.atime.radians(r_val[0], r_val[1], r_val[2], jd, fr)[1]
                alt_km = WGS72.atime.radians(r_val[0], r_val[1], r_val[2], jd, fr)[2] / 1000 # convert m to km for consistency

                # Convert radians to degrees
                lat_deg = lat_rad * (180.0 / math.pi)
                lon_deg = lon_rad * (180.0 / math.pi)

                # SGP4 often returns longitude in the range [-180, 180] or [0, 360].
                # Ensure it's within standard mapping ranges, though Django's Point handles it.

                # Calculate bearing (optional but good for visuals)
                # This is a simplification; a true bearing calculation requires
                # knowing the previous position or using orbital mechanics formulas.
                # For a rough estimate, you could calculate based on velocity vector or
                # simply set to 0 if not critical for your use case.
                # For now, let's keep it simple.
                bearing = 0 # Placeholder: More complex to calculate with SGP4 directly without a second point.

                located_items.append({
                    "name": record["name"],
                    "norad_id": record["norad_id"],
                    "timestamp": current_time_utc, # Use the actual time of propagation
                    "lat": lat_deg,
                    "lon": lon_deg,
                    "altitude_km": alt_km,
                    "line": f"{record['name']} Orbital Path", # Dynamic line name
                    "direction": "ORBITAL",
                    "bearing": bearing, # Can be refined later
                })

            except Exception as e:
                self.stderr.write(
                    f"Error calculating position for {record['name']} (NORAD ID: {record['norad_id']}): {e}"
                )
                continue
        return located_items


    def get_journey(self, item, vehicle):
        # The journey logic for 6-hour blocks is good.
        # We need to adapt it to use the satellite's NORAD ID and Name.
        journey_datetime = self.get_datetime(item) # This will be the current_time_utc from get_items

        # Calculate the start of the current 6-hour block
        total_seconds_since_epoch = int(journey_datetime.timestamp())
        interval_seconds = 6 * 3600
        block_start_timestamp = (
            total_seconds_since_epoch // interval_seconds
        ) * interval_seconds
        block_start_datetime = datetime.datetime.fromtimestamp(
            block_start_timestamp, datetime.timezone.utc
        )

        # Use NORAD ID as part of the unique identifier for the journey
        route_name = item.get("line", f"{item['name']} Orbit")
        journey_code_prefix = f"SAT-{item['norad_id']}"
        journey_code = f"{journey_code_prefix}-{block_start_datetime.strftime('%Y%m%d%H%M%S')}"

        try:
            journey = VehicleJourney.objects.get(
                vehicle=vehicle,
                datetime=block_start_datetime, # Block start time
                route_name=route_name,
                code=journey_code # Use the unique code for lookup
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
                datetime=block_start_datetime, # Use the block start time
                code=journey_code, # Set the unique code
            )
            self.stdout.write(
                f"Creating new journey for {item['name']} (NORAD ID: {item['norad_id']}) "
                f"block: {block_start_datetime}"
            )
            return journey

    def create_vehicle_location(self, item):
        # Create VehicleLocation using lat/lon from the item
        return VehicleLocation(
            latlong=Point(float(item["lon"]), float(item["lat"])),
            heading=item["bearing"], # This will be 0 for now, but can be improved
            # You might want to store altitude if your model supports it
            # altitude=item.get("altitude_km"),
        )