from django.core.management.base import BaseCommand
from busstops.models import CustomStyle


class Command(BaseCommand):
    help = 'Test custom style path matching'

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='Path to test (e.g., /operators/nasa)')

    def handle(self, path, **options):
        self.stdout.write(f"Testing path: {path}")
        self.stdout.write("-" * 50)
        
        # Get all active custom styles
        styles = CustomStyle.objects.filter(active=True)
        
        if not styles.exists():
            self.stdout.write(self.style.WARNING("No active custom styles found"))
            return
        
        self.stdout.write(f"Found {styles.count()} active custom styles:")
        
        for style in styles:
            self.stdout.write(f"\nStyle: {style.name}")
            self.stdout.write(f"  Date range: {style.start_date} to {style.end_date}")
            self.stdout.write(f"  Priority: {style.priority}")

            # Check if the new fields exist
            if hasattr(style, 'path_patterns'):
                self.stdout.write(f"  Path patterns: {repr(style.path_patterns)}")
                self.stdout.write(f"  Exact match: {style.exact_match}")

                # Determine if this is site-wide or path-specific
                is_site_wide = not (style.path_patterns and style.path_patterns.strip())
                self.stdout.write(f"  Type: {'Site-wide' if is_site_wide else 'Path-specific'}")

                # Test if it matches with detailed debugging
                matches = style.matches_path(path)
                self.stdout.write(f"  Matches path '{path}': {matches}")

                # Debug the matching logic step by step
                if style.path_patterns and style.path_patterns.strip():
                    patterns = []
                    for line in style.path_patterns.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
                        pattern = line.strip()
                        if pattern:
                            patterns.append(pattern)

                    self.stdout.write(f"  Parsed patterns: {patterns}")

                    for pattern in patterns:
                        if style.exact_match:
                            pattern_matches = (path == pattern)
                            self.stdout.write(f"    Pattern '{pattern}' (exact): {pattern_matches}")
                        else:
                            if '*' in pattern:
                                import fnmatch
                                pattern_matches = fnmatch.fnmatch(path, pattern)
                                self.stdout.write(f"    Pattern '{pattern}' (wildcard): {pattern_matches}")
                            else:
                                pattern_matches = path.startswith(pattern)
                                self.stdout.write(f"    Pattern '{pattern}' (prefix): {pattern_matches}")
                else:
                    self.stdout.write(f"  No patterns = site-wide style")

                if matches:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ This style would apply!"))
                else:
                    self.stdout.write(f"  ✗ This style would not apply")
            else:
                self.stdout.write(self.style.ERROR("  ERROR: path_patterns field not found - migration may not have run"))
        
        # Test the main method
        self.stdout.write(f"\n" + "="*50)

        # Test with current date
        from django.utils import timezone
        current_date = timezone.now().date()
        self.stdout.write(f"Current date: {current_date}")

        active_style = CustomStyle.get_active_style_for_date(path=path)

        if active_style:
            self.stdout.write(self.style.SUCCESS(f"Active style for path '{path}': {active_style.name}"))
            self.stdout.write(f"  Priority: {active_style.priority}")
            self.stdout.write(f"  Date range: {active_style.start_date} to {active_style.end_date}")
        else:
            self.stdout.write(self.style.WARNING(f"No active style found for path '{path}'"))

        # Also test what the context processor would return
        self.stdout.write(f"\n" + "-"*30)
        self.stdout.write("Context processor test:")

        # Simulate what happens in the context processor
        try:
            from busstops.context_processors import custom_styles

            class MockRequest:
                def __init__(self, path):
                    self.path = path

            mock_request = MockRequest(path)
            context = custom_styles(mock_request)

            if context.get('has_custom_style'):
                style = context.get('custom_style')
                self.stdout.write(self.style.SUCCESS(f"Context processor returns: {style.name if style else 'None'}"))
            else:
                self.stdout.write(self.style.WARNING("Context processor returns: No custom style"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Context processor error: {e}"))
