FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Java is required for Spark-based integration and pipeline execution.
RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . .

CMD ["python", "Master_Run_Pipeline.py"]
