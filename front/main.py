import os
import traceback

from fastapi import FastAPI, Request, Response
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.core.sampling.local.sampler import LocalSampler
from aws_xray_sdk.core.models import http

from lib.logger import logger
from lib.adapter import ChatbotAdapter, SearchAdapter, ArchitectureWhisperer

plugins = ('ECSPlugin',)
xray_recorder.configure(
    sampling=False,
    service='front',
    plugins=plugins,
)
patch_all()
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

@api.middleware("xray")
async def init_xray_segment(request: Request, call_next):
    if request.url.path == '/healthz/':
        return await call_next(request)

    segment = xray_recorder.begin_segment(name=request.url.path)
    segment.put_http_meta(http.URL, str(request.url))
    segment.put_http_meta(http.USER_AGENT, request.headers.get('User-Agent'))
    segment.put_http_meta(http.X_FORWARDED_FOR, request.headers.get('X-Forwarded-For'))
    segment.put_http_meta(http.XRAY_HEADER, segment.trace_id)
    segment.put_http_meta(http.METHOD, request.method)

    response: Response = await call_next(request)
    segment.put_http_meta(http.STATUS, response.status_code)
    xray_recorder.end_segment()
    return response


@api.get('/healthz/')
async def healthz():
    return {
        'status': 'ok',
    }


@api.post('/v1/chat/')
async def chat(message: Message):
    with xray_recorder.in_subsegment('chat') as segment:
        logger.info(f'user_input: {message.json()}')
        segment.put_metadata('message', message.json())

        if not message.prompt:
            segment.add_exception(Exception('Sorry, You must input something.'), None)
            return {
                'status': 'error',
                'type': 'chat',
                'generation': 'Sorry, You must input something.'
            }

        if len(message.prompt) > 180:
            segment.add_exception(Exception('Sorry, Your input is too long. > 180 characters.'), None)
            return {
                'status': 'error',
                'type': 'chat',
                'generation': 'Sorry, Your input is too long. > 180 characters.'
            }

        try:
            kind, generation = whisperer.orchestrate(user_input=message.prompt, context=message.context)
            segment.put_metadata('generation', generation)
            return {
                'status': 'ok',
                'type': kind,
                'generation': generation,
            }
        except Exception as e:
            logger.exception(traceback.format_exc())
            segment.add_exception(e, traceback.extract_stack())
            return {
                'status': 'error',
                'type': 'chat',
                'generation': 'Sorry, it might be an internal error. I am calling my supervisor to fix it.'
            }


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(api, host='0.0.0.0', port=8080)