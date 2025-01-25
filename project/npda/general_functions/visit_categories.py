from ...constants import VISIT_FIELDS


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
        categories.append(
            {
                "category": category[0].value,
                "present": category_present,
                "has_error": category_error_present,
            }
        )
    return categories

