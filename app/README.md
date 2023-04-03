# KoAlpacaDocker

model weight file will be placed at EFS

# Build

## Setup environment

copy `dev/local.env` to `.env`

```bash
cp dev/local.env .env
```

## Download KoAlpaca weigths

```bash
python3 -m lib.chatbot
```

## Build Docker Image

```bash
docker build -t koalpaca .
```
