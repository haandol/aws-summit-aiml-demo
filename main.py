import os
from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from lib import logger, chatbot

load_dotenv()


class Message(BaseModel):
    context: Union[str, None] = Field(
        default=None, title='context texts',
    )
    prompt: str
    

model = None
tokenizer = None
api = FastAPI()


@api.on_event("startup")
async def startup_event():
    global tokenizer, model

    model_name = os.environ['MODEL_NAME']
    cache_dir= os.environ['CACHE_DIR']
    tokenizer, model = chatbot.setup_model(
        model_name=model_name,
        cache_dir=cache_dir,
    )


@api.post('/v1/chat')
async def chat(message: Message):
    logger.info(message)
    generation = chatbot.generate(
        tokenizer=tokenizer,
        model=model,
        prompt=message.prompt,
        context=message.context
    )
    return {
        'generation': generation,
    }