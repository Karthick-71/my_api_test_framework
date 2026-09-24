"""Pytest plugin: write a JUnit file shaped for Playwright Test History.

Playwright Test History (https://github.com/ParthiCM/playwright-test-history)
builds a cross-build test matrix and groups failures by cause from a JUnit
file. Pytest's own --junitxml works, but two details make the grouping weak:

1. It reads the test id from the test name (TC-1042 style). Pytest names are
   function names, so every parametrised case would need an id in its name.
2. It groups failures by the first line of the failure text. Pytest puts the
   failing *source line* first, so no two tests ever share a signature.

This plugin writes a second JUnit file that fixes both:
    name     = "TC-1001 'Create order with valid payload'"  (id from @pytest.mark.tc)
    failure  = first line is the exception message, then "at file:line"

Enable it with:  pytest --triage-junit reports/junit-triage.xml
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

import pytest

MARKER = "tc"


@dataclass
class _Case:
    tc_id: str
    title: str
    classname: str
    outcome: str = "passed"  # passed | failed | skipped
    message: str = ""
    location: str = ""
    duration: float = 0.0


def pytest_addoption(parser):
    parser.addoption(
        "--triage-junit",
        action="store",
        default=None,
        metavar="PATH",
        help="Also write a JUnit file shaped for Playwright Test History to PATH.",
    )


def pytest_configure(config):
    config.addinivalue_line("markers", f"{MARKER}(id, title): test case id and title used in reports")
    path = config.getoption("--triage-junit")
    if path and not hasattr(config, "workerinput"):  # skip on xdist workers
        config.pluginmanager.register(TriageJUnitWriter(Path(path)), "triage-junit-writer")


def _clean_title(text: str) -> str:
    # The history tool takes a quoted segment as the title, so quotes inside it must go.
    return re.sub(r"\s+", " ", text.replace("'", "’").replace('"', "’")).strip()


def _fallback_id(item) -> str:
    return item.nodeid.split("::", 1)[-1]


class TriageJUnitWriter:
    def __init__(self, path: Path):
        self.path = path
        self.cases: dict[str, _Case] = {}

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items):
        for item in items:
            marker = item.get_closest_marker(MARKER)
            if marker and marker.args:
                tc_id = str(marker.args[0])
                title = str(marker.args[1]) if len(marker.args) > 1 else item.name
            else:
                tc_id, title = _fallback_id(item), (item.function.__doc__ or item.name).strip().splitlines()[0]
            self.cases[item.nodeid] = _Case(tc_id, _clean_title(title), item.location[0])

    def pytest_runtest_logreport(self, report):
        case = self.cases.get(report.nodeid)
        if case is None:
            return
        case.duration += getattr(report, "duration", 0.0) or 0.0

        if report.failed and case.outcome != "failed":
            case.outcome = "failed"
            case.message, case.location = self._failure(report)
        elif report.skipped and case.outcome == "passed":
            case.outcome = "skipped"
            if hasattr(report, "wasxfail"):
                case.message = f"xfail: {report.wasxfail}"

    @staticmethod
    def _failure(report) -> tuple[str, str]:
        prefix = "" if report.when == "call" else f"{report.when} error: "
        crash = getattr(report.longrepr, "reprcrash", None)
        if crash is not None:
            first = crash.message.strip().splitlines()[0] if crash.message.strip() else "failed"
            return prefix + first, f"{crash.path}:{crash.lineno}"
        text = str(report.longrepr).strip().splitlines()
        return prefix + (text[-1] if text else "failed"), ""

    def pytest_sessionfinish(self, session):
        cases = list(self.cases.values())
        failures = sum(c.outcome == "failed" for c in cases)
        skipped = sum(c.outcome == "skipped" for c in cases)
        total_time = sum(c.duration for c in cases)

        lines = [
            '<?xml version="1.0" encoding="utf-8"?>',
            f'<testsuites tests="{len(cases)}" failures="{failures}" skipped="{skipped}" time="{total_time:.3f}">',
            f'  <testsuite name="pytest" tests="{len(cases)}" failures="{failures}" skipped="{skipped}"'
            f' time="{total_time:.3f}">',
        ]
        for c in cases:
            name = quoteattr(f"{c.tc_id} '{c.title}'")
            open_tag = f'    <testcase name={name} classname={quoteattr(c.classname)} time="{c.duration:.3f}"'
            if c.outcome == "passed":
                lines.append(open_tag + "/>")
            elif c.outcome == "skipped":
                lines.append(open_tag + ">")
                lines.append(f"      <skipped message={quoteattr(c.message)}/>")
                lines.append("    </testcase>")
            else:
                body = c.message + (f"\n    at {c.location}" if c.location else "")
                lines.append(open_tag + ">")
                lines.append(f"      <failure message={quoteattr(c.message)}>{escape(body)}</failure>")
                lines.append("    </testcase>")
        lines += ["  </testsuite>", "</testsuites>", ""]

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(lines), encoding="utf-8")

    def pytest_terminal_summary(self, terminalreporter):
        terminalreporter.write_sep("-", f"triage junit: {self.path}")
