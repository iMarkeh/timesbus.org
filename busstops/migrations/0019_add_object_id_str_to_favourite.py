# Generated manually to add string object_id support to Favourite model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('busstops', '0018_add_favourite_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='favourite',
            name='object_id_str',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AlterField(
            model_name='favourite',
            name='object_id',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='favourite',
            unique_together={('user', 'content_type', 'object_id', 'object_id_str')},
        ),
    ]