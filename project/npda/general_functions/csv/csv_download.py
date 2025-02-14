import json

from django.apps import apps
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from ..write_errors_to_xlsx import write_errors_to_xlsx


def download_csv(request, submission_id):
    """
    Download a CSV file.
    """
    Submission = apps.get_model(app_label="npda", model_name="Submission")
    submission = get_object_or_404(Submission, id=submission_id)

    response = HttpResponse(submission.csv_file, content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="{submission.csv_file_name}"'
    )
    return response


def download_xlsx(request, submission_id):
    """
    Download a XLSX file.
    NB: This repurposes download_csv with a simple file rename.
    """
    Submission = apps.get_model(app_label="npda", model_name="Submission")
    submission = get_object_or_404(Submission, id=submission_id)

    filename_without_extension = ".".join(submission.csv_file_name.split(".")[:-1])
    xlsx_file_name = f"{filename_without_extension}_data_quality_report.xlsx"

    errors = {}
    if submission.errors:
        errors = json.loads(submission.errors)

    is_jersey = submission.paediatric_diabetes_unit.pz_code == "PZ248"

    xlsx_file = write_errors_to_xlsx(errors or {}, submission.csv_file, is_jersey)

    response = HttpResponse(xlsx_file, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{xlsx_file_name}"'
    return response
