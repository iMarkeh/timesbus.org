import json
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from busstops.models import Favourite


@login_required
@require_POST
@csrf_protect
def toggle_favourite(request):
    """AJAX endpoint to toggle favourite status of an object"""
    try:
        data = json.loads(request.body)
        content_type_id = data.get('content_type_id')
        object_id = data.get('object_id')
        
        if not content_type_id or not object_id:
            return JsonResponse({'error': 'Missing content_type_id or object_id'}, status=400)
        
        # Get the content type and object
        content_type = get_object_or_404(ContentType, id=content_type_id)
        model_class = content_type.model_class()
        obj = get_object_or_404(model_class, id=object_id)
        
        # Toggle favourite
        favourite, created = Favourite.toggle_favourite(request.user, obj)
        
        return JsonResponse({
            'success': True,
            'is_favourited': created,
            'message': 'Added to favourites' if created else 'Removed from favourites'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def favourites_list(request):
    """View to display user's favourites"""
    favourites = Favourite.get_user_favourites(request.user)
    
    # Group by content type for better display
    grouped_favourites = {}
    for fav in favourites:
        content_type = fav.content_type.model
        if content_type not in grouped_favourites:
            grouped_favourites[content_type] = []
        grouped_favourites[content_type].append(fav)
    
    context = {
        'favourites': favourites,
        'grouped_favourites': grouped_favourites,
        'page_title': 'My Favourites',
    }
    
    return render(request, 'favourites/favourites_page.html', context)


@login_required
def favourites_api(request):
    """API endpoint to get user's favourites as JSON"""
    favourites = Favourite.get_user_favourites(request.user)
    
    data = []
    for fav in favourites:
        obj = fav.content_object
        if obj:  # Make sure the object still exists
            data.append({
                'id': fav.id,
                'content_type': fav.content_type.model,
                'object_id': fav.object_id,
                'object_name': str(obj),
                'object_url': getattr(obj, 'get_absolute_url', lambda: '#')(),
                'created_at': fav.created_at.isoformat(),
            })
    
    return JsonResponse({
        'favourites': data,
        'count': len(data)
    })
