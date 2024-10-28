from datetime import date


def retrieve_quarter_for_date(date_instance: date) -> int:
    """
    Returns the quarter number of the patient for a given submission date (today)

    A quarter simply is defined as the quarter of the audit year the submission date lies in

    **The audit year starts on the 1st of April and ends on the 31st of March the following year**
    quarter 1: 1st April - 30th June
    quarter 2: 1st July - 30th September
    quarter 3: 1st October - 31st December
    quarter 4: 1st January - 31st March
    """
    # Audit start date is on the 1st April every year
    audit_start_date = date(date_instance.year, 4, 1)
    if date_instance < audit_start_date:
        # The patient was audited in the previous year
        quarter_2 = date(date_instance.year - 1, 7, 1)
        quarter_3 = date(date_instance.year - 1, 10, 1)
        quarter_4 = date(date_instance.year, 1, 1)
    else:
        # The patient was audited in the current year
        # Audit end date is on the 31st of March of every year
        quarter_2 = date(date_instance.year, 7, 1)
        quarter_3 = date(date_instance.year, 10, 1)
        quarter_4 = date(date_instance.year + 1, 1, 1)

    if date_instance < quarter_2:
        return 1
    elif date_instance < quarter_3:
        return 2
    elif date_instance < quarter_4:
        return 3
    else:
        return 4


def current_audit_year_start_date(date_instance: date) -> date:
    """
    Returns the start date of the current audit year for a given submission date (today)

    **The audit year starts on the 1st of April and ends on the 31st of March the following year**
    """
    audit_start_date = date(date_instance.year, 4, 1)
    if date_instance < audit_start_date:
        return date(date_instance.year - 1, 4, 1)
    else:
        return date(date_instance.year, 4, 1)
