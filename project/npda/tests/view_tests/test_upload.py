from datetime import datetime
import os
import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from project.npda.general_functions.data_generator_extended import (
    AgeRange,
    HbA1cTargetRange,
    VisitType,
)
from project.npda.models.npda_user import NPDAUser
from project.npda.tests.model_tests.test_submissions import ALDER_HEY_PZ_CODE
from project.npda.tests.utils import login_and_verify_user
from project.npda.management.commands.create_csv import Command as GenerateCSVCommand


@pytest.mark.django_db
def test_csv_upload_view(
    seed_groups_fixture,
    seed_users_fixture,
    client,
    tmpdir,
):
    """Use the generate csv function to assert basic behaviors for uploading
    csv.
    """

    # Get a user
    ah_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()
    client = login_and_verify_user(client, ah_user)

    # Define parameters for CSV generation
    audit_start_date = datetime(2024, 4, 1)
    audit_end_date = datetime(2025, 3, 31)
    n_pts_to_seed = 5
    age_range = AgeRange.AGE_11_15
    hba1c_target = HbA1cTargetRange.TARGET
    visits = "CDCD DHPC ACDC CDCD"
    visit_types = [
        VisitType.CLINIC,
        VisitType.DIETICIAN,
        VisitType.CLINIC,
        VisitType.DIETICIAN,
        VisitType.DIETICIAN,
        VisitType.HOSPITAL_ADMISSION,
        VisitType.PSYCHOLOGY,
        VisitType.CLINIC,
        VisitType.ANNUAL_REVIEW,
        VisitType.CLINIC,
        VisitType.DIETICIAN,
        VisitType.CLINIC,
        VisitType.CLINIC,
        VisitType.DIETICIAN,
        VisitType.CLINIC,
        VisitType.DIETICIAN,
    ]
    output_path = tmpdir.mkdir("csv_output")

    # Generate CSV
    file_path = os.path.join(output_path, f"npda_seed_data-{n_pts_to_seed}-{visits.replace(' ', '')}.csv")
    GenerateCSVCommand().generate_csv(
        audit_start_date=audit_start_date,
        audit_end_date=audit_end_date,
        n_pts_to_seed=n_pts_to_seed,
        age_range=age_range,
        hba1c_target=hba1c_target,
        visits=visits,
        visit_types=visit_types,
        output_path=str(output_path),
    )

    # Read the generated CSV for upload
    with open(file_path, "rb") as f:
        csv_file = SimpleUploadedFile(f.name, f.read(), content_type="text/csv")

    # Send POST request with CSV file
    url = reverse("home")
    response = client.post(url, {"csv_upload": csv_file})

    # Assert the response to ensure no error
    assert response.status_code == 302
