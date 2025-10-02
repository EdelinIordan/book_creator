FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace/orchestrator:/workspace/libs/python

WORKDIR /workspace/orchestrator

COPY libs/python /workspace/libs/python
COPY services/orchestrator/requirements.txt /workspace/requirements.txt

RUN pip install --upgrade pip \
    && pip install -r /workspace/requirements.txt \
    && pip install -e /workspace/libs/python[providers] \
    && rm -rf /root/.cache/pip

COPY services/orchestrator /workspace/orchestrator

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9100"]
