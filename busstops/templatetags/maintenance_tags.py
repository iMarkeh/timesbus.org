from django import template
from django.utils import timezone # Import timezone
from datetime import time

register = template.Library()

@register.inclusion_tag('maintenance.html', takes_context=True)
def show_maintenance_alert(context):
    now = timezone.now() # Use timezone.now()

    # --- DEBUGGING PRINT STATEMENTS START ---
    is_sunday = now.weekday() == 6
    start_time = time(20, 30) # 9:30 PM
    end_time = time(22, 20)   # 11:00 PM
    current_time = now.time()
    is_within_time_window = start_time <= current_time <= end_time
    show_alert = is_sunday and is_within_time_window
    # --- DEBUGGING PRINT STATEMENTS END ---

    return {
        'show_alert': show_alert,
    }
