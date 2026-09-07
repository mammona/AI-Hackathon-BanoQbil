# ---- AI Fasal Shield Backend – Docker image ----
# Python 3.11 slim + CPU-only PyTorch  →  ~2.5 GB image
FROM python:3.11-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered log output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ---- system dependencies (small, cached layer) ----
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# ---- Python dependencies ----
# Install CPU-only PyTorch first (large, cached layer)
RUN pip install --no-cache-dir \
    "torch>=2.6,<2.12" --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir \
    "torchvision>=0.21,<0.27" --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- application code ----
COPY . .

# Ensure data directories exist
RUN mkdir -p data/reports

# Expose the FastAPI port
EXPOSE 8000

# Health-check: hit the /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start the FastAPI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
