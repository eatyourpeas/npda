import csv
import io
from ...constants.csv_headings import HEADINGS_LIST


def csv_header():
    out = io.StringIO()

    writer = csv.writer(out)
    writer.writerow(HEADINGS_LIST)

    return out.getvalue()
