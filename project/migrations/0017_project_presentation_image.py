from django.db import migrations, models

import project.models


class Migration(migrations.Migration):

    dependencies = [
        ('project', '0016_alter_project_progress'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='presentation_image',
            field=models.ImageField(
                blank=True,
                help_text=(
                    'Gambar hero/blueprint untuk showcase dan mode '
                    'presentasi client.'
                ),
                null=True,
                upload_to=project.models.upload_project_presentation,
            ),
        ),
    ]
