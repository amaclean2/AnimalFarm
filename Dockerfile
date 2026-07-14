FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "aiofiles>=23.0.0"

COPY *.py ./
COPY agents/ ./agents/
COPY routers/ ./routers/
COPY world/ ./world/
COPY static/ ./static/

RUN mkdir -p /app/logs

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
