import os
from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from lib.logger import logger
from lib import chatbot

load_dotenv()


class Message(BaseModel):
    context: Union[str, None] = Field(
        default=None, title='context texts',
    )
    prompt: str
    temperature: float = Field(
        default=0.1, title='temperature',
    )
    

model = None
tokenizer = None
api = FastAPI()


@api.on_event("startup")
async def startup_event():
    global tokenizer, model

    model_name = os.environ['MODEL_NAME']
    cache_dir= os.environ['CACHE_DIR']

    logger.info(f'Loading model: {model_name} with cache_dir: {cache_dir}')
    tokenizer, model = chatbot.setup_model(
        model_name=model_name,
        cache_dir=cache_dir,
    )
    logger.info('Model loaded')


@api.get('/healthz')
async def healthz():
    return {
        'status': 'ok',
    }


@api.post('/v1/chat')
async def chat(message: Message):
    logger.info(message)
    generation = chatbot.generate(
        tokenizer=tokenizer,
        model=model,
        prompt=message.prompt,
        context=message.context,
        temperature=message.temperature,
    )
    return {
        'generation': generation,
    }