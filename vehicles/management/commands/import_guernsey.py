import datetime
import logging
from django.contrib.gis.geos import Point
from ..import_live_vehicles import ImportLiveVehiclesCommand
from ...models import VehicleLocation, VehicleJourney

logger = logging.getLogger(__name__)


class Command(ImportLiveVehiclesCommand):
    source_name = "Guernsey"  # Updated source name
    operator = "SGUE"  # Updated operator
    url = "https://api.timesbus.org/tracking/guernsey?api_key=timesbus-vm"  # Updated API URL

    @staticmethod
    def get_datetime(item):
        # Use the 'reported' field for the vehicle location time
        reported_time_str = item.get("reported")
        if reported_time_str:
            # datetime.fromisoformat can handle this
            return datetime.datetime.fromisoformat(
                reported_time_str.replace("Z", "+00:00")
            )
        logger.warning(
            "Missing 'reported' field, falling back to current time."
        )  # Log if falling back
        return datetime.datetime.now(
            datetime.timezone.utc
        )  # Fallback to now if reported is not available

    def get_vehicle(self, item):
        # The new API has both "vehicleId" (a UUID) and "vehicleRef" (the number)
        # Let's use "vehicleRef" as the code, similar to the original script's logic
        vehicle_code = item.get("vehicleRef")
        if not vehicle_code:
            # Fallback to vehicleId if vehicleRef is missing, though vehicleRef seems more suitable
            logger.warning(
                f"Missing 'vehicleRef', falling back to 'vehicleId' for item: {item}"
            )
            vehicle_code = item["vehicleId"]

        defaults = {
            "operator_id": self.operator,
        }
        # We can use vehicleRef as the vehicleRef if it's present and suitable
        if item.get("vehicleRef"):
            defaults["fleet_number"] = item["vehicleRef"]
        vehicle, created = self.vehicles.get_or_create(
            defaults, source=self.source, code=vehicle_code
        )
        if created:
            logger.info(f"Created new vehicle: {vehicle_code}")
        return vehicle, created  # returning 2 variables

    def get_items(self):
        # Modified to handle the new API's dictionary response structure
        data = super().get_items()
        items = data.get("items", [])  # Extracts list of vehicle items
        logger.info(f"Fetched {len(items)} items from API")
        return items

    def get_journey(self, item, vehicle):
        journey = VehicleJourney()
        journey.route_name = item["routeName"]
        journey.direction = item["direction"][:8]
        journey.destination = item.get(
            "destination", ""
        )  # Use .get() with a default
        journey.block = item.get("vehicleDutyId", "")
        logger.debug(
            f"Created journey for vehicle {vehicle.code}: route={journey.route_name}, destination={journey.destination}"
        )
        return journey

    def create_vehicle_location(self, item):
        position_data = item.get("position")
        if not position_data:
            logger.warning(f"Missing 'position' data for item: {item}")
            return None  # No position data available

        latitude = position_data.get("latitude")
        longitude = position_data.get("longitude")
        bearing = position_data.get("bearing")

        if latitude is None or longitude is None:
            logger.warning(f"Missing coordinates for item: {item}")
            return None  # Need valid coordinates

        location = VehicleLocation(
            latlong=Point(longitude, latitude),  # Corrected order for Point
            heading=bearing,  # Use .get() as bearing might be optional
        )
        logger.debug(
            f"Created location: lat={latitude}, lon={longitude}, bearing={bearing}"
        )
        return location
