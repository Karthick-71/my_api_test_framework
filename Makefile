.PHONY: install test smoke lint format api data history clean

PY ?= .venv/bin/python

install:            ## create .venv and install dependencies
	python3 -m venv .venv
	$(PY) -m pip install -q --upgrade pip
	$(PY) -m pip install -q -r requirements.txt

test:               ## full suite (starts the Orders API automatically)
	$(PY) -m pytest

smoke:              ## fast subset
	$(PY) -m pytest -m smoke

lint:
	$(PY) -m ruff check .
	$(PY) -m ruff format --check .

format:
	$(PY) -m ruff format .
	$(PY) -m ruff check . --fix

api:                ## run the Orders API on :8000 for manual exploring (docs at /docs)
	$(PY) -m uvicorn sut.orders_api:app --reload --port 8000

data:               ## rebuild test_data/api_test_cases.xlsx from tools/build_test_data.py
	$(PY) tools/build_test_data.py

history:            ## record reports/junit-triage.xml into a local history (needs Node 18+)
	@test -d .triage-tool || git clone -q https://github.com/ParthiCM/playwright-test-history.git .triage-tool
	node .triage-tool/src/triage-report.js $$(test -d .history/store || echo --init) \
	  --junit reports/junit-triage.xml --build $$(ls .history/store 2>/dev/null | wc -l | xargs expr 1 +) \
	  --env dev --job my_api_test_framework --store .history/store --out reports/history/index.html

clean:
	rm -rf reports site .pytest_cache orders.db
