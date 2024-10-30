import re
import itertools
from django import template, forms
from django.conf import settings
from ..general_functions import get_visit_category_for_field
from ...constants import VisitCategories, VISIT_FIELD_FLAT_LIST, VISIT_FIELDS
from datetime import date

register = template.Library()


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
def match_category(value):
    """
    matches a category to a field in the visit form
    """
    field_name = value.name
    visit_category = get_visit_category_for_field(field_name=field_name)
    if visit_category:
        return visit_category.value
    else:
        return None


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
        {"category": VisitCategories.SICK_DAY, "colour": "rcpch_purple_dark_tint"},
        {"category": VisitCategories.FLU, "colour": "rcpch_orange"},
        {"category": VisitCategories.HOSPITAL_ADMISSION, "colour": "rcpch_red"},
    ]
    for colour in colours:
        if colour["category"].value == category:
            return colour["colour"]
    return None


@register.simple_tag
def category_for_first_item(form, field, index):
    """
    Return categories only for those first fields in the category
    """
    if index < 3:
        if index == 2:
            current_visit_category = get_visit_category_for_field(field_name=field.name)
            return current_visit_category.value
        return ""

    current_visit_category = get_visit_category_for_field(field_name=field.name)
    if field.name == "visit_date":
        return ""

    previous_field = list(form)[index - 2]
    previous_visit_category = get_visit_category_for_field(
        field_name=previous_field.name
    )

    if current_visit_category == previous_visit_category:
        return ""
    else:
        return current_visit_category.value


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

    if field in VISIT_FIELD_FLAT_LIST:
        return "There are errors associated with one or more of this child's visits."

    errors = errors_by_field[field] if field in errors_by_field else []

    error_messages = [error["message"] for error in errors]

    return "\n".join(error_messages)


@register.filter
def errors_for_category(selected_category, errors_by_field):
    """
    Returns all error messages for a given category
    """

    # VISIT_FIELDS: (VisitCategory -> [string])
    # Get the first or default to the empty list
    fields_in_category = next(
        (
            fields
            for (category, fields) in VISIT_FIELDS
            if category.value == selected_category
        ),
        [],
    )

    # errors_by_field: { [string] -> [{ message: string }]}
    errors = [
        errors
        for (field, errors) in errors_by_field.items()
        if field in fields_in_category
    ]

    # flatten
    errors = itertools.chain(*errors)

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

@register.simple_tag
def docs_url():
    return settings.DOCS_URL
