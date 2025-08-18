from django import template
from django.contrib.contenttypes.models import ContentType
from busstops.models import Favourite

register = template.Library()


@register.simple_tag
def is_favourited(user, obj):
    """Check if an object is favourited by the user"""
    return Favourite.is_favourited(user, obj)


@register.simple_tag
def get_user_favourites(user, content_type=None):
    """Get all favourites for a user, optionally filtered by content type"""
    return Favourite.get_user_favourites(user, content_type)


@register.inclusion_tag('favourites/favourite_button.html', takes_context=True)
def favourite_button(context, obj, css_class=""):
    """Render a favourite/unfavourite button for an object"""
    request = context.get('request')
    user = request.user if request else None
    
    is_fav = Favourite.is_favourited(user, obj) if user and user.is_authenticated else False
    
    return {
        'user': user,
        'object': obj,
        'is_favourited': is_fav,
        'css_class': css_class,
        'content_type_id': ContentType.objects.get_for_model(obj).id,
        'object_id': obj.pk,
    }


@register.inclusion_tag('favourites/favourites_list.html')
def favourites_list(user, limit=None):
    """Render a list of user's favourites"""
    if not user.is_authenticated:
        return {'favourites': [], 'grouped_favourites': {}, 'user': user}

    favourites = Favourite.get_user_favourites(user)

    if limit:
        favourites = favourites[:limit]

    # Group by content type for better display
    grouped_favourites = {}
    for fav in favourites:
        content_type = fav.content_type.model
        if content_type not in grouped_favourites:
            grouped_favourites[content_type] = []
        grouped_favourites[content_type].append(fav)

    return {
        'favourites': favourites,
        'grouped_favourites': grouped_favourites,
        'user': user,
    }
