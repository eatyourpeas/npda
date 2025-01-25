import csv
import io
from project.constants import (
    CSV_HEADING_OBJECTS,
    UNIQUE_IDENTIFIER_ENGLAND,
    UNIQUE_IDENTIFIER_JERSEY,
)


def csv_header(is_jersey=False):
    if is_jersey:
        HEADINGS_LIST = UNIQUE_IDENTIFIER_JERSEY + CSV_HEADING_OBJECTS
    else:
        HEADINGS_LIST = UNIQUE_IDENTIFIER_ENGLAND + CSV_HEADING_OBJECTS

    HEADINGS_LIST = [item["heading"] for item in HEADINGS_LIST]

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(HEADINGS_LIST)

    return out.getvalue()
