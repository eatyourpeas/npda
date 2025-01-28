import urllib.parse
from ...constants import VISIT_FIELDS, VISIT_TABS, VISIT_CATEGORY_COLOURS


def get_visit_categories(instance, form=None):
    """
    Returns visit categories present in this visit instance, and tags them as to whether they contain errors
    """
    categories = []
    for category, fields in VISIT_FIELDS:
        category_present = False
        category_error_present = False

        # Data can be either:
        #  - On the bound form field after submitting the questionnaire
        if form:
            for field in form:
                if field.name in fields:
                    category_present = True
                    
                    if field.errors:
                        category_error_present = True

        #  - On the instance itself after a CSV upload
        for field in fields:
            if getattr(instance, field):
                category_present = True

        if instance.errors:
            for field in instance.errors.keys():
                if field in fields:
                    category_error_present = True

        categories.append(
            {
                "name": category.value,
                "present": category_present,
                "has_errors": category_error_present,
                "anchor": urllib.parse.quote_plus(category.value),
                "colour": VISIT_CATEGORY_COLOURS[category]
            }
        )
    return categories


def get_visit_tabs(form):
    tabs = []
    all_categories = get_visit_categories(form.instance, form)

    for tab_name, categories in VISIT_TABS:
        category_names = [c.value for c in categories]
        categories = [c for c in all_categories if c["name"] in category_names]

        tab = {
            "name": tab_name,
            "categories": categories,
            "has_errors": any([c["has_errors"] for c in categories])
        }

        tabs.append(tab)

    return tabs