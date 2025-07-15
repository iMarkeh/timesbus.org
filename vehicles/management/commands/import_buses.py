import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Creates a fixed range of test vehicles directly in the 'vehicles_vehicle' table, providing defaults for non-nullable columns."

    # --- Configuration for this specific script ---
    WANTED_CODES = []
    OPERATOR_PREFIX = "BUS"
    VEHICLE_TABLE_NAME = "vehicles_vehicle"
    # ---------------------------------------------

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE(
                f"Attempting to create test vehicles with '{self.OPERATOR_PREFIX}-' "
                f"slugs from given code "
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
