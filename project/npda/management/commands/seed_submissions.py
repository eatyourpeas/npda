"""CLI for seeding Submissions for a given User (and that user's PDU). Will additionally create 
Patients and Visits.

Visit type options:
    - C (CLINIC)
    - A (ANNUAL_REVIEW)
    - D (DIETICIAN)
    - P (PSYCHOLOGY)
    - H (HOSPITAL_ADMISSION)

Example use:

    python manage.py seed_submission \
        --user_pk=1 \
        --submission_date="2024-10-18" \
        --pts=50 \
        --visits="CDCD DHPC ACDC CDCD"
    
    will generate a submission for User.pk=1 that includes 50 patients, each of whom will have
    12 Visits evenly spread throughout the audit year's quarters, with types Clinic, Dietician, ...,
    Clinic, Dietician.
"""

from datetime import datetime, timezone
from django.core.management.base import BaseCommand

from project.npda.general_functions.data_generator_extended import VisitType
from project.npda.models.npda_user import NPDAUser

class Command(BaseCommand):
    help = "Seeds submissions with specific user, submission date, number of patients, and visit types."


    def print_success(self, message: str):
        self.stdout.write(self.style.SUCCESS(message))


    def print_error(self, message: str):
        self.stdout.write(self.style.ERROR(f"ERROR: {message}"))

    def add_arguments(self, parser):
        parser.add_argument(
            '--user_pk', 
            type=int, 
            help="User primary key (optional, defaults to SuperuserAda's PJ if not provided)."
        )
        parser.add_argument(
            '--submission_date', 
            type=str, 
            help="Submission date in YYYY-MM-DD format (optional, defaults to today)."
        )
        parser.add_argument(
            '--pts', 
            type=int, 
            required=True, 
            help="Number of patients to seed."
        )
        parser.add_argument(
            '--visits', 
            type=str, 
            required=True, 
            help="Visit types (e.g., 'CDCD DHPC ACDC CDCD'). Can have whitespaces, these will be "
            "ignored"
        )

    def handle(self, *args, **options):
        
        # Get user_pk with default to a superuser's pk if not provided
        user_pk = options.get('user_pk')
        if not user_pk:
            user = NPDAUser.objects.filter(is_superuser=True, first_name="SuperuserAda",).first()
            if not user:
                self.print_error("No superuser found to default user_pk.")
                return
            user_pk = user.pk
        self.print_success(f"Using user_pk: {user_pk}")

        # Handle submission_date with default to today's date if not provided
        submission_date_str = options.get('submission_date')
        if submission_date_str:
            try:
                submission_date = datetime.strptime(submission_date_str, "%Y-%m-%d").date()
            except ValueError:
                self.print_error("Invalid submission_date format. Use YYYY-MM-DD.")
                return
        else:
            submission_date = timezone.now().date()
        self.print_success(f"Using submission_date: {submission_date}")

        # Number of patients to seed (pts)
        pts = options['pts']
        self.print_success(f"Number of patients to seed: {pts}")

        # Visit types
        visits = options['visits']
        self.print_success(f"Visit types provided: {self._map_visit_type_letters_to_names(visits)}")

        # Start seeding logic

        self.print_success("Submissions have been seeded successfully.")
    
    def _map_visit_type_letters_to_names(self, vt_letters:str)->str:
        rendered_vt_names: list[str] = []
        letter_name_map = {
            "C" : VisitType.CLINIC.name,
            "A" : VisitType.ANNUAL_REVIEW.name,
            "D" : VisitType.DIETICIAN.name,
            "P" : VisitType.PSYCHOLOGY.name,
            "H" : VisitType.HOSPITAL_ADMISSION.name,
        }
        for letter in vt_letters:
            if letter == " ":
                rendered_vt_names.append("\n\t")
                continue
            if letter.upper() not in "CADPH":
                self.print_error("INVALID VISIT TYPE LETTER: " + letter)
            
            rendered_vt_names.append(f"\n\t{letter_name_map[letter]}")
        
        return "".join(rendered_vt_names)
            
            
