# Generated manually for ChangeNoteTag model and tags field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('busstops', '0012_add_custom_style'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChangeNoteTag',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text="Tag name (e.g., 'Bug Fix', 'Feature', 'Maintenance')", max_length=50, unique=True)),
                ('color', models.CharField(default='#2E8A9E', help_text='Hex color for the tag (e.g., #ff0000)', max_length=7)),
                ('description', models.TextField(blank=True, help_text='Optional description of what this tag represents')),
            ],
            options={
                'verbose_name': 'Change Note Tag',
                'verbose_name_plural': 'Change Note Tags',
                'ordering': ['name'],
            },
        ),
        migrations.AddField(
            model_name='changenote',
            name='tags',
            field=models.ManyToManyField(blank=True, help_text='Tags to categorize this change note', to='busstops.changenotetag'),
        ),
    ]
