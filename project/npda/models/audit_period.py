from django.contrib.gis.db import models
from django.core.exceptions import ValidationError

class AuditPeriod(models.Model):
    is_open = models.BooleanField()
    start_date = models.DateField()
    end_date = models.DateField()

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError("Audit start date must be before the audit end date.")

    def __str__(self):
        return f"AuditPeriod {self.start_date} - {self.end_date}"