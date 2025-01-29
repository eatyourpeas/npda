# python
import logging


from django.core.management.base import BaseCommand

# Logging setup
logger = logging.getLogger(__name__)

from .create_groups import groups_seeder
from .seed_functions.paediatric_diabetes_units_seeder import (
    paediatric_diabetes_units_seeder,
)
from .seed_functions.audit_periods_seeder import audit_periods_seeder


class Command(BaseCommand):
    help = "seed database with organisation trust data for testing and development."

    def add_arguments(self, parser):
        parser.add_argument("-m", "--mode", type=str, help="Mode")

    def handle(self, *args, **options):

        if options["mode"] == "seed_groups_and_permissions":
            self.stdout.write("setting up groups and permissions...")
            groups_seeder(run_create_groups=True)
        elif options["mode"] == "add_permissions_to_existing_groups":
            self.stdout.write("adding permissions to groups...")
            groups_seeder(add_permissions_to_existing_groups=True)
        elif options["mode"] == "seed_paediatric_diabetes_units":
            self.stdout.write("seeding paediatric diabetes units...")
            paediatric_diabetes_units_seeder()
        elif options["mode"] == "seed_audit_periods":
            self.stdout.write("seeding audit periods...")
            audit_periods_seeder()

        else:
            self.stdout.write("No options supplied...")


def image():
    return """

                                .^~^      ^777777!~:       ^!???7~:
                                ^JJJ:.:!^ 7#BGPPPGBGY:   !5BBGPPGBBY.
                                 :~!!?J~. !BBJ    YBB?  ?BB5~.  .~J^
                              .:~7?JJ?:   !BBY^~~!PBB~ .GBG:
                              .~!?JJJJ^   !BBGGGBBBY^  .PBG^
                                 ?J~~7?:  !BBJ.:?BB5^   ~GBG?^:^~JP7
                                :?:   .   !BBJ   ~PBG?.  :?PBBBBBG5!
                                ..::...     .::. ...:^::. .. .:^~~^:.
                                !GPGGGGPY7.   :!?JJJJ?7~..PGP:    !GGJ
                                7BBY~~!YBBY  !JJ?!^^^!??::GBG:    7BBJ
                                7BB?   .GBG.^JJ7.     .. .GBG!^^^^JBBJ
                                7BB577?5BBJ ~JJ!         .GBBGGGGGGBBJ
                                7BBGPPP5J~  :JJJ^.   .^^ .GBG^.::.?BBJ
                                7#B?         :7JJ?77?JJ?^:GBB:    7##Y
                                ~YY!           :~!77!!^. .JYJ.    ~YY7


                                National Paediatric Diabetes Audit 2024

                """
