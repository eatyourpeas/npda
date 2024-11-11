import tempfile
import pytest

from project.npda.general_functions.csv_summarize import csv_summarize


def csv_summarize_from_str(contents):
    with tempfile.NamedTemporaryFile() as f:
        f.write(contents.encode())
        f.seek(0)

        return csv_summarize(f)


# https://github.com/rcpch/national-paediatric-diabetes-audit/issues/357
@pytest.mark.django_db
def test_csv_summarize(dummy_sheet_csv):
    lines = dummy_sheet_csv.split("\n")[:2]

    assert lines[1].startswith("719 573 0220")
    lines[1] = lines[1].replace("719 573 0220", "7195730220")

    csv = "\n".join(lines)

    summary = csv_summarize_from_str(csv)

    assert summary["total_records"] == 1
    assert summary["number_unique_nhs_numbers"] == 1
