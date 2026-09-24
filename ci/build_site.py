"""Assemble the GitHub Pages site for one CI run.

site/
  index.html          landing page: this run's totals and links
  report.html         pytest-html report for this run
  history/index.html  cross-build history (written by ci/update_history.sh)
"""

from __future__ import annotations

import argparse
import html
import os
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


def totals(junit: Path) -> dict:
    if not junit.exists():
        return {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "time": 0.0}
    root = ET.parse(junit).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    keys = ("tests", "failures", "errors", "skipped")
    out = {k: sum(int(s.get(k, 0)) for s in suites) for k in keys}
    out["time"] = sum(float(s.get("time", 0)) for s in suites)
    return out


def page(t: dict, build: str, build_url: str) -> str:
    failed = t["failures"] + t["errors"]
    passed = t["tests"] - failed - t["skipped"]
    ok = failed == 0 and t["tests"] > 0
    stamp = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    status = "All tests passed" if ok else f"{failed} failing"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>API test reports</title>
<style>
:root {{ --bg:#f6f5f1; --ink:#16191a; --mute:#5f6669; --line:#dcdad2; --card:#fff; --ok:#1a7a45; --bad:#b42318; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#0f1311; --ink:#e8ece9; --mute:#9aa39e; --line:#27302b;
  --card:#161d19; --ok:#5fd08c; --bad:#ff7a6b; }} }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:16px/1.55 system-ui, -apple-system, Segoe UI, sans-serif; }}
main {{ max-width:760px; margin:0 auto; padding:48px 16px; }}
h1 {{ font-size:28px; margin:0 0 4px; }} p {{ color:var(--mute); margin:0 0 24px; }}
.status {{ display:inline-block; padding:4px 12px; border-radius:999px; font-weight:600;
  color:{"var(--ok)" if ok else "var(--bad)"}; border:1px solid currentColor; margin-bottom:24px; }}
.grid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:28px; }}
.grid div {{ background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px; }}
.grid b {{ display:block; font-size:24px; }} .grid span {{ color:var(--mute); font-size:13px; }}
a.card {{ display:block; background:var(--card); border:1px solid var(--line); border-radius:12px; padding:18px;
  margin-bottom:12px; color:inherit; text-decoration:none; }}
a.card:hover {{ border-color:var(--ok); }} a.card b {{ display:block; font-size:18px; }}
a.card span {{ color:var(--mute); font-size:14px; }}
footer {{ margin-top:28px; font-size:13px; color:var(--mute); }} footer a {{ color:inherit; }}
@media (max-width:560px) {{ .grid {{ grid-template-columns:repeat(2,1fr); }} }}
</style></head><body><main>
<h1>API test reports</h1>
<p>Pytest suite for the Orders API · build #{html.escape(build)} · {stamp}</p>
<span class="status">{status}</span>
<div class="grid">
  <div><b>{t["tests"]}</b><span>tests</span></div>
  <div><b>{passed}</b><span>passed</span></div>
  <div><b>{failed}</b><span>failed</span></div>
  <div><b>{t["time"]:.1f}s</b><span>duration</span></div>
</div>
<a class="card" href="history/"><b>Test history &rarr;</b>
  <span>Every test across every build, flaky-test detection and failures grouped by root cause.</span></a>
<a class="card" href="report.html"><b>This run's report &rarr;</b>
  <span>Per-test results, logs and request/response detail for build #{html.escape(build)}.</span></a>
<footer><a href="{html.escape(build_url)}">CI run</a> · History report by
<a href="https://github.com/ParthiCM/playwright-test-history">Playwright Test History</a></footer>
</main></body></html>
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reports", type=Path, required=True)
    ap.add_argument("--history", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    report = args.reports / "report.html"
    if report.exists():
        shutil.copy(report, args.out / "report.html")
    build = os.getenv("BUILD_NUMBER", "local")
    build_url = os.getenv("BUILD_URL", "#")
    (args.out / "index.html").write_text(page(totals(args.reports / "junit.xml"), build, build_url), encoding="utf-8")
    (args.out / ".nojekyll").write_text("")
    print(f"site written to {args.out}")


if __name__ == "__main__":
    main()
