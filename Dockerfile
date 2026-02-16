FROM python:3.11-slim

# System deps for OCR (pytesseract + pdf2image)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-fra \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user and give ownership of app directory
RUN useradd --create-home appuser && \
    mkdir -p uploads && \
    chown -R appuser:appuser /app

USER appuser

# Ensure Python output is unbuffered (visible in container logs immediately)
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Default CMD; Railway overrides via railway.toml startCommand
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
