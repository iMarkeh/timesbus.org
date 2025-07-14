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
    WANTED_CODES = [10743, 12032, 12042, 12050, 12051, 15619, 15652, 16907, 16910, 16913, 16914, 16916, 16917, 16918, 16919, 16920, 16939, 16941, 16944, 16964, 16966, 17013, 17015, 17016, 17479, 17673, 17676, 17677, 17678, 17717, 17719, 17730, 18022, 18023, 18024, 18026, 18027, 18028, 18029, 18031, 18033, 18035, 18038, 18040, 18042, 18043, 18044, 18047, 18048, 18050, 18052, 18054, 18055, 18120, 18121, 18122, 18164, 18309, 18316, 18317, 18318, 18319, 18320, 18335, 18338, 18344, 18347, 18348, 18391, 18418, 18426, 18427, 18428, 18429, 18430, 18431, 18432, 18434, 18435, 18449, 18473, 18507, 18509, 19009, 19011, 19015, 19022, 19050, 19052, 19057, 19060, 19061, 19066, 19070, 19073, 19074, 19100, 19101, 19111, 19113, 19121, 19122, 19123, 19127, 19147, 19200, 19203, 19209, 19380, 19384, 19638, 19639, 19688, 21211, 21212, 21213, 21214, 21215, 21216, 21248, 21273, 22576, 22635, 22755, 22760, 22764, 22798, 22831, 27784, 28620, 30016, 34426, 34456, 34530, 34702, 34848, 34850, 34851, 35128, 35129, 35130, 35133, 35135, 35136, 35137, 35139, 35140, 35141, 35142, 35143, 35144, 35145, 35146, 35147, 35148, 35149, 35150, 36001, 36002, 36003, 36005, 36006, 36007, 39676, 39678, 39679, 39690, 39691, 39693, 47812]
    OPERATOR_PREFIX = "SCEM"
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
                        code = current_code_str

                        # Example logic for fleet_number and fleet_code
                        # Adjust this based on your actual data requirements and schema types
                        fleet_number = current_code_str # Or an integer if applicable, e.g., int(current_code_str) if it's always numeric
                        fleet_code = "" # Often a string identifier

                        reg = "" # Assuming reg is a string/varchar
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
                        source_id = None
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
