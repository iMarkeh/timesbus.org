from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = (
        "Creates a fixed range of test vehicles directly in the 'vehicles_vehicle' "
        "table, providing defaults for non-nullable columns."
    )

    # --- Configuration for this specific script ---
    # Example: If you want vehicles SE-101, SE-102, SE-ABC, SE-XYZ
    WANTED_CODES = ["YY67_HBG", "YJ18_DHC", "YJ18_DHD", "SJ73_HSV", "SJ73_HSX", "SJ73_HSY", "SJ73_HVO", "SD74_KRJ"]
    OPERATOR_PREFIX = "HNMI"
    VEHICLE_TABLE_NAME = "vehicles_vehicle"
    # ---------------------------------------------

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE(
                f"Attempting to create test vehicles with '{self.OPERATOR_PREFIX}-' "
                f"slugs from the WANTED_CODES list in table '{self.VEHICLE_TABLE_NAME}'..."
            )
        )

        try:
            with transaction.atomic():
                with connection.cursor() as cursor:
                    # Collect data for insertion, using None for SQL NULL
                    # and Python booleans for SQL booleans.
                    vehicle_insert_data = []

                    for current_code_raw in self.WANTED_CODES:
                        # Ensure all codes are treated as strings for consistency
                        current_code_str = str(current_code_raw)
                        slug = f"{self.OPERATOR_PREFIX}-{current_code_str}"
                        code = f"{current_code_str}"

                        # Example logic for fleet_number and fleet_code
                        # Adjust this based on your actual data requirements and schema types
                        fleet_number = None # Or an integer if applicable, e.g., int(current_code_str) if it's always numeric
                        fleet_code = "" # Often a string identifier

                        reg = ""
                        colours = ""
                        name = ""
                        branding = ""
                        notes = ""
                        latest_journey_data = None
                        withdrawn = False
                        data = None # For JSONB/JSONField, pass Python dict if needed, else None
                        locked = False
                        garage_id = None
                        latest_journey_id = None
                        livery_id = None
                        operator_id = self.OPERATOR_PREFIX.upper()
                        source_id = 63
                        vehicle_type_id = None

                        vehicle_insert_data.append(
                            (
                                slug,
                                code,
                                fleet_number,
                                fleet_code,
                                reg,
                                colours,
                                name,
                                branding,
                                notes,
                                latest_journey_data,
                                withdrawn,
                                data,
                                locked,
                                garage_id,
                                latest_journey_id,
                                livery_id,
                                operator_id,
                                source_id,
                                vehicle_type_id,
                            )
                        )

                    if not vehicle_insert_data:
                        self.stdout.write(
                            self.style.WARNING("No vehicles to insert within the specified list.")
                        )
                        return

                    # Construct the VALUES part for bulk insertion using placeholders
                    # For (val1, val2, ...), you'll have (%s, %s, ...)
                    placeholders = ", ".join(["%s"] * len(vehicle_insert_data[0]))
                    values_list_placeholders = [
                        f"({placeholders})" for _ in vehicle_insert_data
                    ]

                    # Flatten the list of tuples into a single tuple for execute_many
                    flat_values = [item for sublist in vehicle_insert_data for item in sublist]

                    # Note: execute_many is generally preferred for performance
                    # but it expects a list of tuples, one tuple per row.
                    # Your current approach flattens, so a single execute call with
                    # VALUES (%s, %s, ...), (%s, %s, ...) is also valid.
                    # Let's stick with the single INSERT...VALUES statement for clarity
                    # given the `ON CONFLICT` clause.

                    insert_sql = f"""
                    INSERT INTO {self.VEHICLE_TABLE_NAME} (
                        slug, code, fleet_number, fleet_code, reg, colours, name,
                        branding, notes, latest_journey_data, withdrawn, data,
                        locked, garage_id, latest_journey_id, livery_id,
                        operator_id, source_id, vehicle_type_id
                    )
                    VALUES {','.join(values_list_placeholders)}
                    ON CONFLICT (slug) DO NOTHING;
                    """

                    # Execute the bulk insert with parameters
                    cursor.execute(insert_sql, flat_values)
                    rows_processed = cursor.rowcount

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Successfully processed. "
                            f"Attempted to create {len(vehicle_insert_data)} vehicles. "
                            f"Inserted/Skipped {rows_processed} rows."
                        )
                    )

        except Exception as e:
            logger.exception("Error creating vehicles:") # Log full traceback
            raise CommandError(f"Error creating vehicles: {e}")
