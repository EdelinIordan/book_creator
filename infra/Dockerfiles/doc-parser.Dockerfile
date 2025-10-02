FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app:/workspace/libs/python

WORKDIR /app

COPY libs/python /workspace/libs/python
COPY services/doc-parser/requirements.txt ./requirements.txt

RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && pip install -e /workspace/libs/python \
    && rm -rf /root/.cache/pip

COPY services/doc-parser /app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9200"]
