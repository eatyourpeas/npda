# import types
from collections import defaultdict
from typing import Any, Dict, List, Union
import io

from openpyxl.worksheet.worksheet import Worksheet

# import models
from ..models.submission import Submission

# import functions
from project.npda.general_functions.csv.csv_parse import csv_parse

# import third-party libaries
import pandas as pd
from json import loads as json_loads
from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill, Font
from openpyxl.comments import Comment

# import csv mappings
from ...constants.csv_headings import (
    CSV_HEADING_OBJECTS,
    UNIQUE_IDENTIFIER_ENGLAND,
    UNIQUE_IDENTIFIER_JERSEY,
)


def write_errors_to_xlsx(
    errors: dict[str, dict[str, list[str]]],
    original_csv_file_bytes: bytes,
    is_jersey: bool,
) -> bytes:
    """
    Write errors to an Excel file. Highlight invalid cells in the source CSV.

    Args:
      errors A nested dictionary containing errors grouped by row index, then field.

    """

    xlsx_file = io.BytesIO()

    # Get original data
    df = csv_parse(
        io.BytesIO(initial_bytes=original_csv_file_bytes), is_jersey=is_jersey
    ).df
    # Write an xlsx of the original data.
    df.to_excel(xlsx_file, sheet_name="Uploaded data (raw)", index=False)

    # If the csv file is from Jersey, add the Jersey unique identifier to the CSV headings, otherwise add the England unique identifier
    if is_jersey:
        CSV_HEADINGS = UNIQUE_IDENTIFIER_JERSEY + CSV_HEADING_OBJECTS

        flattened_errors = flatten_errors(
            errors, df["Unique Reference Number"], CSV_HEADINGS
        )
    else:
        CSV_HEADINGS = UNIQUE_IDENTIFIER_ENGLAND + CSV_HEADING_OBJECTS
        flattened_errors = flatten_errors(errors, df["NHS Number"], CSV_HEADINGS)

    # Add sheet that lists the errors.
    with pd.ExcelWriter(xlsx_file, mode="a", engine="openpyxl") as writer:
        df_new = pd.DataFrame(
            flattened_errors
        )  # Example DataFrame; replace with your actual data
        df_new.to_excel(writer, sheet_name="Errors - Overview", index=False)

    # Load the workbook in openpyxl
    wb: Workbook = load_workbook(xlsx_file)

    # Set text to red
    overview_sheet = wb["Errors - Overview"]
    for row in overview_sheet.iter_rows(min_row=2, min_col=3):
        for cell in row:
            cell.font = Font(color="FF0000")

    # Setup the styled worksheet
    styled_sheet: Worksheet = wb.copy_worksheet(wb["Uploaded data (raw)"])
    styled_sheet.title = (
        "Uploaded data (comments)"  # You can set any name for the copied sheet
    )

    # Style the openpyxl worksheet to highlight in red erroneous/invalid cells.
    # Also add comments to annotate the actual error.
    for patient_errors in flattened_errors:
        row_index = patient_errors["metadata_patient_row"] + 1
        for field_name, field_error in patient_errors.items():
            column_index = find_column_index_by_name(field_name, styled_sheet)
            if column_index:
                styled_sheet.cell(row=row_index, column=column_index).fill = (
                    PatternFill(patternType="solid", fgColor="FFC9C9")
                )  # Change color to red.
                styled_sheet.cell(row=row_index, column=column_index).comment = Comment(
                    field_error,
                    "Data Validator [Automated: RCPCH]",
                    height=300,
                    width=300,
                )

    # Specify the desired order by reordering the `workbook.worksheets` list
    wb._sheets = [
        wb["Uploaded data (raw)"],
        wb["Uploaded data (comments)"],
        wb["Errors - Overview"],
    ]

    # Save the styled sheet.
    wb.save(xlsx_file)

    return xlsx_file.getvalue()


def find_column_index_by_name(column_name: str, ws: Worksheet) -> int | None:
    column_index = None
    for col in ws.iter_cols(
        1, ws.max_column, 1, 1
    ):  # Check headers in the first row only
        if col[0].value == column_name:
            column_index = col[0].column  # Get the column index
            break
    return column_index


def flatten_errors(
    errors: defaultdict[int, defaultdict[Any, list]],
    uploaded_unique_national_identifiers: "pd.Series[str]",
    csv_heading_list: "List[Dict[str, str]]",
) -> "List[Dict[str, Union[int, str]]]":
    """
    Flatten a nested dictionary of errors into a list of dictionaries, where each dictionary represents a row with
    its errors.

    Args:
        errors (defaultdict[int, defaultdict[Any, list]]): A nested dictionary containing
            errors grouped by row number and field name. The structure is:
            {row_number: {field_name: [error_messages]}}
        uploaded_unique_national_identifiers (pd.Series[str]): A pandas Series containing the unique national identifiers (NHS Numbers or Unique Reference Numbers) of the uploaded data.
        csv_heading_list (List[Dict[str, str]]): A list of dictionaries containing the CSV headings. (e.g. [{'heading': 'Date of Birth', 'model_field': 'date_of_birth', 'model': 'patient'}]) They differ depending on whether NHS Numbers or Unique Reference Numbers are used.

    Returns:
        list: A list of dictionaries, where each dictionary contains:
            - 'row': The row number (as an integer)
            - Field names as keys and concatenated error messages as values

    """

    flattened_data: "List[Dict[str, Union[int, str]]]" = []

    for row_num, errors in errors.items():
        # Add patient_row and NHS Number to the row dictionary.
        row_dict = {"metadata_patient_row": int(row_num) + 1}
        row_dict["metadata_unique_national_identifiers"] = (
            uploaded_unique_national_identifiers.tolist()[int(row_num)]
        )

        for field, error_list in errors.items():
            # Flatten nested error messages into a single string
            error_messages = "; ".join(error_list)
            # Map field name to human-readable string ("date_of_birth" -> "Date of Birth")
            field: dict[str, str] = next(
                (item for item in csv_heading_list if item["model_field"] == field),
                {
                    "heading": "Unable to get header",
                    "model_field": "error",
                    "model": "error",
                },
            )
            field_heading = field.get("heading", "Heading not found")
            row_dict[f"{field_heading}"] = error_messages

        flattened_data.append(row_dict)
    return flattened_data
