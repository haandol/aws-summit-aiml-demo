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
    top_k: int = Field(
        default=0, title='top_k',
    )
    top_p: float = Field(
        default=1, title='top_p',
    )
    max_new_tokens: int = Field(
        default=32, title='max_new_tokens',
    )
    temperature: float = Field(
        default=0.5, title='temperature',
    )
    do_sample: bool = Field(
        default=False, title='do_sample',
    )


api = FastAPI()

model_name = os.environ['MODEL_NAME']
cache_dir= os.environ['CACHE_DIR']
load_in_8bit= bool(os.environ.get('LOAD_IN_8BIT', False))

logger.info(f'Loading model: {model_name} with cache_dir: {cache_dir}')
tokenizer, model = chatbot.setup_model(
    model_name=model_name,
    cache_dir=cache_dir,
    load_in_8bit=load_in_8bit,
)
logger.info('Model loaded')


@api.get('/healthz')
@api.get('/healthz/')
async def healthz():
    return {
        'status': 'ok',
    }


@api.post('/v1/chat')
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
            top_k=message.top_k,
            top_p=message.top_p,
            max_new_tokens=message.max_new_tokens,
            temperature=message.temperature,
            do_sample=message.do_sample,
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