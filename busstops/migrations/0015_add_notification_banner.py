# Generated manually for NotificationBanner model

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('busstops', '0014_add_default_change_note_tags'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationBanner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Internal name for this banner (e.g., 'OXBC Service Disruption')", max_length=100)),
                ('message', models.TextField(help_text='Banner message to display to users')),
                ('banner_type', models.CharField(choices=[('info', 'Info (Blue)'), ('warning', 'Warning (Orange)'), ('error', 'Error (Red)'), ('success', 'Success (Green)')], default='info', help_text='Banner style/color', max_length=10)),
                ('path_pattern', models.CharField(blank=True, help_text="URL path pattern (e.g., '/operators/oxbc', '/services/1-*', '/vehicles'). Leave blank for site-wide banner.", max_length=255)),
                ('exact_match', models.BooleanField(default=False, help_text='If checked, path must match exactly. If unchecked, banner shows if URL starts with this pattern.')),
                ('start_datetime', models.DateTimeField(help_text='When to start showing this banner')),
                ('end_datetime', models.DateTimeField(blank=True, help_text='When to stop showing this banner (leave blank for indefinite)', null=True)),
                ('active', models.BooleanField(default=True, help_text='Whether this banner is active')),
                ('dismissible', models.BooleanField(default=True, help_text='Whether users can dismiss this banner')),
                ('priority', models.IntegerField(default=0, help_text='Higher numbers show first (if multiple banners match)')),
                ('link_text', models.CharField(blank=True, help_text="Optional link text (e.g., 'More Info')", max_length=100)),
                ('link_url', models.URLField(blank=True, help_text='Optional link URL')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Notification Banner',
                'verbose_name_plural': 'Notification Banners',
                'ordering': ['-priority', '-start_datetime'],
            },
        ),
    ]
