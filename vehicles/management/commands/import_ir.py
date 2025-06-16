import datetime
import logging
import requests
import xml.etree.ElementTree as ET
from django.contrib.gis.geos import Point
from ..import_live_vehicles import ImportLiveVehiclesCommand
from ...models import VehicleLocation, VehicleJourney

logger = logging.getLogger(__name__)

IRISHRAIL_NAMESPACE = "{http://api.irishrail.ie/realtime/}"


class Command(ImportLiveVehiclesCommand):
    source_name = "Irish Rail GTFS"
    operator = "ie-7778017"
    url = "https://api.irishrail.ie/realtime/realtime.asmx/getCurrentTrainsXML_WithTrainType?TrainType=D"

    request_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
    }

    request_timeout = 10

    def get_items(self):
        """
        Fetches and parses the XML data from the Irish Rail API.
        Includes a User-Agent header in the request.
        """
        try:
            response = requests.get(
                self.url,
                timeout=self.request_timeout,
                headers=self.request_headers,
            )
            response.raise_for_status()
            xml_data = response.content

            root = ET.fromstring(xml_data)
            items = root.findall(f"{IRISHRAIL_NAMESPACE}objTrainPositions")
            logger.info(f"Fetched {len(items)} train positions from Irish Rail API")
            return items
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching data from Irish Rail API: {e}")
            return []
        except ET.ParseError as e:
            logger.error(f"Error parsing XML from Irish Rail API: {e}")
            return []

    @staticmethod
    def get_datetime(item):
        return datetime.datetime.now(datetime.timezone.utc)

    def get_vehicle(self, item):
        train_code_element = item.find(f"{IRISHRAIL_NAMESPACE}TrainCode")
        vehicle_code = train_code_element.text if train_code_element is not None else None

        if not vehicle_code:
            logger.warning(f"Missing 'TrainCode' for item: {ET.tostring(item)}")
            return None, False

        defaults = {
            "operator_id": self.operator,
            "fleet_code": vehicle_code,
        }
        vehicle, created = self.vehicles.get_or_create(
            defaults, source=self.source, code=vehicle_code
        )
        if created:
            logger.info(f"Created new vehicle (train): {vehicle_code}")
        return vehicle, created

    def get_journey(self, item, vehicle):
        """
        Extracts journey details for the train.
        Refined parsing of PublicMessage for route_name and destination.
        """
        journey = VehicleJourney()

        public_message_element = item.find(f"{IRISHRAIL_NAMESPACE}PublicMessage")
        public_message = (
            public_message_element.text if public_message_element is not None else ""
        )

        direction_element = item.find(f"{IRISHRAIL_NAMESPACE}Direction")
        direction_text = direction_element.text if direction_element is not None else ""

        train_code_element = item.find(f"{IRISHRAIL_NAMESPACE}TrainCode")
        train_code = train_code_element.text if train_code_element is not None else ""

        ROUTE_NAME_MAX_LENGTH = 64
        DESTINATION_MAX_LENGTH = 64
        DIRECTION_MAX_LENGTH = 8

        # --- Set Direction first (already truncated) ---
        journey.direction = direction_text[:DIRECTION_MAX_LENGTH]

        # --- Determine Destination ---
        # Prioritize the explicit 'Direction' field for destination
        if direction_text:
            journey.destination = direction_text[:DESTINATION_MAX_LENGTH]
        else:
            # Fallback for destination from PublicMessage if 'Direction' is missing
            # This handles cases like "TERMINATED Bray at 21:18" where Bray is the destination
            # We look for a keyword like "TERMINATED " or "Arrived " and extract the station name
            destination_from_message = ""
            if "TERMINATED " in public_message:
                parts = public_message.split("TERMINATED ", 1)
                if len(parts) > 1:
                    # e.g., "Bray at 21:18" -> "Bray"
                    destination_from_message = parts[1].split(" at ")[0].strip()
            elif "Arrived " in public_message:
                parts = public_message.split("Arrived ", 1)
                if len(parts) > 1:
                    # e.g., "Mallow next stop Cork" -> "Cork" (last stop)
                    if " next stop " in parts[1]:
                        destination_from_message = parts[1].split(" next stop ")[1].strip()
                    else:
                        destination_from_message = parts[1].split(" ")[0].strip() # Just the first word
            
            # If nothing specific extracted, try the last segment of a "X to Y" route
            if not destination_from_message:
                lines = public_message.split("\n")
                if len(lines) > 1 and " to " in lines[1]:
                    route_parts = lines[1].strip().split(" to ")
                    if len(route_parts) > 1:
                        destination_from_message = route_parts[1].split(" ")[0].strip(")") # remove any closing parenthesis


            journey.destination = destination_from_message[:DESTINATION_MAX_LENGTH]


        # --- Determine Route Name ---
        lines = public_message.split("\n")
        extracted_route_name = ""

        if len(lines) > 1 and lines[0].strip() == train_code:
            # If the first line is just the train code, the second line is the route
            # Example: "P537\nCobh to Cork\n..."
            # Example: "E257\n20:03 - Malahide to Bray(1 mins late)\n..."
            route_candidate = lines[1].strip()

            # Remove leading timestamp if present (e.g., "20:03 - ")
            if route_candidate and route_candidate[0].isdigit() and " - " in route_candidate:
                # Find the first hyphen that indicates a route, not a timestamp
                parts = route_candidate.split(" - ", 1)
                if len(parts) > 1 and not (parts[0].isdigit() and len(parts[0].split(':'))==2): # If first part is not a time
                    extracted_route_name = route_candidate
                elif len(parts) > 1 and parts[0].isdigit() and len(parts[0].split(':'))==2: # If first part IS a time
                     extracted_route_name = parts[1].strip() # Take everything after "HH:MM - "
                else:
                    extracted_route_name = route_candidate # Fallback
            else:
                extracted_route_name = route_candidate
        else:
            # Fallback: if not standard multi-line with train code first, use the entire message
            # This might still be too long, but captures edge cases where route isn't line 2
            extracted_route_name = public_message

        # Truncate string to fit model field limit
        journey.route_name = extracted_route_name[:ROUTE_NAME_MAX_LENGTH]

        journey.block = ""

        logger.debug(
            f"Created journey for vehicle {vehicle.code}: route='{journey.route_name}', destination='{journey.destination}', direction='{journey.direction}'"
        )
        return journey

    def create_vehicle_location(self, item):
        latitude_element = item.find(f"{IRISHRAIL_NAMESPACE}TrainLatitude")
        longitude_element = item.find(f"{IRISHRAIL_NAMESPACE}TrainLongitude")

        latitude = float(latitude_element.text) if latitude_element is not None else None
        longitude = float(longitude_element.text) if longitude_element is not None else None

        if latitude is None or longitude is None or (latitude == 0 and longitude == 0):
            logger.warning(
                f"Missing or invalid (0,0) coordinates for item: {ET.tostring(item)}"
            )
            return None

        location = VehicleLocation(
            latlong=Point(longitude, latitude),
            heading=None,
        )
        logger.debug(
            f"Created location: lat={latitude}, lon={longitude}"
        )
        return location
