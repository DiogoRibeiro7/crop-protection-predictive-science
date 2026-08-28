FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs
RUN poetry config virtualenvs.create false && poetry install --only main --no-interaction
CMD ["crop-protection-demo"]
