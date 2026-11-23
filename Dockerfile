FROM python:3.15.2-slim-bookworm@sha256:96599df822d0e1c6bb700014a05c7f3c8cabc6e0f7ff3c4f9f69cee033b4b5d9 AS base

ENV POETRY_VERSION=2.4.3 \
    POETRY_VIRTUALENVS_CREATE=false \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN python -m pip install --no-cache-dir "poetry==${POETRY_VERSION}"

COPY pyproject.toml poetry.lock README.md ./
RUN poetry check --lock && poetry install --only main --no-interaction --no-root

COPY src ./src
COPY configs ./configs
COPY data ./data

RUN poetry install --only main --no-interaction \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

FROM base AS runtime

USER appuser
CMD ["crop-protection-demo"]

FROM base AS scientific-test

RUN poetry install --with dev --no-interaction
COPY tests ./tests
RUN chown -R appuser:appuser /app

USER appuser
CMD ["poetry", "run", "pytest", "tests/test_scientific_contract.py"]
