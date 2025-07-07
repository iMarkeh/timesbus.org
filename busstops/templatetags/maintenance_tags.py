from django import template
from django.utils import timezone # Import timezone
from datetime import time

register = template.Library()

@register.inclusion_tag('maintenance.html', takes_context=True)
def show_maintenance_alert(context):
    now = timezone.now() # Use timezone.now()

    # --- DEBUGGING PRINT STATEMENTS START ---
    print(f"\n--- Maintenance Alert Debug ---")
    print(f"Current Time (Django TZ): {now}")
    print(f"Current Weekday (0=Mon, 6=Sun): {now.weekday()}")
    print(f"Current Time (just time part): {now.time()}")

    is_sunday = now.weekday() == 6
    print(f"Is Sunday? {is_sunday}")

    start_time = time(20, 30) # 9:30 PM
    end_time = time(22, 20)   # 11:00 PM
    print(f"Maintenance Window: {start_time} to {end_time}")

    current_time = now.time()
    is_within_time_window = start_time <= current_time <= end_time
    print(f"Is within time window? {is_within_time_window}")

    show_alert = is_sunday and is_within_time_window
    print(f"Final show_alert value: {show_alert}")
    print(f"--- End Debug ---\n")
    # --- DEBUGGING PRINT STATEMENTS END ---

    return {
        'show_alert': show_alert,
    }
