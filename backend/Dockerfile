FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DEFAULT_TIMEOUT=240 PIP_RETRIES=10
WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN python -m pip install --no-cache-dir --retries 10 --timeout 240 -r /tmp/requirements.txt
COPY backend/app/ /app/app/
COPY infra/certgen.py /app/certgen.py
# UI sem npm/npm registry: evita erros de build por dependência JavaScript na rede.
COPY frontend/static/ /app/ui/
EXPOSE 8443 9443
CMD ["python","-m","app.gateway"]
