from datetime import datetime
import os
import pytest
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command


from project.npda.models.npda_user import NPDAUser
from project.npda.tests.model_tests.test_submissions import ALDER_HEY_PZ_CODE
from project.npda.tests.utils import login_and_verify_user
from project.npda.tests.test_csv_upload import mock_remote_calls


# @pytest.mark.skip(reason="CSV upload validation errors")
@pytest.mark.django_db
def test_generate_csv_upload_to_view(
    seed_groups_fixture,
    seed_users_fixture,
    client,
    mock_remote_calls,
    tmpdir,
):
    """Integration test for CSV generation and upload to home view.

    Use the generate csv manage.py cmd to create a CSV file and upload it to
    the home view.

    Mocks remote calls.
    """

    # Get a user
    ah_user = NPDAUser.objects.filter(
        organisation_employers__pz_code=ALDER_HEY_PZ_CODE
    ).first()
    client = login_and_verify_user(client, ah_user)

    # Directory to store generated CSV files
    tmpdir_path = str(tmpdir)

    # Simulate `create_csv` commands
    call_command(
        "create_csv",
        pts=5,
        visits="CDCD DHPC ACDC CDCD",
        hb_target="T",
        age_range="11_15",
        build=True,
        output_path=tmpdir_path,
    )
    call_command(
        "create_csv",
        pts=5,
        visits="CDCCD DDCC CACC",
        hb_target="A",
        age_range="16_19",
        build=True,
        output_path=tmpdir_path,
    )
    call_command(
        "create_csv",
        pts=5,
        visits="CDC ACDC CDCD",
        hb_target="T",
        age_range="0_4",
        build=True,
        output_path=tmpdir_path,
    )
    call_command(
        "create_csv",
        coalesce=True,
        output_path=tmpdir_path,
    )

    # Read the generated coalesced CSV for upload
    tmp_dir_filenames = os.listdir(tmpdir_path)
    coalesced_csv_name = next(
        (file for file in tmp_dir_filenames if file.startswith("coalesced_")),
        None,
    )
    coalesced_csv_path = os.path.join(tmpdir_path, coalesced_csv_name)
    assert os.path.exists(coalesced_csv_path), "CSV file not generated"

    with open(coalesced_csv_path, "rb") as f:
        csv_file = SimpleUploadedFile(
            f.name, f.read(), content_type="text/csv"
        )

    # Send POST request with CSV file
    url = reverse("home")
    response = client.post(url, {"csv_upload": csv_file})

    # Assert the response to ensure no error
    assert response.status_code == 302
