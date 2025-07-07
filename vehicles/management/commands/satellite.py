import datetime
import requests
from django.contrib.gis.geos import Point
from ...models import VehicleLocation, VehicleJourney, Vehicle
from busstops.models import Operator
from ..import_live_vehicles import ImportLiveVehiclesCommand
import sys
N2YO_API_KEY = "6FDCJ7-YLVT4K-9YHY5W-5IF0" # you will have to get one from n2yo, it's free just sign up for an account and it will be within the account settings page (iirc)
OBSERVER_LAT = 0.0
OBSERVER_LON = 0.0
OBSERVER_ALT = 0
SECONDS = 1

 
SATELLITES = [
    (25544, "ISS (Zarya)"),
    (20580, "Hubble Space Telescope"),
    (39084, "Tiangong Space Station"),
    (44238, "Starlink-1001"),
    (37820, "GPS BIIF-1 (USA-203)"),
    (40093, "GPS III SV01"),
    (40286, "GPS III SV02"),
    (42653, "GPS III SV03"),
    (44063, "GPS III SV04"),
    (33393, "GLONASS-M 755"),
    (42138, "GLONASS-K2 801"),
    (42068, "Galileo 6"),
    (48615, "Galileo FOC FM24"),
    (43066, "BeiDou-3 GEO3"),
    (43207, "BeiDou-3 MEO4"),
    (43013, "NOAA 20"),
    (54234, "NOAA 21"),
    (40069, "Gaofen-1"),
    (29486, "Galaxy 15"),
    (29499, "MetOp-A"),
    (25344, "Fengyun-2C"),
    (25994, "NOAA-15"),
    (43010, "GOES-16"),
    (37849, "Landsat 8"),
    (41765, "Sentinel-2A"),
    (26407, "TerreStar-1"),
    (40967, "Cygnus CRS OA-7"),
    (33591, "Terra (EOS AM-1)"),
    (40362, "Aqua"),
    (27386, "Jason-1"),
    (29478, "Marisat"),
    (29047, "Comstar"),
    (19009, "Palapa"),
    (72249, "Starlink-G15-6"),
    (72250, "Starlink-G12-26"),
    (72251, "Starlink-G15-9"),
    (72252, "Starlink-G10-18"),
    (72253, "Starlink-G10-23"),
    (72254, "Starlink-G10-16"),
    (38882, "Marisat West"),
    (38882, "Marisat East"),
    (16908, "Ajisai"),
    (60182, "ALOS-4"),
    (22825, "AO-27"),
    (22826, "IO-26"),
    (43679, "STARS-AO"),
    (43700, "Es'Hail-2"),
    (43721, "FacSat-1"),
    (43722, "Centauri-2"),
    (43728, "3CAT-1"),
    (43738, "InnoSat-2"),
    (43743, "Reaktor Hello World"),
    (72475, "USA-358"),
    (72476, "USA-359"),
    (72477, "USA-360"),
    (2, "Sputnik 1"),
    (5, "Explorer 1"),
    (134, "Transit 5"),
    (25539, "Skynet 5A"),
    (27422, "Idefix"),
    (25338, "Fengyun-1C Debris"),
    (41474, "Iridium 33 Debris"),
    (37849, "Landsat-8"),
] + [(i, f"Satellite_{i}") for i in range(5000, 50120)]

class Command(ImportLiveVehiclesCommand):
    help = "imports space stations and satelites"
    source_name = "N2YO" # add this to Data Sources on the Django backend 

    def get_items(self):
        all_items = []
        for sat_id, name in SATELLITES:
            url = (
                f"https://api.n2yo.com/rest/v1/satellite/positions/"
                f"{sat_id}/{OBSERVER_LAT}/{OBSERVER_LON}/{OBSERVER_ALT}/{SECONDS}/&apiKey={N2YO_API_KEY}"
            )
            try:
                response = self.session.get(url, timeout=20)
                response.raise_for_status()
                data = response.json()
                pos = data.get("positions", [{}])[0]
                if "satlatitude" in pos:
                    all_items.append({
                        "timestamp": pos["timestamp"],
                        "lat": pos["satlatitude"],
                        "lon": pos["satlongitude"],
                        "altitude": pos["sataltitude"],
                        "fn": name,
                        "line": "Orbit",
                        "direction": "Earth",
                        "bearing": 0,
                        "sat_id": sat_id,
                    })
            except Exception as e:
                self.stderr.write(f"Error fetching satellite {name}: {e}")
        return all_items


    def get_datetime(self, item):
        return datetime.datetime.fromtimestamp(item["timestamp"], datetime.timezone.utc)

    def get_vehicle(self, item):
        operator, _ = Operator.objects.get_or_create(
            name="NASA",
            defaults={"code": "NASA", "noc": "NASA"},
        )
        reg = f"SAT-{item['sat_id']}"
        code = reg
        vehicle, created = Vehicle.objects.get_or_create(
            reg=reg,
            operator=operator,
            defaults={"code": code},
        )
        return vehicle, created
    def get_journey(self, item, vehicle):
        journey_datetime = self.get_datetime(item)
        block_start = journey_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        journey, created = VehicleJourney.objects.get_or_create(
            vehicle=vehicle,
            datetime=block_start,
            route_name=item.get("line", "Satelite"),
            defaults={
                "direction": item.get("direction", "Earth"),
                "source": self.source,
            },
        )
        if created:
            journey.code = f"{vehicle.reg}-{block_start.strftime('%Y%m%d')}"
            journey.save()
            self.stdout.write(f"Created journey: {journey.code}")
        return journey

    def create_vehicle_location(self, item):
        return VehicleLocation(
            latlong=Point(float(item["lon"]), float(item["lat"])),
            heading=item["bearing"],
        )
    
    def handle(self, *args, **options):
            super().handle(*args, **options)
            #self.stdout.write(self.style.SUCCESS("✅ All satellites imported, exiting."))
            #sys.exit(0)
