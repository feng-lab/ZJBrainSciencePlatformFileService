FROM python:3.11-alpine

WORKDIR /code
COPY src /code/
COPY requirements.lock pyproject.toml README.md /code/

RUN pip install --requirement /code/requirements.lock

CMD uvicorn zjbs_file_server.app:app --host 0.0.0.0 --port 80
