import pytest

@pytest.hookimpl()
def pytest_html_report_title(report):
    report.title = "Consult Interface Test Report"
