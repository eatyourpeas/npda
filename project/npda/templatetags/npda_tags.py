import re
import itertools
import logging

from django import template, forms
from django.conf import settings
from ...constants import (
    VisitCategories,
    VISIT_FIELD_FLAT_LIST,
    VISIT_FIELDS,
    CSV_HEADING_OBJECTS,
    UNIQUE_IDENTIFIER_ENGLAND,
    UNIQUE_IDENTIFIER_JERSEY,
    VisitCategories,
)

from django.contrib.gis.measure import D
from datetime import date

register = template.Library()

logger = logging.getLogger(__name__)


@register.filter
def is_in(url_name, args):
    """
    receives the request.resolver_match.url_name
    and compares with the template name (can be a list in a string separated by commas),
    returning true if a match is present
    """
    if args is None:
        return None
    arg_list = [arg.strip() for arg in args.split(",")]
    if url_name in arg_list:
        return True
    else:
        return False


class_re = re.compile(r'(?<=class=["\'])(.*)(?=["\'])')


@register.filter
def colour_for_category(category):
    # returns a colour for a given category
    colours = [
        {"category": VisitCategories.HBA1, "colour": "rcpch_dark_grey"},
        {"category": VisitCategories.MEASUREMENT, "colour": "rcpch_yellow"},
        {
            "category": VisitCategories.TREATMENT,
            "colour": "rcpch_strong_green_light_tint1",
        },
        {"category": VisitCategories.CGM, "colour": "rcpch_aqua_green_light_tint1"},
        {"category": VisitCategories.BP, "colour": "rcpch_orange_light_tint1"},
        {"category": VisitCategories.FOOT, "colour": "rcpch_gold"},
        {"category": VisitCategories.DECS, "colour": "rcpch_vivid_green"},
        {"category": VisitCategories.ACR, "colour": "rcpch_red_light_tint2"},
        {"category": VisitCategories.CHOLESTEROL, "colour": "rcpch_orange_dark_tint"},
        {
            "category": VisitCategories.THYROID,
            "colour": "rcpch_red_dark_tint",
        },
        {"category": VisitCategories.COELIAC, "colour": "rcpch_purple_light_tint2"},
        {"category": VisitCategories.PSYCHOLOGY, "colour": "rcpch_yellow_dark_tint"},
        {"category": VisitCategories.SMOKING, "colour": "rcpch_strong_green_dark_tint"},
        {"category": VisitCategories.DIETETIAN, "colour": "rcpch_aqua_green_dark_tint"},
        {"category": VisitCategories.SICK_DAY, "colour": "rcpch_pink_light_tint2"},
        {"category": VisitCategories.FLU, "colour": "rcpch_orange"},
        {
            "category": VisitCategories.HOSPITAL_ADMISSION,
            "colour": "rcpch_strong_green_dark_tint",
        },
    ]
    for colour in colours:
        if colour["category"].value == category:
            return colour["colour"]
    return None


@register.simple_tag
def heading_for_field(pz_code, field):
    """
    Returns the heading for a given field
    """
    if pz_code == "PZ248":
        # Jersey
        CSV_HEADINGS = CSV_HEADING_OBJECTS + UNIQUE_IDENTIFIER_JERSEY
    else:
        # England
        CSV_HEADINGS = CSV_HEADING_OBJECTS + UNIQUE_IDENTIFIER_ENGLAND

    CSV_HEADINGS = [item["heading"] for item in CSV_HEADINGS]
    for item in CSV_HEADINGS:
        if field == item["model_field"]:
            return item["heading"]
    return None


@register.simple_tag
def centile_sds(field):
    """
    Returns the centile and SDS for a given field
    """
    if field.id_for_label == "id_height":
        centile = field.form.instance.height_centile
        sds = field.form.instance.height_sds
    elif field.id_for_label == "id_weight":
        centile = field.form.instance.weight_centile
        sds = field.form.instance.weight_sds
    elif field.id_for_label == "id_bmi":
        centile = field.form.instance.bmi_centile
        sds = field.form.instance.bmi_sds
    else:
        return None, None

    if centile is not None and centile >= 99.9:
        centile = " ≥99.6ᵗʰ"
    elif centile is not None and centile < 0.4:
        centile = "≤0.4ᵗʰ"
    return centile, sds


