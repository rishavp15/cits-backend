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
COPY vendor/ /app/vendor/
COPY requirements.txt /app/requirements.txt
# Install vendored PhonePe SDK wheel (deterministic, no external index required)
RUN set -eux; \
    pip install --upgrade pip; \
    pip install /app/vendor/phonepe_sdk-2.1.5-py3-none-any.whl; \
    pip install -r /app/requirements.txt; \
    python - <<'PY' || true
import pkgutil
mods = [m.name for m in pkgutil.iter_modules() if "phonepe" in m.name.lower()]
print("PhonePe-related modules detected:", mods)
try:
    import phonepe_sdk
    print("phonepe_sdk import OK, version:", getattr(phonepe_sdk, "__version__", "unknown"))
except Exception as exc:
    print("phonepe_sdk import failed:", exc)
try:
    import phonepe
    print("phonepe import OK, version:", getattr(phonepe, "__version__", "unknown"))
except Exception as exc:
    print("phonepe import failed:", exc)
PY

# Copy backend project
COPY cert_platform /app/cert_platform

WORKDIR /app/cert_platform

# Collect static files (safe even if no static yet)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "cert_platform.wsgi:application", "--bind", "0.0.0.0:8000"]