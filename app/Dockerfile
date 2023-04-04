FROM --platform=linux/amd64 pytorch/pytorch:2.0.0-cuda11.7-cudnn8-runtime
LABEL maintainer="ldg55d@gmail.com"

RUN apt-get update && apt-get install -y git

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt 

COPY . /app/
COPY env/dev.env /app/.env

EXPOSE 8080

ENTRYPOINT [ "uvicorn", "main:api", "--host", "0.0.0.0", "--port", "8080" ]
