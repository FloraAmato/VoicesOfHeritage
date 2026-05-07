FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.110" "uvicorn[standard]>=0.27" "pydantic>=2.6" "pydantic-settings>=2.2" \
    "numpy>=1.26" "pandas>=2.2" "scikit-learn>=1.4" "sqlalchemy>=2.0" \
    "websockets>=12.0" "pyyaml>=6.0" "python-multipart>=0.0.9" "joblib>=1.3"

COPY app ./app
COPY config ./config
COPY tests ./tests

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
