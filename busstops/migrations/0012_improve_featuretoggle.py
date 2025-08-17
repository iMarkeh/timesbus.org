# Generated migration to improve FeatureToggle model

from django.db import migrations, models
import django.core.validators
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('busstops', '0011_changenote_datetime_field'),
    ]

    operations = [
        # Add new fields
        migrations.AddField(
            model_name='featuretoggle',
            name='maintenance_message',
            field=models.TextField(blank=True, help_text='Custom message to display during maintenance'),
        ),
        migrations.AddField(
            model_name='featuretoggle',
            name='estimated_hours',
            field=models.PositiveIntegerField(blank=True, default=0, help_text='Estimated hours until feature is back online', null=True),
        ),
        migrations.AddField(
            model_name='featuretoggle',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='featuretoggle',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        
        # Update existing fields with better help text
        migrations.AlterField(
            model_name='featuretoggle',
            name='name',
            field=models.CharField(help_text="Feature identifier (e.g., 'site_maintenance', 'new_feature')", max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='featuretoggle',
            name='enabled',
            field=models.BooleanField(default=True, help_text='Whether this feature is enabled'),
        ),
        migrations.AlterField(
            model_name='featuretoggle',
            name='maintenance',
            field=models.BooleanField(default=False, help_text='Whether this feature is in maintenance mode'),
        ),
        migrations.AlterField(
            model_name='featuretoggle',
            name='super_user_only',
            field=models.BooleanField(default=False, help_text='Only superusers can access this feature'),
        ),
        migrations.AlterField(
            model_name='featuretoggle',
            name='coming_soon',
            field=models.BooleanField(default=False, help_text='Whether this feature is coming soon'),
        ),
        migrations.AlterField(
            model_name='featuretoggle',
            name='coming_soon_percent',
            field=models.IntegerField(blank=True, default=0, help_text='Percentage for gradual rollout (0-100)', null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)]),
        ),
        
        # Update model meta options
        migrations.AlterModelOptions(
            name='featuretoggle',
            options={'ordering': ['name'], 'verbose_name': 'Feature Toggle', 'verbose_name_plural': 'Feature Toggles'},
        ),
    ]
