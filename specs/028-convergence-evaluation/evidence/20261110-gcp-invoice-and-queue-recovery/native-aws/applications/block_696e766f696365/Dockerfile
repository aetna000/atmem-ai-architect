FROM docker.io/library/python:3.13-slim-trixie@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
ADD --checksum=sha256:8c27c342230503b73dfde629642c3b352e87b554e06d60cf58772f236a305ceb https://deb.debian.org/debian-security/pool/updates/main/z/zlib/zlib1g_1.3.dfsg%2breally1.3.1-1%2bdeb13u1_amd64.deb /tmp/runtime-security.deb
RUN dpkg -i /tmp/runtime-security.deb && rm /tmp/runtime-security.deb
WORKDIR /app
COPY requirements.lock .
RUN python -I -m pip --isolated install --no-cache-dir --only-binary=:all: --require-hashes -r requirements.lock && python -I -m pip --isolated uninstall --yes pip && rm -rf /usr/local/lib/python3.13/ensurepip
COPY durable_workflow.py workflow_connection.py workflow_contract.py workflow_database.py workflow_errors.py workflow_process_stage.py workflow_role_bootstrap.py workflow_worker.py invoice_document.py invoice_extraction.py invoice_object_store.py invoice_http.py invoice_identity.py invoice_native.py invoice_runtime_secrets.py invoice_processing.py invoice_parser_transport.py invoice_stage.py invoice_worker.py invoice_web.py approved_http_destination.py structured_output.py structured_http.py policy_review.py aws_json_model.py azure_structured.py gcp_structured.py ibm_structured.py invoice_parser_identity.py invoice_retention.py invoice_operations.py invoice_operator.py ./
COPY invoice-deployment.json ./
COPY workflow_schema.sql invoice-web.html invoice-web.css invoice-web.js rds-global-ca.pem ./
USER 10001:10001
EXPOSE 8080
CMD ["python", "-m", "uvicorn", "invoice_native:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--no-access-log", "--no-proxy-headers", "--limit-concurrency", "32"]
