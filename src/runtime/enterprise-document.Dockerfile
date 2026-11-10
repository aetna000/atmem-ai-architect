# Build the supplied invoice-parser.Dockerfile first, then pass its exact local image.
# The qualifier checks its source hashes before using it as the credentialless PDF base.
ARG PDF_PARSER_IMAGE
FROM docker.io/library/eclipse-temurin@sha256:f1309980e092cb762e6cbf78cf91b7fa0e7d3f3c5fc47a60a582f880b799aa48 AS document-build
ADD --checksum=sha256:f29d4e0d2cff1fc32396f6ac5ce436dfc7b19f9303d3b899e1f56fde85711c96 https://downloads.apache.org/tika/3.3.3/tika-app-3.3.3.jar /build/tika-app.jar
COPY EnterpriseDocument.java /build/EnterpriseDocument.java
RUN javac --release 17 -cp /build/tika-app.jar -d /build/classes /build/EnterpriseDocument.java && jlink --add-modules java.se,jdk.unsupported,jdk.crypto.ec --strip-debug --no-header-files --no-man-pages --output /build/java
FROM ${PDF_PARSER_IMAGE}
USER root
COPY --from=document-build /build/java /opt/java
COPY --chmod=0444 --from=document-build /build/tika-app.jar /app/tika-app.jar
COPY --from=document-build /build/classes /app/document-bridge
COPY enterprise_document_contract.py enterprise_document.py enterprise_document_cli.py enterprise_parser_service.py /app/
USER 10001:10001
CMD ["python", "-I", "/app/enterprise_document_cli.py"]
