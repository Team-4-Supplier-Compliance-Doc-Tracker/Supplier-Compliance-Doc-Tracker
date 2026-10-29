# Runtime image for the compliance CLI.
# History lives on a volume at /data — never baked into the image (auditor retention).
FROM python:3.12-slim

WORKDIR /app

# Package is stdlib-only today (faker/pytest are for generate_data + CI, not the container).
COPY pyproject.toml .
COPY src/ ./src/

ENV PYTHONPATH=/app/src
ENV COMPLIANCE_DB_PATH=/data/compliance.db

VOLUME /data

ENTRYPOINT ["python", "-m", "compliance"]
