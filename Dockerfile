FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
# Install PhonePe SDK first with custom index URL (add trusted hosts + verbose for debugging)
RUN pip install --upgrade pip && \
    pip install \
      --index-url https://phonepe.mycloudrepo.io/public/repositories/phonepe-pg-sdk-python \
      --extra-index-url https://pypi.org/simple \
      --trusted-host phonepe.mycloudrepo.io \
      --trusted-host pypi.org \
      --trusted-host files.pythonhosted.org \
      --verbose \
      phonepe_sdk && \
    pip install -r /app/requirements.txt && \
    python - <<'PY'
import phonepe_sdk
print("PhonePe SDK installed successfully:", phonepe_sdk.__version__)
PY

# Copy backend project
COPY cert_platform /app/cert_platform

WORKDIR /app/cert_platform

# Collect static files (safe even if no static yet)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "cert_platform.wsgi:application", "--bind", "0.0.0.0:8000"]