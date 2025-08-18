# Data migration to fix line endings in CustomStyle path_patterns

from django.db import migrations


def fix_line_endings(apps, schema_editor):
    """Fix Windows line endings in path_patterns"""
    CustomStyle = apps.get_model('busstops', 'CustomStyle')
    
    for style in CustomStyle.objects.all():
        if style.path_patterns:
            # Normalize line endings
            old_patterns = style.path_patterns
            new_patterns = old_patterns.replace('\r\n', '\n').replace('\r', '\n')
            
            if old_patterns != new_patterns:
                style.path_patterns = new_patterns
                style.save(update_fields=['path_patterns'])
                print(f"Fixed line endings for style: {style.name}")


def reverse_fix_line_endings(apps, schema_editor):
    """Reverse migration - no action needed"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('busstops', '0016_add_custom_style_path_targeting'),
    ]

    operations = [
        migrations.RunPython(fix_line_endings, reverse_fix_line_endings),
    ]
