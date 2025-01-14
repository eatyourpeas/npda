import pytest

from django.contrib.auth.models import Group

from project.npda.management.commands.create_groups import groups_seeder


def _seed_groups_fixture(django_db_setup, django_db_blocker):
    """
    Fixture which runs once per session to seed groups
    verbose=False
    """
    with django_db_blocker.unblock():

        if not Group.objects.all().exists():
            groups_seeder(
                run_create_groups=True,
                verbose=False,
            )
        else:
            print("Groups already seeded. Skipping")

@pytest.fixture(scope="session")
def seed_groups_fixture(django_db_setup, django_db_blocker):
    _seed_groups_fixture(django_db_setup, django_db_blocker)


# Required if multiple tests use transactional_db
@pytest.fixture(scope="function")
def seed_groups_per_function_fixture(django_db_setup, django_db_blocker):
    _seed_groups_fixture(django_db_setup, django_db_blocker)
