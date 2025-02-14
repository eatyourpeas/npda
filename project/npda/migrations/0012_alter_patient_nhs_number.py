# Generated by Django 5.1.1 on 2024-10-14 19:35

import project.npda.models.custom_validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("npda", "0011_alter_visitactivity_activity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="patient",
            name="nhs_number",
            field=models.CharField(
                validators=[project.npda.models.custom_validators.validate_nhs_number],
                verbose_name="NHS Number",
            ),
        ),
    ]
