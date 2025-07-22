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
    WANTED_CODES = [120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 201, 202, 203, 204, 205, 206, 207, 208, 210, 211, 212, 213, 214, 216, 217, 218, 219, 220, 221, 222, 234, 235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279, 280, 281, 282, 287, 288, 292, 293, 294, 295, 296, 298, 299, 299, 301, 301, 302, 302, 303, 303, 304, 305, 306, 307, 308, 309, 310, 311, 312, 313, 314, 315, 316, 317, 318, 319, 320, 321, 322, 323, 324, 325, 326, 343, 366, 367, 368, 369, 370, 371, 372, 373, 374, 377, 378, 379, 380, 381, 382, 383, 384, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396, 397, 398, 405, 406, 407, 408, 409, 410, 411, 412, 413, 414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427, 428, 429, 430, 431, 432, 433, 434, 435, 436, 450, 451, 452, 453, 454, 455, 456, 457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 499, 500, 501, 502, 503, 504, 505, 506, 511, 512, 513, 515, 517, 528, 529, 530, 531, 532, 533, 534, 535, 536, 537, 538, 539, 540, 540, 541, 541, 544, 545, 546, 547, 548, 549, 550, 551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656, 657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 668, 669, 670, 671, 672, 673, 674, 675, 676, 677, 678, 679, 680, 681, 682, 683, 684, 685, 686, 687, 688, 689, 690, 691, 692, 693, 694, 695, 696, 697, 698, 700, 701, 702, 703, 704, 705, 708, 709, 710, 711, 712, 713, 714, 715, 716, 717, 718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730, 731, 732, 733, 734, 735, 736, 737, 738, 739, 740, 741, 742, 743, 744, 745, 746, 747, 748, 749, 750, 751, 752, 753, 754, 755, 756, 757, 758, 759, 760, 761, 762, 763, 764, 765, 766, 767, 768, 769, 770, 771, 772, 775, 776, 777, 778, 779, 800, 803, 804, 805, 806, 807, 810, 811, 814, 817, 819, 820, 822, 824, 826, 828, 829, 830, 831, 832, 833, 834, 851, 852, 853, 854, 855, 856, 901, 902, 903, 904, 905, 906, 908, 909, 910, 911, 918, 919, 920, 921, 922, 923, 924, 940, 941, 942, 943, 944, 945, 946, 947, 948, 949, 950, 951, 952, 953, 954, 955, 956, 957, 958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 968, 969, 970, 971, 972, 973, 974, 975, 976, 977, 978, 979, 980, 981, 982, 983, 984, 985, 986, 987, 988, 989, 990, 991, 992, 993, 994, 995, 996, 997]
    OPERATOR_PREFIX = "NCTR"
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
                        code = f"wd-{current_code_str}"

                        # Example logic for fleet_number and fleet_code
                        # Adjust this based on your actual data requirements and schema types
                        fleet_number = None # Or an integer if applicable, e.g., int(current_code_str) if it's always numeric
                        fleet_code = current_code_str # Often a string identifier

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
