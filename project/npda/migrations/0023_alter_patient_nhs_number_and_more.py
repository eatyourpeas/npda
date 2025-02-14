# Generated by Django 5.1.5 on 2025-01-24 23:32

import project.npda.models.custom_validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("npda", "0022_alter_patient_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="patient",
            name="nhs_number",
            field=models.CharField(
                blank=True,
                help_text="This is the NHS number for England and Wales. It is used to identify the patient in the audit.",
                null=True,
                validators=[project.npda.models.custom_validators.validate_nhs_number],
                verbose_name="NHS Number",
            ),
        ),
        migrations.AlterField(
            model_name="patient",
            name="unique_reference_number",
            field=models.CharField(
                blank=True,
                help_text="This is a unique reference number for Jersey patients. It is used to identify the patient in the audit.",
                max_length=50,
                null=True,
                verbose_name="Unique Reference Number",
            ),
        ),
    ]
