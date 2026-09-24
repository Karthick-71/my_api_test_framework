"""The triage JUnit writer, exercised through a real pytest run (pytester)."""

import re

import pytest

pytest_plugins = ["pytester"]

SAMPLE = '''
import pytest

@pytest.mark.tc("TC-1", "Passes")
def test_pass():
    pass

@pytest.mark.tc("TC-2", "Order's total")
def test_fail_a():
    raise AssertionError("Expected HTTP 201 but got 500 for POST /api/orders\\n  request: id 17")

@pytest.mark.tc("TC-3", "Another")
def test_fail_b():
    raise AssertionError("Expected HTTP 201 but got 500 for POST /api/orders\\n  request: id 42")

@pytest.mark.skip(reason="parked")
@pytest.mark.tc("TC-4", "Skipped")
def test_skip():
    pass

@pytest.fixture
def broken():
    raise RuntimeError("database unavailable")

@pytest.mark.tc("TC-5", "Setup error")
def test_setup_error(broken):
    pass

def test_no_marker():
    """Docstring becomes the title."""
'''


@pytest.fixture
def run(pytester):
    pytester.makepyfile(test_sample=SAMPLE)
    out = pytester.path / "triage.xml"
    pytester.runpytest("-p", "framework.reporting.triage_junit", "--triage-junit", str(out))
    return out.read_text()


@pytest.mark.unit
def test_names_carry_id_and_quoted_title(run):
    assert "name=\"TC-1 'Passes'\"" in run
    assert "TC-2 'Order’s total'" in run  # inner quote replaced so the title parses


@pytest.mark.unit
def test_failure_first_line_is_the_message_not_source(run):
    bodies = re.findall(r"<failure message=\"([^\"]*)\">", run)
    assert bodies.count("AssertionError: Expected HTTP 201 but got 500 for POST /api/orders") == 2


@pytest.mark.unit
def test_setup_errors_and_skips_are_recorded(run):
    assert "setup error: RuntimeError: database unavailable" in run
    assert '<skipped message=""/>' in run
    assert 'tests="6" failures="3" skipped="1"' in run


@pytest.mark.unit
def test_unmarked_test_falls_back_to_name_and_docstring(run):
    assert "test_no_marker 'Docstring becomes the title.'" in run
