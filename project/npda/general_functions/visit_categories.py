import urllib.parse
from ...constants.visit_categories import VISIT_CATEGORIES_BY_TAB

def get_visit_categories(instance, form):
    """
    Returns visit categories present in this visit instance, and tags them as to whether they contain errors
    """
    categories = []

    for _, tab in VISIT_CATEGORIES_BY_TAB.items():
        for category_name, category in tab.items():
            fields = category["fields"]

            present = False
            errors = {}

            # Data can be either:
            #  - On the bound form field after submitting the questionnaire
            if form:
                for field in form:
                    if field.name in fields:
                        present = True
                        
                        if field.errors:
                            errors[field.name] = field.errors

            #  - On the instance itself after a CSV upload
            if instance:
                for field in fields:
                    if getattr(instance, field):
                        present = True

                if instance.errors:
                    for field in instance.errors.keys():
                        if field in fields:
                            errors[field] = [error["message"] for error in instance.errors[field]]

            categories.append(
                {
                    "name": category_name,
                    "present": present,
                    "errors": errors,
                    "anchor": urllib.parse.quote_plus(category_name),
                    "colour": category["colour"]
                }
            )

    return categories


def get_visit_tabs(form):
    tabs = []
    instance = form.instance if form else None

    all_categories = get_visit_categories(instance, form)

    assigned_active_tab = False

    for tab_name, categories in VISIT_CATEGORIES_BY_TAB.items():
        category_names = categories.keys()
        categories = [c for c in all_categories if c["name"] in category_names]

        errors = {}
        for category in categories:
            for field, field_errors in category["errors"].items():
                errors[field] = field_errors

        tab = {
            "name": tab_name,
            "categories": categories,
            "errors": errors
        }

        # Show the first tab with errors
        if errors and not assigned_active_tab:
            tab["active"] = True
            assigned_active_tab = True

        tabs.append(tab)
    
    # Otherwise show the first one
    if not assigned_active_tab:
        tabs[0]["active"] = True

    return tabs