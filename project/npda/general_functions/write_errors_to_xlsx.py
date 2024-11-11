# import types
from collections import defaultdict
from typing import Any

# import models
from ..models.submission import Submission

# import functions
from ..general_functions.serialize_validation_errors import serialize_errors

# import third-party libaries
import pandas as pd

def write_errors_to_xlsx(errors: defaultdict[Any, defaultdict[Any, list]], new_submission: Submission) -> bool:
  """
  Write errors to an Excel file. This .xlsx file can later be downloaded by the user to highlight invalid cells when attempting to upload CSV data. 

  Args:
    errors (defaultdict[Any, defaultdict[Any, list]]): A dictionary containing errors grouped by row index and field.

  """

  # Serialize the errors to get text.
  errors = serialize_errors(errors)

  # Write an xlsx of the original data.  
  

  print("Running write_errors_to_xlsx")
  print(new_submission.csv_file)
  return True

def read_csv(csv_file: str) -> pd.DataFrame:
  df = pd.read_csv(csv_file)
  return df