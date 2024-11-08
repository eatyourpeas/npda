# python imports
from datetime import date

# django imports
from django.apps import apps

# third part imports
import pandas as pd

# RCPCH imports
from ...constants.csv_headings import (
    ALL_DATES,
)


def csv_summarize(dataframe):
    """
    This function takes a csv file and processes the file to create a summary of the data
    It returns a dictionary with the status of the operation and the summary data
    """
    Patient = apps.get_model("npda", "Patient")

    total_records = len(dataframe)
    number_unique_nhs_numbers = dataframe["NHS Number"].nunique()
    unique_nhs_numbers_no_spaces = (
        dataframe["NHS Number"].fillna("").apply(lambda x: str(x).replace(" ", "")).unique()
    )
    count_of_records_per_nhs_number = dataframe["NHS Number"].value_counts()
    matching_patients_in_current_audit_year = Patient.objects.filter(
        nhs_number__in=list(unique_nhs_numbers_no_spaces),
        submissions__submission_active=True,
        submissions__audit_year=date.today().year,
    ).count()

    summary = {
        "total_records": total_records,
        "number_unique_nhs_numbers": number_unique_nhs_numbers,
        "count_of_records_per_nhs_number": list(
            count_of_records_per_nhs_number.items()
        ),
        "matching_patients_in_current_audit_year": matching_patients_in_current_audit_year,
    }

    return summary
