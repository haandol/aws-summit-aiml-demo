import os
import traceback
from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from lib.logger import logger
from lib.adapter import ChatbotAdapter, SearchAdapter, ArchitectureWhisperer

load_dotenv()


class Message(BaseModel):
    context: str = Field(
        default='', title='context texts',
    )
    prompt: str = Field(
        default='', title='prompt texts',
    )


SEARCH_ENDPOINT = os.environ['SEARCH_ENDPOINT']
logger.info(f'SEARCH_ENDPOINT: {SEARCH_ENDPOINT}')
CHAT_ENDPOINT = os.environ['CHAT_ENDPOINT']
logger.info(f'CHAT_ENDPOINT: {CHAT_ENDPOINT}')

whisperer = ArchitectureWhisperer(
    chatbot_adapter=ChatbotAdapter(CHAT_ENDPOINT),
    search_adapter=SearchAdapter(SEARCH_ENDPOINT),
)

api = FastAPI()


@api.get('/healthz/')
async def healthz():
    return {
        'status': 'ok',
    }


@api.post('/v1/chat/')
async def chat(message: Message):
    logger.info(f'user_input: {message}')

    if not message.prompt:
        return {
            'status': 'error',
            'generation': 'Sorry, You must input something.'
        }

    try:
        generation = whisperer.orchestrate(user_input=message.prompt[:200], context=message.context[-500:])
        return {
            'status': 'ok',
            'generation': generation,
        }
    except:
        logger.exception(traceback.format_exc())
        return {
            'status': 'error',
            'generation': 'Sorry, I could not understand your question.'
        }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(api, host='0.0.0.0', port=8080)