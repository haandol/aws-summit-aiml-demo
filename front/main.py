import os
from typing import Union

import requests
from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from lib.logger import logger

load_dotenv()


class Message(BaseModel):
    context: Union[str, None] = Field(
        default=None, title='context texts',
    )
    prompt: str
    temperature: float = Field(
        default=0.1, title='temperature',
    )


CHAT_ENDPOINT = os.environ['CHAT_ENDPOINT']
api = FastAPI()


@api.get('/healthz/')
async def healthz():
    return {
        'status': 'ok',
    }


@api.post('/v1/chat')
async def chat(message: Message):
    logger.info(f'input: {message}')

    resp = requests.post(CHAT_ENDPOINT, json=message.dict())
    if resp.status_code != 200:
        return {
            'status': 'error',
            'message': 'failed to request to chat server..',
        }

    data = resp.json()
    logger.info(f'resp: {data}')
    if data['status'] == 'error':
        return {
            'status': 'error',
            'message': 'failed to generate text..',
        }

    return {
        'status': 'ok',
        'generation': data['generation'],
    }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(api, host='0.0.0.0', port=8080)