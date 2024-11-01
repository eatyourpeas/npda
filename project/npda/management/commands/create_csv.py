"""TODO:
    - [ ] Move constants to a separate file. Currently importing from `seed_submission.py`.
    - [ ] Generalise the parsing of inputs and share between this and `seed_submission.py`.

Generate a CSV using data generator.

Default behavior of data generator is creating VALID visits - CSV.

Example use:

    python manage.py create_csv \
        --pts=5 \
        --visits="CDCD DHPC ACDC CDCD" \
        --hb_target=T

    Will generate a csv file with 5 patients, each with 12 visits, with the visit encoding provided.
    The HbA1c target range for each visit will be set to 'TARGET'.
    The resulting csv will have 5 * 12 = 60 rows (one for each visit).

    Options:

    --pts (int, required):
        The number of pts to seed for this csv file. (NOTE: resulting rows will be pts * visits
        )

    --visits (str, required):
        A string encoding the VisitTypes each patient should have. Use
        visit type abbreviations. Can use whitespace (ignored)
        (e.g., "CDCD DHPC ACDC CDCD").
        Each patient will have associated Visits in the sequence provided,
        evenly spread throughout the audit year's quarters, randomly within
        each quarter.

        Visit type options:
            - C (CLINIC)
            - A (ANNUAL_REVIEW)
            - D (DIETICIAN)
            - P (PSYCHOLOGY)
            - H (HOSPITAL_ADMISSION)

    --hb_target (str, required):
        Character setting for HbA1c target range per visit:
            - T (TARGET)
            - A (ABOVE)
            - W (WELL_ABOVE)

    --submission_date (str, optional):
        The submission date in YYYY-MM-DD format. Defaults to today. This
        date is used to set the audit period's start and end dates, and visit
        values e.g. diabetes diagnosis date.

    --output_path (str, optional):
        Path to save the csv. Defaults to `project/npda/dummy_sheets/local_generated_data`.

Implementation notes:

    We can use the `FakePatientCreator`'s `.build()` methods to generate Python object stubs of Patients and Visits. We then use pandas to concatenate these values into the csv.

    Factory `.build()` will not create related objects (but is significantly quicker). At the end,
    need to additionally add the `Transfer` column values manually.
"""

from collections import defaultdict
from datetime import datetime
import random

from django.utils import timezone
from django.core.management.base import BaseCommand
import pandas as pd
import numpy as np

from project.constants.csv_headings import CSV_HEADINGS
from project.npda.general_functions.audit_period import (
    get_audit_period_for_date,
)
from project.npda.general_functions.data_generator_extended import (
    AgeRange,
    FakePatientCreator,
    HbA1cTargetRange,
    VisitType,
)
from project.npda.general_functions.model_utils import (
    print_instance_field_attrs,
    get_model_field_attrs_and_vals,
)
from project.npda.models import (
    NPDAUser,
    Patient,
    Submission,
    OrganisationEmployer,
)
from project.npda.management.commands.seed_submission import (
    letter_name_map,
    hb_target_map,
    CYAN,
    RESET,
)

PZ_CODE = "PZ999"
GP_ODS_CODES = [
    "A81001",
    "A81002",
    "A81004",
    "A81005",
    "A81006",
    "A81007",
    "A81009",
    "A81011",
    "A81012",
    "A81013",
    "A81014",
    "A81016",
    "A81017",
    "A81018",
    "A81019",
    "A81020",
    "A81021",
    "A81022",
    "A81023",
    "A81025",
]
TEMPLATE_HEADERS = pd.read_csv(
    "project/npda/dummy_sheets/npda_csv_submission_template_for_use_from_april_2021.csv"
).columns


