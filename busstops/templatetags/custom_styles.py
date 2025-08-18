from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def custom_style_css():
    """Generate custom CSS for the current date"""
    from busstops.models import CustomStyle
    
    active_style = CustomStyle.get_active_style_for_date()
    if not active_style:
        return ""
    
    css_parts = []
    
    # Light mode variables
    light_variables = active_style.get_css_variables(dark_mode=False)
    if light_variables:
        light_css = ":root {\n"
        for var, value in light_variables.items():
            light_css += f"  {var}: {value};\n"
        light_css += "}"
        css_parts.append(light_css)
    
    # Dark mode variables
    dark_variables = active_style.get_css_variables(dark_mode=True)
    if dark_variables:
        dark_css = ".dark-mode,\nhtml.dark-mode body {\n"
        for var, value in dark_variables.items():
            dark_css += f"  {var}: {value};\n"
        dark_css += "}"
        css_parts.append(dark_css)
    
    # Additional CSS
    if active_style.additional_css:
        css_parts.append(active_style.additional_css)
    
    if css_parts:
        full_css = f"<style>\n/* Custom styles for {active_style.name} */\n" + "\n\n".join(css_parts) + "\n</style>"
        return mark_safe(full_css)
    
    return ""


@register.simple_tag
def has_custom_style():
    """Check if there's an active custom style for today"""
    from busstops.models import CustomStyle
    return CustomStyle.get_active_style_for_date() is not None


@register.simple_tag
def get_custom_style():
    """Get the active custom style for today"""
    from busstops.models import CustomStyle
    return CustomStyle.get_active_style_for_date()


@register.inclusion_tag('banners/notification_banners.html')
def render_notification_banners(banners):
    """Render notification banners with proper styling"""
    return {'banners': banners}


@register.simple_tag
def banner_css_class(banner_type):
    """Get CSS class for banner type"""
    classes = {
        'info': 'banner-info',
        'warning': 'banner-warning',
        'error': 'banner-error',
        'success': 'banner-success',
    }
    return classes.get(banner_type, 'banner-info')
