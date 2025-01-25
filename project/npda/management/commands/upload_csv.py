import json

from asgiref.sync import async_to_sync

from django.core.management.base import BaseCommand

from project.npda.models import NPDAUser
from project.npda.general_functions.csv import csv_upload, csv_parse, csv_header


class Command(BaseCommand):
    help = (
        "Upload a CSV file. Command line equivalent of uploading via the web interface"
    )

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="File to upload")

        parser.add_argument(
            "--user", type=int, default=1, help="PK of the user uploading the file"
        )

        parser.add_argument(
            "--pz-code",
            type=str,
            default="PZ999",
            help="PZ code of the PDU for the upload",
        )

    def handle(self, *args, **options):
        user_pk = options["user"]
        user = NPDAUser.objects.get(pk=user_pk)

        pdu_pz_code = options["pz_code"]

        is_jersey = pdu_pz_code == "PZ248"

        df = csv_parse(options["file"], is_jersey=is_jersey).df

        with open(options["file"], "r") as f:
            errors = async_to_sync(csv_upload)(user, df, f, pdu_pz_code)

        if errors:
            print(json.dumps(errors))
