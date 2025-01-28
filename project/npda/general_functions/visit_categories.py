import urllib.parse
from ...constants import VISIT_FIELDS, VISIT_TABS, VISIT_CATEGORY_COLOURS


def get_visit_categories(visit_instance):
    """
    Returns visit categories present in this visit instance, and tags them as to whether they contain errors
    """
    categories = []
    for category in VISIT_FIELDS:
        category_present = False
        category_error_present = False
        for field in category[1]:
            if hasattr(visit_instance, field):
                if getattr(visit_instance, field) is not None:
                    category_present = True
                    errors = visit_instance.errors
                    if errors:
                        if field in errors:
                            category_error_present = True
        
        category_name = category[0].value

        categories.append(
            {
                "name": category_name,
                "present": category_present,
                "has_error": category_error_present,
                "anchor": urllib.parse.quote_plus(category_name),
                "colour": VISIT_CATEGORY_COLOURS[category[0]]
            }
        )
    return categories


def get_visit_tabs(visit_instance):
    tabs = []
    all_categories = get_visit_categories(visit_instance)

    for tab_name, categories in VISIT_TABS:
        category_names = [c.value for c in categories]
        categories = [c for c in all_categories if c["name"] in category_names]

        tab = {
            "name": tab_name,
            "categories": categories
        }

        tabs.append(tab)

    return tabs