# Generated manually for CustomStyle model

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('busstops', '0011_changenote_datetime_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomStyle',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Name for this custom style (e.g., 'Christmas 2024', 'Halloween')", max_length=100)),
                ('start_date', models.DateField(help_text='Start date for this custom style')),
                ('end_date', models.DateField(help_text='End date for this custom style')),
                ('light_logo_url', models.URLField(blank=True, help_text='Custom logo URL for light mode')),
                ('light_banner_url', models.URLField(blank=True, help_text='Custom banner background URL for light mode')),
                ('light_brand_color', models.CharField(blank=True, help_text='Custom brand color for light mode (hex)', max_length=7)),
                ('light_brand_color_darker', models.CharField(blank=True, help_text='Custom darker brand color for light mode (hex)', max_length=7)),
                ('dark_logo_url', models.URLField(blank=True, help_text='Custom logo URL for dark mode')),
                ('dark_banner_url', models.URLField(blank=True, help_text='Custom banner background URL for dark mode')),
                ('dark_brand_color', models.CharField(blank=True, help_text='Custom brand color for dark mode (hex)', max_length=7)),
                ('dark_brand_color_darker', models.CharField(blank=True, help_text='Custom darker brand color for dark mode (hex)', max_length=7)),
                ('additional_css', models.TextField(blank=True, help_text='Additional CSS to inject (advanced users only)')),
                ('active', models.BooleanField(default=True, help_text='Whether this custom style is active')),
                ('priority', models.IntegerField(default=0, help_text='Priority (higher numbers take precedence if dates overlap)')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Custom Style',
                'verbose_name_plural': 'Custom Styles',
                'ordering': ['-priority', '-start_date'],
            },
        ),
    ]
