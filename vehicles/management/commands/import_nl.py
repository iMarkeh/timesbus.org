import datetime
import logging
import re # Import regex for parsing the label
from django.contrib.gis.geos import Point
from ..import_live_vehicles import ImportLiveVehiclesCommand
from ...models import VehicleLocation, VehicleJourney

logger = logging.getLogger(__name__)


class Command(ImportLiveVehiclesCommand):
    source_name = "Netherlands Trains (Spoorkaart)"  # Updated source name
    operator = "NS"  # Still likely NS for most trains

    # Base URL for the Spoorkaart API
    # The 'id' parameter appears to be a required API key/session ID
    API_KEY = "fa58ae962e961617504a40357ae85a42"
    # Specific BBox for Netherlands (adjust if needed)
    NETHERLANDS_BBOX = "3.0,50.7,7.2,53.5"
    url = (
        f"https://spoorkaart.mwnn.nl/?op=trains&bbox={NETHERLANDS_BBOX}&id={API_KEY}"
    )

    @staticmethod
    def get_datetime(item):
        # The provided snippet doesn't have a specific timestamp for the item.
        # If the API response itself has a top-level 'timestamp' field, use that.
        # For now, we'll fall back to the current UTC time.
        # Example if there was a response_timestamp = data.get('timestamp') in get_items():
        # return datetime.datetime.fromtimestamp(response_timestamp, tz=datetime.timezone.utc)
        return datetime.datetime.now(
            datetime.timezone.utc
        )  # Fallback to now if no specific item timestamp

    def get_vehicle(self, item):
        # 'ref' looks like the unique identifier for the train (e.g., train number)
        # Use it as both code and fleet_number as it's directly available.
        vehicle_code = item["properties"].get("ref")
        fleet_number = item["properties"].get("ref") # Use 'ref' as fleet number

        if not vehicle_code:
            logger.error(f"Missing 'ref' in properties for train item: {item}. Skipping vehicle.")
            return None, False

        defaults = {
            "operator_id": self.operator,
            "fleet_number": fleet_number,
        }

        vehicle, created = self.vehicles.get_or_create(
            defaults, source=self.source, code=vehicle_code
        )
        if created:
            logger.info(f"Created new Netherlands train vehicle: {vehicle_code}")
        return vehicle, created

    def get_items(self):
        # The API returns a dictionary with a 'features' key containing the list of train features.
        try:
            data = super().get_items()
            features = data.get("features", [])
            if not isinstance(features, list):
                logger.error(
                    f"Spoorkaart API returned unexpected 'features' format (expected list): {features}"
                )
                return []
            logger.info(f"Fetched {len(features)} train features from Spoorkaart API")
            return features
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from Spoorkaart API: {e}")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred in get_items: {e}")
            return []

    def get_journey(self, item, vehicle):
        journey = VehicleJourney()
        properties = item.get("properties", {})

        # 'type' field for route name (e.g., "IC")
        journey.route_name = properties.get("type", "UNKNOWN_ROUTE")

        # Parse destination and train number from 'label'
        # Example: "IC 142 â†’ Bh +119"
        label = properties.get("label", "")
        match = re.search(r"^(.*?)\s*→\s*(.*?)(?:\s*\(.+\))?(?:\s*\+\d+)?\s*$", label)
        if match:
            # Group 1 is typically the train number/type+number (e.g., "IC 142")
            # Group 2 is the destination (e.g., "Bh")
            journey.block = match.group(1).strip() # Use train number as block/journey ID
            journey.destination = match.group(2).strip()
        else:
            journey.block = properties.get("ref", "") # Fallback to ref if parsing fails
            journey.destination = ""
            logger.warning(f"Could not parse destination from label: '{label}'")

        # Direction is not directly provided in the snippet, default to UNKNOWN
        journey.direction = "UNKNOWN"[:8]

        logger.debug(
            f"Created journey for train {vehicle.code} ({journey.block}): "
            f"route={journey.route_name}, destination={journey.destination}"
        )
        return journey

    def create_vehicle_location(self, item):
        geometry = item.get("geometry", {})
        coordinates = geometry.get("coordinates")

        if not coordinates or not isinstance(coordinates, list) or len(coordinates) != 2:
            logger.warning(f"Missing or invalid 'coordinates' for train item: {item}. Skipping location creation.")
            return None

        # Coordinates order is [longitude, latitude]
        longitude, latitude = coordinates

        # No explicit bearing or speed in the provided snippet
        bearing = None
        speed = None

        # Ensure coordinates are floats
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (TypeError, ValueError):
            logger.warning(
                f"Invalid coordinate format for train item: lat={latitude}, lon={longitude}. "
                "Skipping location creation."
            )
            return None

        location = VehicleLocation(
            latlong=Point(longitude, latitude),  # Correct order for Point (lon, lat)
            heading=bearing,
        )
        logger.debug(
            f"Created location for train {item['properties'].get('ref')}: "
            f"lat={latitude}, lon={longitude}"
        )
        return location
