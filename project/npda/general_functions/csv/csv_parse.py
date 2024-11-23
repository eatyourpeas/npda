# python imports
from dataclasses import dataclass
import logging
import re

# Django imports
from django.core.exceptions import ValidationError

# Third-party imports
import pandas as pd
import numpy as np

# RCPCH imports
from project.constants import (
    ALL_DATES,
    CSV_DATA_TYPES_MINUS_DATES,
    CSV_HEADINGS,
    HEADINGS_LIST,
)

# Logging setup
logger = logging.getLogger(__name__)


@dataclass
class ParsedCSVFile:
    df: pd.DataFrame
    missing_columns: list[str]
    additional_columns: list[str]
    duplicate_columns: list[str]
    parse_type_error_columns: list[str]


def csv_parse(csv_file):
    """
    Read the csv file and return a pandas dataframe
    Assigns the correct data types to the columns
    Parses the dates in the columns to the correct format
    """
    # It is possible the csv file has no header row. In this case, we will use the predefined column names
    # The predefined column names are in the HEADINGS_LIST constant and if cast to lowercase, in lowercase_headings_list
    # We will check if the first row of the csv file matches the predefined column names
    # If it does not, we will use the predefined column names
    # If it does, we will use the column names in the csv file
    # The exception is if the first row of the csv file does not match any of the predefined column names, in which case we will reject the csv

    # Convert the predefined column names to lowercase
    lowercase_headings_list = [heading.lower() for heading in HEADINGS_LIST]

    # Read the first row of the csv file
    df = pd.read_csv(csv_file)

    if any(col.lower() in lowercase_headings_list for col in df.columns):
        # The first row of the csv file matches at least some of the predefined column names
        # We will use the column names in the csv file
        pass
    else:
        # The first row of the csv file does not match the predefined column names
        # We will reject this csv (#391)
        raise ValueError(
            "The first row of the csv file does not match any of the predefined column names. Please include these and upload the file again."
        )

    # Remove leading and trailing whitespace on column names
    # The template published on the RCPCH website has trailing spaces on 'Observation Date: Thyroid Function '
    df.columns = df.columns.str.strip()

    if df.columns[0].lower() not in lowercase_headings_list:
        # No header in the source - pass them from our definitions
        logger.warning(
            f"CSV file uploaded without column names, using predefined column names"
        )

        # Have to reset back otherwise we get an empty dataframe
        csv_file.seek(0)

    # Pandas has strange behaviour for the first line in a CSV - additional cells become row labels
    # https://github.com/pandas-dev/pandas/issues/47490
    #
    # As a heuristic for this, check the row label for the first row is the number 0
    # If it isn't - you've got too many values in the first row
    if not df.iloc[0].name == 0:
        raise ValueError(
            "Suspected too many values in the first row, please check there are no extra values"
        )

    # Accept columns case insensitively but replace them with their official version to make life easier later
    for column in df.columns:
        if not column in HEADINGS_LIST and column.lower() in lowercase_headings_list:
            normalised_column = next(
                c for c in HEADINGS_LIST if c.lower() == column.lower()
            )
            df = df.rename(columns={column: normalised_column})

    missing_columns = [column for column in HEADINGS_LIST if not column in df.columns]

    additional_columns = [
        column for column in df.columns if not column in HEADINGS_LIST
    ]

    # Duplicate columns appear in the dataframe as XYZ.1, XYZ.2 etc
    duplicate_columns = []

    parse_type_error_columns = []

    for column in df.columns:
        result = re.match(r"([\w ]+)\.\d+$", column)

        if result and result.group(1) not in duplicate_columns:
            duplicate_columns.append(result.group(1))

    for column in ALL_DATES:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], format="%d/%m/%Y", errors="coerce")

    # Apply the dtype to non-date columns
    for column, dtype in CSV_DATA_TYPES_MINUS_DATES.items():
        try:
            if column in df.columns:
                df[column] = df[column].astype(dtype)
        except ValueError as e:
            parse_type_error_columns.append(column)
            continue
        # Convert NaN to None for nullable fields
        if column in df.columns:
            df[column] = df[column].where(pd.notnull(df[column]), None)
        # round height and weight if provided to 1 decimal place
        if (
            column
            in [
                "Patient Height (cm)",
                "Patient Weight (kg)",
                "Total Cholesterol Level (mmol/l)",
            ]
            and column in df.columns
        ):
            if df[column].dtype == np.float64:
                df[column] = df[column].round(1)
            else:
                parse_type_error_columns.append(column)

    return ParsedCSVFile(
        df,
        missing_columns,
        additional_columns,
        duplicate_columns,
        parse_type_error_columns,
    )
