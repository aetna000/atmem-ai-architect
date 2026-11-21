# The staging context supplies only reviewed runtime files and the emitted hash lock.
# The compiled package must also supply its owned enterprise-deployment.json.
FROM docker.io/library/python:3.13-slim-trixie@sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20 AS wheels
COPY requirements.lock /build/requirements.lock
RUN python -I -m pip --isolated download --only-binary=:all: --require-hashes --dest /wheels -r /build/requirements.lock
FROM docker.io/library/python:3.13-slim-trixie@sha256:48d884813cf44e927cf64c5529dd630dd3b18338c6dc727991eef9b71e934a20
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
ADD --checksum=sha256:8c27c342230503b73dfde629642c3b352e87b554e06d60cf58772f236a305ceb https://deb.debian.org/debian-security/pool/updates/main/z/zlib/zlib1g_1.3.dfsg%2breally1.3.1-1%2bdeb13u1_amd64.deb /tmp/zlib1g.deb
RUN dpkg -i /tmp/zlib1g.deb && rm /tmp/zlib1g.deb
COPY requirements.lock /app/requirements.lock
RUN --mount=type=bind,from=wheels,source=/wheels,target=/wheels,readonly python -I -m pip --isolated install --no-index --find-links=/wheels --only-binary=:all: --no-cache-dir --require-hashes -r /app/requirements.lock && python -I -m pip --isolated check && python -I -m pip --isolated uninstall --yes pip && rm -rf /usr/local/lib/python3.13/ensurepip
COPY runtime/ /app/
USER 10001:10001
CMD ["python", "-I", "/app/enterprise_native.py", "api"]
