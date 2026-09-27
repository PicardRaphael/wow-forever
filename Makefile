.PHONY: test test-fast lint fmt typecheck registry numbers verify status
# Les cibles tolèrent un projet encore vide (avant T01) : pytest renvoie 5 quand il n'y a aucun test.

test:
	uv run pytest -q || [ $$? -eq 5 ]

test-fast:
	@if [ -d tests/unit ]; then uv run pytest -q -m "not slow" tests/unit || [ $$? -eq 5 ]; else echo "tests/unit absent"; fi

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

typecheck:
	@if [ -d forever ]; then uv run mypy forever; else echo "forever/ absent"; fi

registry:
	uv run python scripts/check_registry.py $(REGISTRY_FLAGS)

numbers:
	uv run python scripts/check_game_numbers.py

verify: lint typecheck test registry numbers

status:
	uv run forever status
