import re
from http import HTTPStatus

from django.middleware.gzip import GZipMiddleware
from django.utils.cache import add_never_cache_headers

# from multidb.pinning import pin_this_thread, unpin_this_thread
from whitenoise.middleware import WhiteNoiseMiddleware

from django.contrib.auth import get_user_model
User = get_user_model()


from .models import FeatureToggle
from django.shortcuts import render
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

class WhiteNoiseWithFallbackMiddleware(WhiteNoiseMiddleware):
    def immutable_file_test(self, path, url):
        # ensure that cache-control headers are added
        # for files with hashes added by parcel e.g. "dist/js/BigMap.19ec75b5.js"
        if re.match(r"^.+\.[0-9a-f]{8,12}\..+$", url):
            return True
        return super().immutable_file_test(path, url)

    # https://github.com/evansd/whitenoise/issues/245
    def __call__(self, request):
        response = super().__call__(request)
        if response.status_code == HTTPStatus.NOT_FOUND and request.path.startswith(
            self.static_prefix
        ):
            add_never_cache_headers(response)
        return response


# def pin_db_middleware(get_response):
#     def middleware(request):
#         if (
#             request.method == "POST"
#             or request.path.startswith("/admin/")
#             or request.path.startswith("/accounts/")
#             or "/edit" in request.path
#         ):
#             pin_this_thread()
#         else:
#             unpin_this_thread()
#         return get_response(request)

#     return middleware


class GZipIfNotStreamingMiddleware(GZipMiddleware):
    def process_response(self, request, response):
        if response.streaming:
            return response

        return super().process_response(request, response)

EXEMPT_PATHS = ['/admin/', '/accounts/login', '/accounts/logout', '/queue/', '/ads.txt', '/robots.txt', '/favicon.ico']

class SiteLockMiddleware:
    """
    Middleware to handle site-wide maintenance mode and feature toggles.

    Checks for maintenance mode features and blocks access for non-superusers
    when maintenance is enabled.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_timeout = 60  # Cache feature toggle for 1 minute

    def __call__(self, request):
        # Always allow access to exempt paths
        if any(request.path.startswith(path) for path in EXEMPT_PATHS):
            return self.get_response(request)

        # Check for site-wide maintenance mode
        maintenance_feature = self._get_maintenance_feature()

        if maintenance_feature and self._should_block_user(maintenance_feature, request.user):
            context = self._get_maintenance_context(maintenance_feature)
            return render(request, 'site_locked.html', context, status=503)

        return self.get_response(request)

    def _get_maintenance_feature(self):
        """Get the maintenance feature toggle, with caching"""
        cache_key = 'site_maintenance_feature'
        feature = cache.get(cache_key)

        if feature is None:
            try:
                # Look for any feature with maintenance enabled
                feature = FeatureToggle.objects.filter(
                    maintenance=True,
                    enabled=True
                ).first()

                # Cache the result (or None if no maintenance feature found)
                cache.set(cache_key, feature, self.cache_timeout)

            except Exception as e:
                logger.error(f"Error checking maintenance feature: {e}")
                feature = None

        return feature

    def _should_block_user(self, feature, user):
        """Determine if user should be blocked based on feature settings"""
        # Always allow superusers during maintenance
        if user and user.is_superuser:
            return False

        # Block if maintenance is enabled
        return feature.maintenance and feature.enabled

    def _get_maintenance_context(self, feature):
        """Get context for the maintenance template"""
        context = {
            'hours': feature.estimated_hours or 2,  # Default to 2 hours if not set
            'message': feature.maintenance_message or 'The site is currently under maintenance.',
            'feature_name': feature.name,
        }
        return context
