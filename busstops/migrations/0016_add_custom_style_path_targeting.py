# Generated manually for CustomStyle path targeting

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('busstops', '0015_add_notification_banner'),
    ]

    operations = [
        migrations.AddField(
            model_name='customstyle',
            name='path_patterns',
            field=models.TextField(blank=True, help_text='URL path patterns, one per line (e.g., "/operators/nasa", "/vehicles/nasa-*"). Leave blank for site-wide styling.'),
        ),
        migrations.AddField(
            model_name='customstyle',
            name='exact_match',
            field=models.BooleanField(default=False, help_text='If checked, paths must match exactly. If unchecked, style applies if URL starts with any pattern.'),
        ),
    ]
