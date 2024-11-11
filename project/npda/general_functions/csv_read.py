import pandas as pd

# RCPCH imports
from ...constants import ALL_DATES, CSV_DATA_TYPES_MINUS_DATES

def csv_read(csv_file):
    """
    Read the csv file and return a pandas dataframe
    Assigns the correct data types to the columns
    Parses the dates in the columns to the correct format
    """

    # Parse the dates in the columns to the correct format first
    df = pd.read_csv(csv_file)
    # Remove leading and trailing whitespace on column names
    # The template published on the RCPCH website has trailing spaces on 'Observation Date: Thyroid Function '
    df.columns = df.columns.str.strip()

    for column in ALL_DATES:
        if column in df.columns:
            df[column] = pd.to_datetime(df[column], format="%d/%m/%Y", errors="coerce")

    # Apply the dtype to non-date columns
    for column, dtype in CSV_DATA_TYPES_MINUS_DATES.items():
        try:
            df[column] = df[column].astype(dtype)
        except ValueError as e:
            raise ValidationError(
                f"The data type for {column} cannot be processed. Please make sure the data type is correct."
            )
        df[column] = df[column].where(pd.notnull(df[column]), None)
        # round height and weight if provided to 1 decimal place
        if column in [
            "Patient Height (cm)",
            "Patient Weight (kg)",
            "Total Cholesterol Level (mmol/l)",
        ]:
            df[column] = df[column].round(1)

    return df

