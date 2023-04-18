import os
import traceback

from fastapi import FastAPI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from lib.logger import logger
from lib import chatbot

load_dotenv()


class Message(BaseModel):
    prompt: str
    top_p: float = Field(
        default=0.8, title='top_p',
    )
    max_new_tokens: int = Field(
        default=128, title='max_new_tokens',
    )
    temperature: float = Field(
        default=0.2, title='temperature',
    )
    

api = FastAPI()

model_name = os.environ['MODEL_NAME']
cache_dir= os.environ['CACHE_DIR']

logger.info(f'Loading model: {model_name} with cache_dir: {cache_dir}')
tokenizer, model = chatbot.setup_model(
    model_name=model_name,
    cache_dir=cache_dir,
)
logger.info('Model loaded')


@api.get('/healthz/')
async def healthz():
    return {
        'status': 'ok',
    }


@api.post('/v1/chat/')
async def chat(message: Message):
    global tokenizer
    global model

    logger.info(message)
    try:
        generation = chatbot.generate(
            tokenizer=tokenizer,
            model=model,
            prompt=message.prompt,
            top_p=message.top_p,
            max_new_tokens=message.max_new_tokens,
            temperature=message.temperature,
        )
        return {
            'status': 'ok',
            'generation': generation,
        }
    except:
        return {
            'status': 'error',
            'message': traceback.format_exc(),
        }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(api, host='0.0.0.0', port=8080)