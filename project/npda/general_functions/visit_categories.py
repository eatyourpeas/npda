import urllib.parse
from ...constants import VISIT_FIELDS, VISIT_TABS, VISIT_CATEGORY_COLOURS


def get_visit_categories(instance, form=None):
    """
    Returns visit categories present in this visit instance, and tags them as to whether they contain errors
    """
    categories = []
    for category, fields in VISIT_FIELDS:
        present = False
        errors = []

        # Data can be either:
        #  - On the bound form field after submitting the questionnaire
        if form:
            for field in form:
                if field.name in fields:
                    present = True
                    
                    if field.errors:
                        errors = field.errors

        #  - On the instance itself after a CSV upload
        for field in fields:
            if getattr(instance, field):
                present = True

        if instance.errors:
            for field in instance.errors.keys():
                if field in fields:
                    errors = [error["message"] for error in instance.errors[field]]

        categories.append(
            {
                "name": category.value,
                "present": present,
                "errors": errors,
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

        errors = []
        for category in categories:
            errors += category["errors"]

        tab = {
            "name": tab_name,
            "categories": categories,
            "errors": errors
        }

        tabs.append(tab)

    return tabs