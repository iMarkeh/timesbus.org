# Data migration to add default change note tags

from django.db import migrations


def create_default_tags(apps, schema_editor):
    """Create some useful default tags for change notes"""
    ChangeNoteTag = apps.get_model('busstops', 'ChangeNoteTag')
    
    default_tags = [
        {'name': 'Bug Fix', 'color': '#dc3545', 'description': 'Fixes for bugs and issues'},
        {'name': 'Feature', 'color': '#28a745', 'description': 'New features and functionality'},
        {'name': 'Improvement', 'color': '#007bff', 'description': 'Enhancements to existing features'},
        {'name': 'Maintenance', 'color': '#6c757d', 'description': 'Routine maintenance and updates'},
        {'name': 'Data Update', 'color': '#17a2b8', 'description': 'Updates to data sources or content'},
        {'name': 'Performance', 'color': '#fd7e14', 'description': 'Performance improvements and optimizations'},
        {'name': 'Security', 'color': '#e83e8c', 'description': 'Security-related changes'},
        {'name': 'UI/UX', 'color': '#6f42c1', 'description': 'User interface and experience improvements'},
    ]
    
    for tag_data in default_tags:
        ChangeNoteTag.objects.get_or_create(
            name=tag_data['name'],
            defaults={
                'color': tag_data['color'],
                'description': tag_data['description']
            }
        )


def remove_default_tags(apps, schema_editor):
    """Remove the default tags (reverse migration)"""
    ChangeNoteTag = apps.get_model('busstops', 'ChangeNoteTag')
    
    default_tag_names = [
        'Bug Fix', 'Feature', 'Improvement', 'Maintenance', 
        'Data Update', 'Performance', 'Security', 'UI/UX'
    ]
    
    ChangeNoteTag.objects.filter(name__in=default_tag_names).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('busstops', '0013_add_change_note_tags'),
    ]

    operations = [
        migrations.RunPython(create_default_tags, remove_default_tags),
    ]
