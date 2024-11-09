import pytest
from unittest.mock import AsyncMock, patch

from httpx import HTTPError
from django.core.exceptions import ValidationError

from project.npda.tests.factories.patient_factory import (
    VALID_FIELDS,
    VALID_FIELDS_WITH_GP_POSTCODE,
    INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE,
    GP_POSTCODE_WITH_SPACES
)

from project.npda.forms.external_patient_validators import validate_patient_async

async_client = AsyncMock()

MOCK_GP_DETAILS_FOR_ODS_CODE = {
    "GeoLoc": {
        "Location": {
            "PostCode": VALID_FIELDS_WITH_GP_POSTCODE["gp_practice_postcode"]
        }
    }
}

# We don't want to call remote services in unit tests
@pytest.fixture(autouse=True)
def mock_remote_calls():
    with patch("project.npda.forms.external_patient_validators.validate_postcode", AsyncMock(return_value=VALID_FIELDS["postcode"])):
        with patch("project.npda.forms.external_patient_validators.gp_details_for_ods_code", AsyncMock(return_value=MOCK_GP_DETAILS_FOR_ODS_CODE)):
            with patch("project.npda.forms.external_patient_validators.gp_ods_code_for_postcode", AsyncMock(return_value=VALID_FIELDS["gp_practice_ods_code"])):
                with patch("project.npda.forms.external_patient_validators.imd_for_postcode", AsyncMock(return_value=INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE)):
                    yield None


async def test_validate_patient():
    result = await validate_patient_async(
        postcode=VALID_FIELDS["postcode"],
        gp_practice_ods_code=VALID_FIELDS["gp_practice_ods_code"],
        gp_practice_postcode=None,
        async_client=async_client
    )

    assert(result.postcode == VALID_FIELDS["postcode"])
    assert(result.gp_practice_ods_code == VALID_FIELDS["gp_practice_ods_code"])
    assert(result.gp_practice_postcode == VALID_FIELDS_WITH_GP_POSTCODE["gp_practice_postcode"])
    assert(result.index_of_multiple_deprivation_quintile == INDEX_OF_MULTIPLE_DEPRIVATION_QUINTILE)


async def test_invalid_postcode():
    with patch("project.npda.forms.external_patient_validators.validate_postcode", AsyncMock(return_value=None)):
        result = await validate_patient_async(
            postcode="INVALID",
            gp_practice_ods_code=None,
            gp_practice_postcode=None,
            async_client=async_client
        )

        assert(type(result.postcode) is ValidationError)


async def test_http_error_validating_postcode():
    with patch("project.npda.forms.external_patient_validators.validate_postcode", AsyncMock(side_effect=HTTPError("oopsie!"))):
        result = await validate_patient_async(
            postcode="INVALID",
            gp_practice_ods_code=None,
            gp_practice_postcode=None,
            async_client=async_client
        )

        assert(result.postcode is None)


async def test_unexpected_error_validating_postcode():
    with patch("project.npda.forms.external_patient_validators.validate_postcode", AsyncMock(side_effect=RuntimeError("oopsie!"))):
        with pytest.raises(RuntimeError):
            await validate_patient_async(
                postcode=VALID_FIELDS["postcode"],
                gp_practice_ods_code=None,
                gp_practice_postcode=None,
                async_client=async_client
            )


async def test_invalid_postcode_for_index_of_multiple_deprivation():
    with patch("project.npda.forms.external_patient_validators.imd_for_postcode", AsyncMock(return_value=None)):
        result = await validate_patient_async(
            postcode="INVALID",
            gp_practice_ods_code=None,
            gp_practice_postcode=None,
            async_client=async_client
        )

        assert(result.index_of_multiple_deprivation_quintile is None)


async def test_http_error_calculating_index_of_multiple_deprivation():
    with patch("project.npda.forms.external_patient_validators.imd_for_postcode", AsyncMock(side_effect=HTTPError("oopsie!"))):
        result = await validate_patient_async(
            postcode=VALID_FIELDS["postcode"],
            gp_practice_ods_code=None,
            gp_practice_postcode=None,
            async_client=async_client
        )

        assert(result.index_of_multiple_deprivation_quintile is None)


async def test_http_error_calculating_index_of_multiple_deprivation():
    with patch("project.npda.forms.external_patient_validators.imd_for_postcode", AsyncMock(side_effect=RuntimeError("oopsie!"))):
        with pytest.raises(RuntimeError):
            await validate_patient_async(
                postcode=VALID_FIELDS["postcode"],
                gp_practice_ods_code=None,
                gp_practice_postcode=None,
                async_client=async_client
            )


