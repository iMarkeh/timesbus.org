# Generated migration for cached display fields in Favourite model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('busstops', '0019_add_object_id_str_to_favourite'),
    ]

    operations = [
        migrations.AddField(
            model_name='favourite',
            name='display_name',
            field=models.CharField(blank=True, help_text='Cached display name for performance', max_length=255),
        ),
        migrations.AddField(
            model_name='favourite',
            name='display_subtitle',
            field=models.CharField(blank=True, help_text='Cached subtitle (e.g., NOC for operators)', max_length=255),
        ),
    ]