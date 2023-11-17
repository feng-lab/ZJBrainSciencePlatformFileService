FROM python:3.11-alpine

RUN apk update && apk add curl

WORKDIR /code

COPY requirements.lock ./
RUN sed '/-e/d' requirements.lock > requirements.txt && rm requirements.lock
RUN pip install --no-cache-dir --requirement requirements.txt

COPY src ./

CMD uvicorn zjbs_file_server.main:app --host 0.0.0.0 --port 80
