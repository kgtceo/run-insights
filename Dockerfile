FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
CMD ["sh", "-c", "python -m uvicorn run_insights.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
