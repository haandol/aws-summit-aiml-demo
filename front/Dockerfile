FROM --platform=linux/amd64 python:3.10-slim
LABEL maintainer="ldg55d@gmail.com"

RUN apt-get update && apt-get install -y curl

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt 

COPY . /app/
COPY env/dev.env /app/.env

EXPOSE 8080

ENTRYPOINT [ "uvicorn", "main:api", "--host", "0.0.0.0", "--port", "8080" ]
