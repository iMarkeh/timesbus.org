from django.core.cache import cache
from django.template.defaultfilters import linebreaks, linebreaksbr
from django.templatetags.static import static
from django.urls import reverse
from django.utils.safestring import mark_safe
from jinja2 import Environment, nodes
from jinja2.ext import Extension

from busstops.templatetags.urlise import urlise
from vehicles.context_processors import _liveries_css_version
from busstops.models import Favourite, CustomStyle
from django.contrib.contenttypes.models import ContentType

# based on https://jinja.palletsprojects.com/en/3.1.x/extensions/#cache


class FragmentCacheExtension(Extension):
    # a set of names that trigger the extension.
    tags = {"cache"}

    def __init__(self, environment):
        super().__init__(environment)

        # add the defaults to the environment
        environment.extend(fragment_cache_prefix="", fragment_cache=None)

    def parse(self, parser):
        # the first token is the token that started the tag.  In our case
        # we only listen to ``'cache'`` so this will be a name token with
        # `cache` as value.  We get the line number so that we can give
        # that line number to the nodes we create by hand.
        lineno = next(parser.stream).lineno

        # now we parse a single expression that is used as cache key.
        args = [parser.parse_expression()]

        # if there is a comma, the user provided a timeout.  If not use
        # None as second parameter.
        if parser.stream.skip_if("comma"):
            args.append(parser.parse_expression())
        else:
            args.append(nodes.Const(None))

        # now we parse the body of the cache block up to `endcache` and
        # drop the needle (which would always be `endcache` in that case)
        body = parser.parse_statements(["name:endcache"], drop_needle=True)

        # now return a `CallBlock` node that calls our _cache_support
        # helper method on this extension.
        return nodes.CallBlock(
            self.call_method("_cache_support", args), [], [], body
        ).set_lineno(lineno)

    def _cache_support(self, name, timeout, caller):
        """Helper callback."""
        key = self.environment.fragment_cache_prefix + name

        # try to load the block from the cache
        # if there is no fragment in the cache, render it and store
        # it in the cache.
        rv = cache.get(key)
        if rv is not None:
            return rv
        rv = caller()
        cache.set(key, rv, timeout)
        return rv


def environment(**options):
    env = Environment(extensions=[FragmentCacheExtension], **options)
    env.lstrip_blocks = True
    env.trim_blocks = True
    
    def is_favourited(user, obj):
        """Check if an object is favourited by the user"""
        try:
            return Favourite.is_favourited(user, obj)
        except (ValueError, TypeError, AttributeError):
            # Handle any database compatibility issues
            return False
    
    def can_be_favourited(obj):
        """Check if an object can be favourited (now supports both int and string PKs)"""
        return obj.pk is not None
    
    def get_content_type_id(obj):
        """Get content type ID for an object"""
        return ContentType.objects.get_for_model(obj).id
    
    def custom_style_css(request=None):
        """Generate custom CSS for the current date and path"""
        try:
            path = request.path if request else None
            active_style = CustomStyle.get_active_style_for_date(path=path)
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
        except Exception:
            return ""
    
    env.globals.update(
        {
            "static": static,
            "url": reverse,
            "liveries_css_version": _liveries_css_version,
            "urlise": urlise,
            "linebreaksbr": mark_safe(linebreaksbr),
            "linebreaks": mark_safe(linebreaks),
            "is_favourited": is_favourited,
            "get_content_type_id": get_content_type_id,
            "custom_style_css": custom_style_css,
            "can_be_favourited": can_be_favourited,
        }
    )
    return env
