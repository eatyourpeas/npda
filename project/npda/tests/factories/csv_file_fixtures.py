import pytest

@pytest.fixture
def dummy_sheets_folder(request):
    return request.config.rootdir / 'project' / 'npda' / 'dummy_sheets'

@pytest.fixture
def dummy_sheet_csv(dummy_sheets_folder):
    file = dummy_sheets_folder / 'dummy_sheet.csv'
    with open(file, 'r') as f:
        return f.read()