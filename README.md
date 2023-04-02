# KoAlpacaDocker

# Build

## Setup environment

copy `dev/dev.env` to `.env`

```bash
cp dev/dev.env .env
```

## Download KoAlpaca weigths

```bash
python3 -m lib.chatbot
```

## Build Docker Image

```bash
docker build -t koalpaca .
```