async def test_validate_patient_with_gp_practice_ods_code():
    result = await validate_patient_async(
        postcode=None,
        gp_practice_ods_code=VALID_FIELDS["gp_practice_ods_code"],
        gp_practice_postcode=None,
        async_client=async_client
    )

    assert(result.gp_practice_ods_code == VALID_FIELDS["gp_practice_ods_code"])
    assert(result.gp_practice_postcode == VALID_FIELDS_WITH_GP_POSTCODE["gp_practice_postcode"])


async def test_invalid_gp_practice_ods_code():
    with patch("project.npda.forms.external_patient_validators.gp_details_for_ods_code", AsyncMock(return_value=None)):
        result = await validate_patient_async(
            postcode=None,
            gp_practice_ods_code="INVALID",
            gp_practice_postcode=None,
            async_client=async_client
        )

        assert(type(result.gp_practice_ods_code) is ValidationError)


async def test_http_error_validating_gp_practice_ods_code():
    with patch("project.npda.forms.external_patient_validators.gp_details_for_ods_code", AsyncMock(side_effect=HTTPError("oopsie!"))):
        result = await validate_patient_async(
            postcode=None,
            gp_practice_ods_code=VALID_FIELDS["gp_practice_ods_code"],
            gp_practice_postcode=None,
            async_client=async_client
        )

        assert(result.gp_practice_ods_code is None)


async def test_unexpected_error_validating_gp_practice_ods_code():
    with patch("project.npda.forms.external_patient_validators.gp_details_for_ods_code", AsyncMock(side_effect=RuntimeError("oopsie!"))):
        with pytest.raises(RuntimeError):
            await validate_patient_async(
                postcode=None,
                gp_practice_ods_code=VALID_FIELDS["gp_practice_ods_code"],
                gp_practice_postcode=None,
                async_client=async_client
            )


@patch("project.npda.forms.external_patient_validators.validate_postcode", AsyncMock(return_value=VALID_FIELDS_WITH_GP_POSTCODE["gp_practice_postcode"]))
async def test_validate_patient_with_gp_practice_postcode():
    result = await validate_patient_async(
        postcode=None,
        gp_practice_ods_code=None,
        gp_practice_postcode=VALID_FIELDS_WITH_GP_POSTCODE["gp_practice_postcode"],
        async_client=async_client
    )

    assert(result.gp_practice_ods_code == VALID_FIELDS["gp_practice_ods_code"])
    assert(result.gp_practice_postcode == VALID_FIELDS_WITH_GP_POSTCODE["gp_practice_postcode"])


async def test_normalised_postcode_used_for_call_to_nhs_spine():
    # The NHS API only returns results if you have a space between the parts of the postcode
    with patch("project.npda.forms.external_patient_validators.validate_postcode", AsyncMock(return_value=GP_POSTCODE_WITH_SPACES)):
        with patch("project.npda.forms.external_patient_validators.gp_ods_code_for_postcode") as mock_gp_ods_code_for_postcode:
            result = await validate_patient_async(
                postcode=None,
                gp_practice_ods_code=None,
                gp_practice_postcode=VALID_FIELDS_WITH_GP_POSTCODE["gp_practice_postcode"],
                async_client=async_client
            )

            mock_gp_ods_code_for_postcode.assert_called_once_with(GP_POSTCODE_WITH_SPACES, async_client)

            assert(result.gp_practice_postcode == GP_POSTCODE_WITH_SPACES)


async def test_invalid_gp_practice_postcode():
    with patch("project.npda.forms.external_patient_validators.gp_ods_code_for_postcode", AsyncMock(return_value=None)):
        result = await validate_patient_async(
            postcode=None,
            gp_practice_ods_code=None,
            gp_practice_postcode="INVALID",
            async_client=async_client
        )

        assert(type(result.gp_practice_postcode) is ValidationError)


async def test_http_error_validating_gp_practice_postcode():
    with patch("project.npda.forms.external_patient_validators.gp_ods_code_for_postcode", AsyncMock(side_effect=HTTPError("oopsie!"))):
        result = await validate_patient_async(
            postcode=None,
            gp_practice_ods_code=None,
            gp_practice_postcode=VALID_FIELDS_WITH_GP_POSTCODE["gp_practice_postcode"],
            async_client=async_client
        )

        assert(result.gp_practice_postcode is None)


async def test_unexpected_error_validating_gp_practice_postcode():
    with patch("project.npda.forms.external_patient_validators.gp_ods_code_for_postcode", AsyncMock(side_effect=RuntimeError("oopsie!"))):
        with pytest.raises(RuntimeError):
            await validate_patient_async(
                postcode=None,
                gp_practice_ods_code=None,
                gp_practice_postcode=VALID_FIELDS_WITH_GP_POSTCODE["gp_practice_postcode"],
                async_client=async_client
            )
