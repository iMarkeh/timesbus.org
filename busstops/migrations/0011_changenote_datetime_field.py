# Generated migration to change ChangeNote.date to ChangeNote.datetime

from django.db import migrations, models
import django.utils.timezone
from datetime import datetime, time


def copy_date_to_datetime(apps, schema_editor):
    """Copy existing date values to the new datetime field"""
    ChangeNote = apps.get_model('busstops', 'ChangeNote')
    for note in ChangeNote.objects.all():
        # Convert date to datetime at midnight
        note.datetime = django.utils.timezone.make_aware(
            datetime.combine(note.date, time.min)
        )
        note.save()


def copy_datetime_to_date(apps, schema_editor):
    """Reverse migration: copy datetime back to date"""
    ChangeNote = apps.get_model('busstops', 'ChangeNote')
    for note in ChangeNote.objects.all():
        note.date = note.datetime.date()
        note.save()


class Migration(migrations.Migration):

    dependencies = [
        ('busstops', '0010_changenote'),
    ]

    operations = [
        # Add the new datetime field (nullable initially)
        migrations.AddField(
            model_name='changenote',
            name='datetime',
            field=models.DateTimeField(null=True, blank=True),
        ),
        # Copy data from date field to datetime field
        migrations.RunPython(copy_date_to_datetime, copy_datetime_to_date),
        # Make datetime field non-nullable (auto_now_add only works on creation)
        migrations.AlterField(
            model_name='changenote',
            name='datetime',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        # Remove the old date field
        migrations.RemoveField(
            model_name='changenote',
            name='date',
        ),
        # Update the Meta ordering
        migrations.AlterModelOptions(
            name='changenote',
            options={'ordering': ['-datetime']},
        ),
    ]
