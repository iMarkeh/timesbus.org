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
                
                # Test if it matches
                matches = style.matches_path(path)
                self.stdout.write(f"  Matches path '{path}': {matches}")
                
                if matches:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ This style would apply!"))
                else:
                    self.stdout.write(f"  ✗ This style would not apply")
            else:
                self.stdout.write(self.style.ERROR("  ERROR: path_patterns field not found - migration may not have run"))
        
        # Test the main method
        self.stdout.write(f"\n" + "="*50)
        active_style = CustomStyle.get_active_style_for_date(path=path)
        
        if active_style:
            self.stdout.write(self.style.SUCCESS(f"Active style for path '{path}': {active_style.name}"))
        else:
            self.stdout.write(self.style.WARNING(f"No active style found for path '{path}'"))
