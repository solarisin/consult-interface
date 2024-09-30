import logging

import pytest
from tests.data_registry import DataRegistry

# pytest fixtures

@pytest.fixture(scope="session")
def project_root_path(request):
    return request.config.rootpath

@pytest.fixture(scope="session")
def data_registry(project_root_path):
    logging.warn('INITIALIZATION')
    yield DataRegistry.get_registry(project_root_path)
    logging.warn('TEAR DOWN')

# pytest hooks

@pytest.hookimpl()
def pytest_html_report_title(report):
    report.title = "Consult Interface Test Report"