class Command(BaseCommand):
    help = "Creates a csv file that can be uploaded to the NPDA platform."

    def print_success(self, message: str):
        self.stdout.write(self.style.SUCCESS(message))

    def print_info(self, message: str):
        self.stdout.write(self.style.WARNING(message))

    def print_error(self, message: str):
        self.stdout.write(self.style.ERROR(f"ERROR: {message}"))

    def add_arguments(self, parser):
        parser.add_argument(
            "--pts",
            type=int,
            required=True,
            help="Number of patients to seed.",
        )
        parser.add_argument(
            "--visits",
            type=str,
            required=True,
            help="Visit types (e.g., 'CDCD DHPC ACDC CDCD'). Can have whitespaces, these will be "
            "ignored",
        )
        parser.add_argument(
            "--hb_target",
            type=str,
            required=True,
            choices=["T", "A", "W"],
            help="HBA1C Target range for visit seeding.",
        )
        parser.add_argument(
            "--submission_date",
            type=str,
            help="Submission date in YYYY-MM-DD format (optional, defaults to today).",
        )
        parser.add_argument(
            "--output_path",
            type=str,
            help="Path to save the csv",
            default="project/npda/dummy_sheets/local_generated_data",
        )

    def handle(self, *args, **options):

        if not (parsed_values := self._parse_values_from_options(**options)):
            return

        audit_start_date = parsed_values["audit_start_date"]
        audit_end_date = parsed_values["audit_end_date"]
        n_pts_to_seed = parsed_values["n_pts_to_seed"]
        hba1c_target = parsed_values["hba1c_target"]
        visits = parsed_values["visits"]
        visit_types = parsed_values["visit_types"]
        submission_date = parsed_values["submission_date"]
        age_range = AgeRange.AGE_11_15
        output_path = parsed_values["output_path"]



        # Print out the parsed values
        self.print_info(
            f"Using submission_date: {CYAN}{submission_date}{RESET}\n"
            f"Audit period: Start Date - {CYAN}{audit_start_date}{RESET}, "
            f"End Date - {CYAN}{audit_end_date}{RESET}\n"
        )
        self.print_info(
            f"Number of rows to seed: {CYAN}{n_pts_to_seed}{RESET}\n"
        )
        formatted_visits = "\n    ".join(
            f"{CYAN}{visit_type}{RESET}"
            for visit_type in self._map_visit_type_letters_to_names(
                visits
            ).split("\n")
        )
        self.print_info(f"Visit types provided:\n    {formatted_visits}\n")
        self.print_info(f"HbA1c target range: {CYAN}{hba1c_target}{RESET}\n")

        self.generate_csv(
            audit_start_date,
            audit_end_date,
            n_pts_to_seed,
            age_range,
            hba1c_target,
            visits,
            visit_types,
            output_path,
        )

    def generate_csv(
        self,
        audit_start_date,
        audit_end_date,
        n_pts_to_seed,
        age_range,
        hba1c_target,
        visits,
        visit_types,
        output_path,
    ):

        # Start csv logic

        # First initialise FakePatientCreator object
        fake_patient_creator = FakePatientCreator(
            audit_start_date=audit_start_date,
            audit_end_date=audit_end_date,
        )

        # Build pt stubs
        new_pts = fake_patient_creator.build_fake_patients(
            n=n_pts_to_seed,
            age_range=age_range,
        )

        # For each pt, add visits
        new_visits = fake_patient_creator.build_fake_visits(
            patients=new_pts,
            age_range=age_range,
            hb1ac_target_range=hba1c_target,
            visit_types=visit_types,
        )

        # `CSV_HEADINGS` is a tuple for csv headings and model fields
        # Create a map = {
        #   model : {
        #     model_field : csv_heading
        #   }
        # }
        csv_map = self._get_map_model_csv_heading_field()

        # Initialise data list, where each item is a dict relating to a row in the csv
        # Each dict will have keys as csv headings and values as the data
        data = []

        # We're using the build method so Patients and Visits are separate objects
        # Need to manually iterate and join the data
        N_VISIT_TYPES = len(visit_types)
        for ix, pt in enumerate(new_pts):
            gp_ods_code = random.choice(GP_ODS_CODES)
            visit_start_idx = ix * N_VISIT_TYPES
            visit_end_idx = visit_start_idx + N_VISIT_TYPES
            for visit in new_visits[visit_start_idx:visit_end_idx]:
                visit_dict = {}

                for model, field_heading_mappings in csv_map.items():
                    for (
                        model_field,
                        csv_heading,
                    ) in field_heading_mappings.items():
                        if model == "Visit":
                            visit_dict[csv_heading] = getattr(
                                visit, model_field
                            )
                        elif model == "Patient":
                            # Foreign key so need to manually set the value
                            if model_field == "pdu":
                                visit_dict[csv_heading] = PZ_CODE
                                continue
                            if model_field == "gp_ods_code":
                                visit_dict[csv_heading] = gp_ods_code
                                continue

                            visit_dict[csv_heading] = getattr(pt, model_field)

                        # date of leaving service
                        # & reason for leaving service. Ignore for now
                        elif model == "Transfer":
                            visit_dict[csv_heading] = None

                data.append(visit_dict)

        df = (
            pd.DataFrame(data)
            # The template file headers are weird
            .rename(
                columns={
                    "Observation Date: Thyroid Function": "Observation Date: Thyroid Function ",
                    "At time of or following measurement of thyroid function, was the patient prescribed any thyroid treatment?": "At time of, or following measurement of thyroid function, was the patient prescribed any thyroid treatment?",
                }
            )
            # Reorder columns
            # [TEMPLATE_HEADERS]
        )
        df.to_csv(
            f"{output_path}/npda_seed_data-{n_pts_to_seed}-{visits.replace(' ','')}.csv",
            index=False,
        )

    def _parse_values_from_options(self, **options):

        # Handle submission_date with default to today's date if not provided
        submission_date_str = options.get("submission_date")
        if submission_date_str:
            try:
                submission_date = timezone.make_aware(
                    datetime.strptime(submission_date_str, "%Y-%m-%d")
                ).date()
            except ValueError:
                self.print_error(
                    "Invalid submission_date format. Use YYYY-MM-DD."
                )
                return
        else:
            submission_date = timezone.now().date()

        audit_start_date, audit_end_date = get_audit_period_for_date(
            submission_date
        )

        # Number of patients to seed (pts)
        n_pts_to_seed = options["pts"]

        # Visit types
        visits: str = options["visits"]
        # Map to actual VisitType
        # NOTE: `_map_visit_type_letters_to_names` already did some basic validation
        visit_types = list(
            map(
                lambda letter: letter_name_map[letter],
                visits.replace(" ", ""),
            )
        )

        # hba1c target
        hba1c_target = hb_target_map[options["hb_target"]]

        # output path
        output_path = options["output_path"]

        return {
            "n_pts_to_seed": n_pts_to_seed,
            "audit_start_date": audit_start_date,
            "audit_end_date": audit_end_date,
            "hba1c_target": hba1c_target,
            "visits": visits,
            "visit_types": visit_types,
            "submission_date": submission_date,
            "output_path": output_path,
        }

    def _map_visit_type_letters_to_names(self, vt_letters: str) -> str:
        rendered_vt_names: list[str] = []

        for letter in vt_letters:
            if letter == " ":
                rendered_vt_names.append("\n\t")
                continue
            if letter.upper() not in "CADPH":
                self.print_error("INVALID VISIT TYPE LETTER: " + letter)

            rendered_vt_names.append(f"\n\t{letter_name_map[letter]}")

        return "".join(rendered_vt_names)

    def _get_map_model_csv_heading_field(self) -> dict:
        """Generates dict that looks like:

        {
            'Patient': {
                'nhs_number': 'NHS Number',
                'date_of_birth': 'Date of Birth',
                ...
            },
            'Visit': {
                'visit_type': 'Visit Type',
                'visit_date': 'Visit/Appointment Date',
                ...
            },
            'Transfer': {
                'date_leaving_service': 'Date Leaving Service',
                ...
        }
        """

        map_model_csv_heading_field = defaultdict(dict)

        for item in CSV_HEADINGS:
            model = item["model"]
            csv_heading = item["heading"]
            model_field = item["model_field"]
            map_model_csv_heading_field[model][model_field] = csv_heading

        return map_model_csv_heading_field
