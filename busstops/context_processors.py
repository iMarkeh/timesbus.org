from django.utils import timezone
from .models import CustomStyle, NotificationBanner


def custom_styles(request):
    """Context processor to inject custom styles for the current date and path"""
    try:
        # Get active style for current date and path
        active_style = CustomStyle.get_active_style_for_date(path=request.path)

        # Debug logging (remove this after testing)
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Path: {request.path}, Active style: {active_style}")
        if active_style and hasattr(active_style, 'path_patterns'):
            logger.debug(f"Style patterns: {active_style.path_patterns}")

        context = {
            'custom_style': active_style,
            'has_custom_style': active_style is not None,
        }

        if active_style:
            # Generate CSS variables for both light and dark modes
            light_variables = active_style.get_css_variables(dark_mode=False)
            dark_variables = active_style.get_css_variables(dark_mode=True)

            context.update({
                'custom_light_variables': light_variables,
                'custom_dark_variables': dark_variables,
                'custom_additional_css': active_style.additional_css,
            })

        return context
    except Exception as e:
        # Log the actual error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in custom_styles context processor: {e}")
        return {
            'custom_style': None,
            'has_custom_style': False,
        }


def notification_banners(request):
    """Context processor to inject notification banners for the current path"""
    try:
        active_banners = NotificationBanner.get_active_banners_for_path(request.path)
        return {
            'notification_banners': active_banners,
            'has_notification_banners': len(active_banners) > 0,
        }
    except Exception:
        # Fail silently if there's any issue (e.g., during migrations)
        return {
            'notification_banners': [],
            'has_notification_banners': False,
        }