@register.filter
def join_with_comma(value):
    if isinstance(value, list):
        return ", ".join(map(str, value))
    return value


@register.simple_tag
def site_contact_email():
    return settings.SITE_CONTACT_EMAIL


@register.filter
def is_select(widget):
    return isinstance(widget, (forms.Select, forms.SelectMultiple))


@register.filter
def is_dateinput(widget):
    return isinstance(widget, (forms.DateInput))


@register.filter
def is_textinput(widget):
    return isinstance(widget, (forms.CharField, forms.TextInput, forms.EmailField))


@register.filter
def is_checkbox(widget):
    return isinstance(widget, (forms.CheckboxInput))


@register.filter
def is_emailfield(widget):
    return isinstance(widget, (forms.EmailField, forms.EmailInput))


@register.filter
def error_for_field(errors_by_field, field):
    """
    Returns all errors for a given field
    """
    if errors_by_field is None:
        return ""

    concatenated_fields = ""

    errors = errors_by_field[field] if field in errors_by_field else []

    error_messages = [error["message"] for error in errors]

    return "\n".join(error_messages)


@register.simple_tag
def today_date():
    return date.today().strftime("%Y-%m-%d")


@register.simple_tag
def patient_valid(patient):
    if not patient.is_valid or patient.visit_set.filter(is_valid=False).exists():
        return False
    else:
        return True


@register.simple_tag
def text_for_data_submission(can_upload_csv, can_complete_questionnaire):
    if can_upload_csv and can_complete_questionnaire:
        return "You can submit data by uploading a CSV or completing the questionnaire. Note that once you upload a CSV, you will not be able to complete the questionnaire. Once you complete the questionnaire, you will not be able to upload a CSV."
    elif can_upload_csv:
        return "You can only submit data by uploading a CSV. If you want to submit data via questionnaire, please contact the NPDA team."
    elif can_complete_questionnaire:
        return "You can only submit data by completing the questionnaire. If you want to submit data via CSV, please contact the NPDA team."
    else:
        return "You cannot upload a CSV or complete a questionnaire."


# Used to keep text highlighted in navbar for the tab that has been selected
@register.simple_tag
def active_navbar_tab(request, url_name):
    if request.resolver_match is not None:
        return (
            "text-rcpch_light_blue"
            if request.resolver_match.url_name == url_name
            else "text-gray-700"
        )
    else:
        # Some routes, such as Error 404, do not have resolver_match property.
        return "text-gray-700"


@register.filter
def join_by_comma(queryset):
    if len(queryset) == 0:
        return "No patients"
    return ", ".join(map(str, queryset.values_list("nhs_number", flat=True)))


@register.filter
def extract_digits(value, underscore_index=0):
    """
    Extracts all digits between the second or subsequent pair of _ characters in the string.
    """
    matches = re.findall(r"_(\d+)", value)
    if len(matches) > 0:
        return int(matches[underscore_index])
    return 0


@register.filter
def get_item(dictionary: dict, key: str):
    """Get a value using a variable from a dictionary"""
    return dictionary.get(key, "")

    try:
        return dictionary.get(key, "")
    except Exception:
        logger.error(f"Error getting value from dictionary: {dictionary=} {key=}")
        return ""


@register.simple_tag
def docs_url():
    return settings.DOCS_URL


@register.filter
def format_nhs_number(nhs_number):
    if nhs_number and len(nhs_number) >= 10:
        return f"{nhs_number[:3]} {nhs_number[3:6]} {nhs_number[6:]}"

    return nhs_number


@register.filter
def get_key_where_true(dictionary: dict) -> str:
    """Get the first key where the value is True.

    NOTE: as dictionaries are unordered, this will not always return the same key.
    So assumes only one key is True for reliable use.

    If no key is True, return an empty string.
    """
    for key, value in dictionary.items():
        if value:
            return key
    return ""


