FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create non-root user
RUN useradd --create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

# Ensure Python output is unbuffered (visible in container logs immediately)
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# start.py reads PORT from env (Railway sets it dynamically)
CMD ["python", "start.py"]
