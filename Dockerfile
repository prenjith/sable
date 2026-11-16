FROM python:3.12-slim

WORKDIR /app
COPY sable.py lsp.py /app/

ENTRYPOINT ["python3", "/app/sable.py"]
