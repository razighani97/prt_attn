# One command rebuilds everything from raw.
# PYTHONPATH guards against macOS hiding the editable-install .pth file.
# caffeinate -i keeps the Mac from sleeping mid-collection (it stretched the
# first 15-minute audit to 7.5 hours).
PY = PYTHONPATH=src caffeinate -i uv run python

.PHONY: all env audit-wikipedia audit-gdelt audit-selection test

all: env audit-wikipedia audit-gdelt audit-selection

env:
	uv sync --all-extras

audit-wikipedia:
	$(PY) -m protest_attention.audit.wikipedia

audit-gdelt: audit-wikipedia
	$(PY) -m protest_attention.audit.gdelt

audit-selection: audit-wikipedia
	$(PY) -m protest_attention.audit.selection

test:
	PYTHONPATH=src uv run pytest -q
