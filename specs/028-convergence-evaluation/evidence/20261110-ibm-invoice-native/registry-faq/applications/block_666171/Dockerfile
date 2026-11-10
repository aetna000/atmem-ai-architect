FROM docker.io/library/python:3.13-slim-trixie@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ADD --checksum=sha256:8c27c342230503b73dfde629642c3b352e87b554e06d60cf58772f236a305ceb https://deb.debian.org/debian-security/pool/updates/main/z/zlib/zlib1g_1.3.dfsg%2breally1.3.1-1%2bdeb13u1_amd64.deb /tmp/runtime-security.deb
RUN dpkg -i /tmp/runtime-security.deb && rm /tmp/runtime-security.deb
WORKDIR /app
COPY requirements.lock .
RUN python -I -m pip --isolated install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock && python -I -m pip --isolated uninstall --yes pip && rm -rf /usr/local/lib/python3.13/ensurepip
COPY public_faq.py public_catalog_store.py public_faq_app.py structured_http.py structured_output.py ibm_structured.py policy_review.py ./
COPY output-contract.json ./
COPY faq-deployment.json ./
COPY web/ ./web/
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "public_faq_app:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log", "--no-proxy-headers", "--limit-concurrency", "16"]
