# One command rebuilds everything from raw.
# PYTHONPATH guards against macOS hiding the editable-install .pth file.
# caffeinate -i keeps the Mac from sleeping mid-collection (it stretched the
# first 15-minute audit to 7.5 hours).
PY = PYTHONPATH=src caffeinate -i uv run python

.PHONY: all env audit-wikipedia test

all: env audit-wikipedia

env:
	uv sync --all-extras

audit-wikipedia:
	$(PY) -m protest_attention.audit.wikipedia

test:
	PYTHONPATH=src uv run pytest -q