@register.simple_tag
def jersify(pz_code, field):
    """
    Tests to see if this field is rendered in a form with patients from Jersey
    If so will return unique reference number otherwise will return nhs number
    """
    if pz_code == "PZ248":
        # Jersey
        if (
            field.id_for_label == "id_unique_reference_number"
            or field.id_for_label != "id_nhs_number"
        ):
            return True
        else:
            return False
    else:
        if (
            field.id_for_label == "id_nhs_number"
            or field.id_for_label != "id_unique_reference_number"
        ):
            return True
        else:
            return False


@register.simple_tag
def nhs_number_vs_urn(pz_code, patient=None):
    """
    Tests to see if this field is rendered in a form with patients from Jersey
    If so will return unique reference number otherwise will return a formatted nhs number
    """
    if pz_code == "PZ248":
        if patient and patient.unique_reference_number:
            return patient.unique_reference_number
        # Jersey
        return "Unique Reference Number"
    else:
        if patient and patient.nhs_number:
            if len(patient.nhs_number) >= 10:
                return f"{patient.nhs_number[:3]} {patient.nhs_number[3:6]} {patient.nhs_number[6:]}"
            return patient.nhs_number
        return "NHS Number"


@register.simple_tag
def jersify_errors_for_unique_patient_identifier(
    pz_code, nhs_number_errors, unique_reference_number_errors
):
    """
    Visit errors depending on whether the patient is from Jersey or not
    """
    if pz_code == "PZ248":
        return unique_reference_number_errors
    else:
        return nhs_number_errors


@register.filter
def round_distance(value, decimal_places):
    if value is None:
        return "-"
    if isinstance(value, D):
        return round(value.km, decimal_places)
    return value


@register.filter
def tab_identifier(value):
    if value in [
        VisitCategories.MEASUREMENT.value,
        VisitCategories.HBA1.value,
        VisitCategories.TREATMENT.value,
        VisitCategories.CGM.value,
        VisitCategories.BP.value,
    ]:
        return "Routine Measurements".lower().replace(" ", "_")
    elif value in [
        VisitCategories.FOOT.value,
        VisitCategories.DECS.value,
        VisitCategories.ACR.value,
        VisitCategories.CHOLESTEROL.value,
        VisitCategories.THYROID.value,
        VisitCategories.COELIAC.value,
        VisitCategories.PSYCHOLOGY.value,
        VisitCategories.SMOKING.value,
        VisitCategories.DIETETIAN.value,
        VisitCategories.SICK_DAY.value,
        VisitCategories.FLU.value,
    ]:
        return "Annual Review".lower().replace(" ", "_")
    elif value in [VisitCategories.HOSPITAL_ADMISSION.value]:
        return "Inpatient Entry".lower().replace(" ", "_")


@register.filter
def lowerify(value):
    # replace spaces with underscores and make lowercase
    value = value.replace(" ", "_")
    return value.lower()


@register.filter
def flatten(values):
    return list(itertools.chain(*values))


@register.filter
def centile_for_field(field, centile_sds):
    """
    Returns the centile for a given field
    """
    if field.id_for_label == "id_height":
        centile = field.form.instance.height_centile
        sds = field.form.instance.height_sds
    elif field.id_for_label == "id_weight":
        centile = field.form.instance.weight_centile
        sds = field.form.instance.weight_sds
    elif field.id_for_label == "id_bmi":
        centile = field.form.instance.bmi_centile
        sds = field.form.instance.bmi_sds
    else:
        return ""

    if centile is not None:
        if centile >= 99.9:
            centile = "centile: ≥99.6ᵗʰ"
        elif centile < 0.4:
            centile = "centile: ≤0.4ᵗʰ"
        centile = f"centile {centile}"
    if sds is not None:
        sds = f"SDS: {sds}"
    else:
        sds = ""
        centile = ""

    if centile_sds == "centile":
        return centile
    elif centile_sds == "sds":
        return sds
    else:
        return ""
