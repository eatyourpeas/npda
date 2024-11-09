"""
CLI for seeding Submissions for a given User (and that user's PDU). Will
additionally create Patients and Visits.

Example use:
    python manage.py seed_submission \
        --pts=50 \
        --visits="CDCD DHPC ACDC CDCD" \
        --hb_target=T
        --user_pk=1 \
        --submission_date="2024-10-18" \

    This will generate a submission for User.pk=1 that includes 50 patients,
    each of whom will have 16 Visits evenly spread throughout the audit
    year's quarters, with types Clinic, Dietician, ..., Clinic, Dietician,
    all with HbA1c target range as TARGET.

Options:

    --pts (int, required):
        The number of patients to seed for this submission.

    --visits (str, required):
        A string encoding the VisitTypes each patient should have. Use
        visit type abbreviations. Can use whitespace (ignored)
        (e.g., "CDCD DHPC ACDC CDCD").
        Each patient will have associated Visits in the sequence provided.

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
    
    --age_range (str, optional):
        The possible age range for the patients to be seeded. 
        Defaults to 11_15.
            - 0_4
            - 5_10
            - 11_15
            - 16_19
            - 20_25
    
    --user_pk (int, optional):
        The primary key of the user for whom the submission is created.
        Defaults to the seeded SuperuserAda. Note that Submission.pdu is set
        to this user's primary organisation_employer.

    --submission_date (str, optional):
        The submission date in YYYY-MM-DD format. Defaults to today. This
        date is used to set the audit period's start and end dates.


Notes:
    - Submission requires an associated `csv_file`. A dummy value is set to
      project/npda/dummy_sheets/dummy_sheet.csv.
"""

from datetime import datetime

from django.utils import timezone
from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import SimpleUploadedFile

from project.npda.general_functions.audit_period import (
    get_audit_period_for_date,
)
from project.npda.general_functions.data_generator_extended import (
    AgeRange,
    FakePatientCreator,
    HbA1cTargetRange,
    VisitType,
)
from project.npda.models import (
    NPDAUser,
    Patient,
    Submission,
    OrganisationEmployer,
)

letter_name_map = {
    "C": VisitType.CLINIC,
    "A": VisitType.ANNUAL_REVIEW,
    "D": VisitType.DIETICIAN,
    "P": VisitType.PSYCHOLOGY,
    "H": VisitType.HOSPITAL_ADMISSION,
}
hb_target_map = {
    "T": HbA1cTargetRange.TARGET,
    "A": HbA1cTargetRange.ABOVE,
    "W": HbA1cTargetRange.WELL_ABOVE,
}
age_range_map = {
    "0_4": AgeRange.AGE_0_4,
    "5_10": AgeRange.AGE_5_10,
    "11_15": AgeRange.AGE_11_15,
    "16_19": AgeRange.AGE_16_19,
    "20_25": AgeRange.AGE_20_25,
}

# ANSI Colour Codes
CYAN = "\033[96m"
RESET = "\033[0m"
GREEN = "\033[92m"

class Command(BaseCommand):
    help = "Seeds submission with specific user, submission date, number of patients, and visit types."

    def print_success(self, message: str):
        self.stdout.write(self.style.SUCCESS(message))

    def print_info(self, message: str):
        self.stdout.write(self.style.WARNING(message))

    def print_error(self, message: str):
        self.stdout.write(self.style.ERROR(f"ERROR: {message}"))

    def add_arguments(self, parser):
        parser.add_argument(
            "--user_pk",
            type=int,
            help="User primary key (optional, defaults to SuperuserAda's PK if not provided).",
        )
        parser.add_argument(
            "--submission_date",
            type=str,
            help="Submission date in YYYY-MM-DD format (optional, defaults to today).",
        )
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
            "--age_range",
            type=str,
            default="11_15",
            choices=["0_4", "5_10", "11_15", "16_19", "20_25"],
            help="Age range for patients to be seeded.",
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
        user_pk = parsed_values["user_pk"]
        submission_by = parsed_values["submission_by"]
        submission_date = parsed_values["submission_date"]
        age_range = age_range_map[options["age_range"]]

        # Associate submission's PDU with user
        primary_pdu_for_user = (
            OrganisationEmployer.objects.filter(
                npda_user=submission_by, is_primary_employer=True
            )
            .first()
            .paediatric_diabetes_unit
        )

        # Print out the parsed values
        self.print_info(
            f"Using user_pk: {CYAN}{user_pk} ({submission_by}){RESET}\n"
        )
        self.print_info(
            f"Submission PDU: {CYAN}{primary_pdu_for_user}{RESET}\n"
        )
        self.print_info(
            f"Using submission_date: {CYAN}{submission_date}{RESET}\n"
            f"Audit period: Start Date - {CYAN}{audit_start_date}{RESET}, "
            f"End Date - {CYAN}{audit_end_date}{RESET}\n"
        )
        self.print_info(
            f"Number of patients to seed: {CYAN}{n_pts_to_seed}{RESET}\n"
        )
        formatted_visits = "\n    ".join(
            f"{CYAN}{visit_type}{RESET}"
            for visit_type in self._map_visit_type_letters_to_names(
                visits
            ).split("\n")
        )
        self.print_info(f"Visit types provided:\n    {formatted_visits}\n")
        # Now create the submission
        self.print_info(f"HbA1c target: {CYAN}{hba1c_target.name}{RESET}\n")
        self.print_info(f"Age range: {CYAN}{age_range.name}{RESET}\n")

        # Start seeding logic

        # First create patients
        fake_patient_creator = FakePatientCreator(
            audit_start_date=audit_start_date,
            audit_end_date=audit_end_date,
        )
        new_pts = fake_patient_creator.create_and_save_fake_patients(
            n=n_pts_to_seed,
            age_range=age_range,
            hb1ac_target_range=hba1c_target,
            visit_types=visit_types,
            visit_kwargs={"is_valid": True},
        )

        

        # Need a mock csv
        with open("project/npda/dummy_sheets/dummy_sheet.csv", "rb") as f:
            mock_csv = SimpleUploadedFile(
                name="dummy_sheet.csv",
                content=f.read(),
                content_type="text/csv",
            )
        new_submission = Submission.objects.create(
            paediatric_diabetes_unit=primary_pdu_for_user,
            audit_year=audit_start_date.year,
            submission_date=submission_date,
            submission_by=submission_by,
            submission_active=True,
            csv_file=mock_csv,
        )

        # Add patients to submission
        new_submission.patients.add(*new_pts)

        self.print_success(
            f"Submission has been seeded successfully: {new_submission}",
        )

    def _parse_values_from_options(self, **options):
        # Get user_pk with default to a superuser's pk if not provided
        user_pk = options.get("user_pk")
        if not user_pk:
            user = NPDAUser.objects.filter(
                is_superuser=True,
                first_name="SuperuserAda",
            ).first()
            if not user:
                self.print_error("No superuser found to default user_pk.")
                return
            user_pk = user.pk

        if not (submission_by := NPDAUser.objects.filter(pk=user_pk).first()):
            self.print_error(f"Could not find user with pk {user_pk}")
            return

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
        
        # Age range
        age_range = age_range_map[options["age_range"]]

        return {
            "n_pts_to_seed": n_pts_to_seed,
            "audit_start_date": audit_start_date,
            "audit_end_date": audit_end_date,
            "hba1c_target": hba1c_target,
            "visits": visits,
            "visit_types": visit_types,
            "submission_by": submission_by,
            "user_pk": user_pk,
            "submission_date": submission_date,
            "age_range": age_range,
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
