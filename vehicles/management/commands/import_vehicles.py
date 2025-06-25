import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Creates a fixed range of test vehicles directly in the 'vehicles_vehicle' table, providing defaults for non-nullable columns."

    # --- Configuration for this specific script ---
    WANTED_CODES = [66780, 60820, 8, 44, 77, 177, 116, 84, 15, 28, 436, 526, 2150, 3166, 3245, 25,3460, 3496, 3520, 3629, 55, 4632, "RM1414", 74, 1001, 246, 368, 394, 163, 17,11, 235, 280, 235, 112, 214, 254, 70, 185, 308, 321, 91, 97, 57, "8860 VR", 27,97, 432, 270, 224, 174, "C295", 1205, 7001, "EX30", 5781, 1722, 5083, 3065,5208, 1676, 63, 4706, 612, "LMA 284", "SDK 442", "HTF 586", "YDK 590","HVU 244N", "PA 164", 80, 1250, "EX62", 2, "LSU 282", "A118", 106, 256,"BRJ 333", "W4", 6]
    OPERATOR_PREFIX = "MOTGM"
    VEHICLE_TABLE_NAME = "vehicles_vehicle"
    # ---------------------------------------------

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE(
                f"Attempting to create test vehicles with '{self.OPERATOR_PREFIX}-' "
                f"slugs from code kieron welsh is a nonce"
                f"(inclusive) in table..."
            )
        )

        try:
            with transaction.atomic(), connection.cursor() as cursor:
                default_source_id = 'NULL' # If 'source_id' is nullable in DB
                default_operator_id = self.OPERATOR_PREFIX.upper()


                vehicle_data_values = []
                for current_numeric_code in range(0, len(self.WANTED_CODES) + 1):
                    current_code_str = str(WANTED_CODES[current_numeric_code])
                    slug = f"{self.OPERATOR_PREFIX}-{current_code_str}"
                    code = current_code_str
                    if self.WANTED_CODES[current_numeric_code].isstring():
                        fleet_number = self.WANTED_CODES[current_numeric_code]
                    fleet_code = current_code_str
                    reg = f""
                    colours = ""
                    name = f""
                    branding = ""
                    notes = f""                    
                    latest_journey_data = 'NULL'
                    withdrawn = "FALSE"
                    data = 'NULL'
                    locked = "FALSE"
                    garage_id = 'NULL'
                    latest_journey_id = 'NULL'
                    livery_id = 'NULL'
                    operator_id = f"'{default_operator_id}'"
                    source_id = default_source_id
                    vehicle_type_id = 'NULL'
                    vehicle_data_values.append(
                        f"""
                        (
                            '{slug}',
                            '{code}',
                            {fleet_number},
                            '{fleet_code}',
                            '{reg}',
                            '{colours}',
                            '{name}',
                            '{branding}',
                            '{notes}',
                            {latest_journey_data},
                            {withdrawn},
                            {data},
                            {locked},
                            {garage_id},
                            {latest_journey_id},
                            {livery_id},
                            {operator_id},
                            {source_id},
                            {vehicle_type_id}
                        )
                        """
                    )

                if not vehicle_data_values:
                    self.stdout.write(self.style.WARNING("No vehicles to insert within the specified range."))
                    return
                insert_sql = f"""
                INSERT INTO {self.VEHICLE_TABLE_NAME} (
                    slug, code, fleet_number, fleet_code, reg, colours, name,
                    branding, notes, latest_journey_data, withdrawn, data,
                    locked, garage_id, latest_journey_id, livery_id,
                    operator_id, source_id, vehicle_type_id
                )
                VALUES {','.join(vehicle_data_values)}
                ON CONFLICT (slug) DO NOTHING;
                """
                
                # Execute the bulk insert
                cursor.execute(insert_sql)
                rows_processed = cursor.rowcount 
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully processed. "
                        f"Attempted to create {len(vehicle_data_values)} vehicles. "
                        f"Inserted/Skipped {rows_processed} rows."
                    )
                )

        except Exception as e:
            raise CommandError(f"Error creating test vehicles: {e}")
