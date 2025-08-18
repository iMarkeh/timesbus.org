from django.core.management.base import BaseCommand
from busstops.models import CustomStyle


class Command(BaseCommand):
    help = 'Fix line endings in CustomStyle path_patterns'

    def handle(self, **options):
        self.stdout.write("Fixing line endings in CustomStyle path_patterns...")
        
        fixed_count = 0
        
        for style in CustomStyle.objects.all():
            if style.path_patterns:
                old_patterns = style.path_patterns
                # Normalize line endings
                new_patterns = old_patterns.replace('\r\n', '\n').replace('\r', '\n')
                
                if old_patterns != new_patterns:
                    self.stdout.write(f"Fixing style: {style.name}")
                    self.stdout.write(f"  Old: {repr(old_patterns)}")
                    self.stdout.write(f"  New: {repr(new_patterns)}")
                    
                    style.path_patterns = new_patterns
                    style.save(update_fields=['path_patterns'])
                    fixed_count += 1
                else:
                    self.stdout.write(f"Style '{style.name}' already has correct line endings")
        
        if fixed_count > 0:
            self.stdout.write(self.style.SUCCESS(f"Fixed {fixed_count} custom styles"))
        else:
            self.stdout.write("No custom styles needed fixing")
            
        # Test the patterns after fixing
        self.stdout.write("\nTesting patterns after fix:")
        for style in CustomStyle.objects.filter(path_patterns__isnull=False).exclude(path_patterns=''):
            self.stdout.write(f"\nStyle: {style.name}")
            self.stdout.write(f"  Patterns: {repr(style.path_patterns)}")
            
            # Test some common paths
            test_paths = ['/operators/nasa', '/vehicles/nasa-iss', '/']
            for path in test_paths:
                matches = style.matches_path(path)
                self.stdout.write(f"  Path '{path}': {'✓' if matches else '✗'}")
