# One command rebuilds everything from raw.
# PYTHONPATH guards against macOS hiding the editable-install .pth file.
# caffeinate -i keeps the Mac from sleeping mid-collection (it stretched the
# first 15-minute audit to 7.5 hours).
PY = PYTHONPATH=src caffeinate -i uv run python

.PHONY: all env audit-wikipedia audit-gdelt audit-selection collect-a clean-a analyse-a plot-a project-a collect-events test

all: env audit-wikipedia audit-selection project-a

env:
	uv sync --all-extras

audit-wikipedia:
	$(PY) -m protest_attention.audit.wikipedia

audit-gdelt: audit-wikipedia
	$(PY) -m protest_attention.audit.gdelt

audit-selection: audit-wikipedia
	$(PY) -m protest_attention.audit.selection

collect-a:
	$(PY) -m protest_attention.collect.project_a

clean-a:
	$(PY) -m protest_attention.clean.project_a

analyse-a: clean-a
	$(PY) -m protest_attention.analyse.decay

plot-a: analyse-a
	$(PY) -m protest_attention.plot.decay

project-a: collect-a
	$(MAKE) plot-a

collect-events:
	$(PY) -m protest_attention.collect.gdelt_events

test:
	PYTHONPATH=src uv run pytest -q
