from django.utils import timezone
from .models import CustomStyle


def custom_styles(request):
    """Context processor to inject custom styles for the current date"""
    active_style = CustomStyle.get_active_style_for_date()
    
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
