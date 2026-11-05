# display help information
default:
    @just --list


# clean the project
clean:
    rm -rf .venv/


# install the dependencies
install:
    uv sync --all-groups
    uvx prek install


# format with ruff
format:
    uvx ruff format

# lint with ruff
lint:
    uvx ruff check

# Run pre-commit [lint, format]"
pre-commit: lint format
    uvx prek run

# test with pytest
test:
    uv run pytest

# serve the documentation locally
docs:
    uv run --only-group docs mkdocs serve
