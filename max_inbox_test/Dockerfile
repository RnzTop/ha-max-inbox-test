FROM python:3.13-alpine@sha256:9cf2fdca7b3dd6082fd160ff5b8664f108c7441e200018a36554b2e8028f45df
WORKDIR /app
COPY inbox.py demo.py ./
ENV PYTHONUNBUFFERED=1
CMD ["python", "/app/demo.py", "/data/inbox.sqlite3", "0.0.0.0", "8099"]
