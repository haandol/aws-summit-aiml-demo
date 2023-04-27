FROM --platform=linux/amd64 nvidia/cuda:12.1.0-devel-ubuntu20.04
LABEL maintainer="ldg55d@gmail.com"

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git \
    curl \
    software-properties-common \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt install -y python3.10 \
    && rm -rf /var/lib/apt/lists/* \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3.10

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt 

COPY . /app/
COPY env/dev.env /app/.env

EXPOSE 8080

ENTRYPOINT [ "uvicorn", "main:api", "--host", "0.0.0.0", "--port", "8080" ]
