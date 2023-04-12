import os
from typing import Union

import requests
from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from lib.logger import logger

load_dotenv()


PROMPT_DICT = {
    'prompt_input': (
        'Below is an instruction that describes a task, paired with an input that provides further context.\n'
        '아래는 작업을 설명하는 명령어와 추가적 맥락을 제공하는 입력이 짝을 이루는 예제입니다.\n\n'
        'Write a response that appropriately completes the request.\n요청을 적절히 완료하는 응답을 작성하세요.\n\n'
        '### Instruction(명령어):\n{instruction}\n\n### Input(입력):\n{context}\n\n### Response(응답):'
    ),
    'prompt_no_input': (
        'Below is an instruction that describes a task.\n'
        '아래는 작업을 설명하는 명령어입니다.\n\n'
        'Write a response that appropriately completes the request.\n명령어에 따른 요청을 적절히 완료하는 응답을 작성하세요.\n\n'
        '### Instruction(명령어):\n{instruction}\n\n### Response(응답):'
    ),
}


class Message(BaseModel):
    context: Union[str, None] = Field(
        default=None, title='context texts',
    )
    prompt: str
    temperature: float = Field(
        default=0.1, title='temperature',
    )


CHAT_ENDPOINT = os.environ['CHAT_ENDPOINT']
logger.info(f'CHAT_ENDPOINT: {CHAT_ENDPOINT}')
api = FastAPI()


@api.get('/healthz/')
async def healthz():
    return {
        'status': 'ok',
    }


@api.post('/v1/chat/')
async def chat(message: Message):
    logger.info(f'input: {message}')

    if message.context:
        message.prompt = PROMPT_DICT['prompt_input'].format(
            instruction=message.prompt,
            context=message.context,
        )
    else:
        message.prompt = PROMPT_DICT['prompt_no_input'].format(
            instruction=message.prompt,
        )

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