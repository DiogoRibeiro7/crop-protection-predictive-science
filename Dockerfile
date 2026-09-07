FROM python:3.12.14-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254 AS base

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
