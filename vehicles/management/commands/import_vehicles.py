import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Creates a fixed range of test vehicles directly in the 'vehicles_vehicle' table, providing defaults for non-nullable columns."

    # --- Configuration for this specific script ---
    WANTED_CODES = [22193, 22195, 22196, 22197, 22198, 22199, 22201, 22202, 22214, 22451, 22452, 22453, 22454, 22455, 22456, 22462, 22463, 22464, 22465, 22466, 22467, 22468, 22469, 22470, 22471, 22472, 22473, 22474, 22475, 22476, 22477, 22478, 22479, 22480, 22481, 22482, 22483, 22484, 22485, 22486, 22487, 22488, 22489, 22490, 22491, 22492, 22493, 22494, 22495, 22011, 22012, 22013, 22014, 22015, 22016, 22017, 22018, 22019, 22020, 22021, 22022, 22023, 22024, 22025, 22026, 22027, 22028, 22029, 22030, 22031, 22032, 22033, 22034, 22035, 22036, 22037, 22038, 22039, 22040, 22041, 22042, 22043, 22044, 22045, 22046, 22047, 22048, 22049, 22050, 22051, 22062, 22063, 22064, 22065, 22066, 22067, 22068, 22069, 22070, 22072, 22074, 22077, 22078, 22079, 22080, 22081, 22082, 22342, 22343, 22344, 22345, 22346, 22347, 22348, 22408, 22409, 22410, 22411, 22412, 22428, 22443, 22444]
    OPERATOR_PREFIX = "SCNE"
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
                for current_numeric_code in range(0, len(self.WANTED_CODES)):
                    current_code_str = str(f"{self.WANTED_CODES[current_numeric_code]}")
                    slug = f"{self.OPERATOR_PREFIX}-{current_code_str}"
                    code = current_code_str
                    if type(self.WANTED_CODES[current_numeric_code]) == int:
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
