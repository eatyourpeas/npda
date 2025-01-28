import re
import itertools
import logging

from django import template, forms
from django.conf import settings
from ...constants import CSV_HEADINGS

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
def heading_for_field(field):
    """
    Returns the heading for a given field
    """
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


@register.filter
def round_distance(value, decimal_places):
    if value is None:
        return "-"
    if isinstance(value, D):
        return round(value.km, decimal_places)
    return value


@register.filter
def lowerify(value):
    # replace spaces with underscores and make lowercase
    value = value.replace(" ", "_")
    return value.lower()


@register.filter
def flatten(values):
    return list(itertools.chain(*values))