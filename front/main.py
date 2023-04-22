import os
import traceback

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from lib.logger import logger
from lib.adapter import ChatbotAdapter
from lib.service import ArchitectureWhisperer
from lib.o11y import tracer, context_from_headers

load_dotenv()
CHAT_ENDPOINT = os.environ['CHAT_ENDPOINT']
logger.info(f'CHAT_ENDPOINT: {CHAT_ENDPOINT}')

whisperer = ArchitectureWhisperer(
    chatbot_adapter=ChatbotAdapter(CHAT_ENDPOINT),
)

api = FastAPI()
FastAPIInstrumentor.instrument_app(api, excluded_urls="healthz/")


class Message(BaseModel):
    context: str = Field(
        default='', title='context texts',
    )
    prompt: str = Field(
        default='', title='prompt texts',
    )


@api.middleware("otel")
async def init_otel_span(request: Request, call_next):
    if request.url.path == '/healthz/':
        return await call_next(request)

    context = context_from_headers(request.headers)
    with tracer.start_as_current_span('root', context=context, kind=trace.SpanKind.SERVER) as span:
        span.set_attribute('service.name', 'front')
        span.set_attribute('http.method', request.method)
        span.set_attribute('http.url', str(request.url))
        span.set_attribute('http.user_agent', request.headers.get('User-Agent') or '')
        span.set_attribute('http.client_ip', request.headers.get('X-Forwarded-For') or '')

        response: Response = await call_next(request)
        span.set_attribute('http.status', response.status_code)
        if response.headers.get('X-Error') is None:
            span.set_status(trace.Status(trace.StatusCode.OK))
        else:
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            span.record_exception(Exception(response.headers.get('X-Error')))
        return response


@api.get('/healthz')
@api.get('/healthz/')
async def healthz():
    return {
        'status': 'ok',
    }


@api.post('/v1/chat')
@api.post('/v1/chat/')
async def chat(message: Message):
    with tracer.start_as_current_span('chat') as span:
        logger.info(f'user_input: {message.json()}')
        span.set_attribute('message', message.json())

        if not message.prompt:
            exc = Exception('Sorry, You must input something.')
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            return JSONResponse(content={
                'status': 'error',
                'type': 'chat',
                'generation': str(exc),
            }, headers={'X-Error': str(exc)})

        if len(message.prompt) > 180:
            exc = Exception('Sorry, Your input is too long. > 180 characters.')
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            return JSONResponse(content={
                'status': 'error',
                'type': 'chat',
                'generation': str(exc),
            }, headers={'X-Error': str(exc)})

        try:
            kind, generation = whisperer.orchestrate(
                user_input=message.prompt,
                context=message.context,
            )
            span.set_attribute('generation', generation)
            return JSONResponse(content={
                'status': 'ok',
                'type': kind,
                'generation': generation,
            })
        except Exception as exc:
            logger.exception(traceback.format_exc())
            span.record_exception(exc)
            span.set_attribute('error.traceback', traceback.format_exc())
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            return JSONResponse(content={
                'status': 'error',
                'type': 'chat',
                'generation': 'Sorry, it might be an internal error. I am calling my supervisor to fix it.'
            }, headers={'X-Error': str(exc)})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(api, host='0.0.0.0', port=8080)