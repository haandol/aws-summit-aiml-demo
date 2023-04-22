import os
import traceback
import threading

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from lib.logger import logger
from lib import chatbot
from lib.o11y import tracer, context_from_headers

load_dotenv()
model_name = os.environ['MODEL_NAME']
cache_dir= os.environ['CACHE_DIR']
load_in_8bit= bool(os.environ.get('LOAD_IN_8BIT', False))
logger.info(f'Loading model: {model_name} with cache_dir: {cache_dir} and load_in_8bit: {load_in_8bit}')

model, tokenizer, is_ready = None, None, False

api = FastAPI()
FastAPIInstrumentor.instrument_app(api, excluded_urls="healthz/")


class BackgroundModelLoader(threading.Thread):
    def run(self, *args, **kwargs):
        global model, tokenizer, is_ready
        logger.info(f'Loading model: {model_name} with cache_dir: {cache_dir}')
        tokenizer, model = chatbot.setup_model(
            model_name=model_name,
            cache_dir=cache_dir,
            load_in_8bit=load_in_8bit,
        )
        logger.info('Model loaded')
        is_ready = True


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


@api.middleware("otel")
async def init_otel_span(request: Request, call_next):
    if request.url.path == '/healthz/':
        return await call_next(request)

    context = context_from_headers(request.headers)
    with tracer.start_as_current_span('root', context=context, kind=trace.SpanKind.SERVER) as span:
        span.set_attribute('service.name', 'chatbot')
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


@api.on_event('startup')
async def startup_event():
    t = BackgroundModelLoader()
    t.start()


@api.get('/healthz')
@api.get('/healthz/')
async def healthz():
    return {
        'status': 'ok',
    }


@api.get('/readyz')
@api.get('/readyz/')
async def readyz():
    return {
        'status': is_ready,
    }


@api.post('/v1/chat')
@api.post('/v1/chat/')
async def chat(message: Message):
    with tracer.start_as_current_span('chat') as span:
        logger.info(f'user_input: {message.json()}')
        span.set_attribute('message', message.json())
        span.set_attribute('is_ready', is_ready)

        if not is_ready:
            exc = Exception('the model is not ready yet')
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            return JSONResponse(content={
                'status': 'error',
                'generation': str(exc),
            }, headers={'X-Error': str(exc)})

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
            return JSONResponse(content={
                'status': 'ok',
                'generation': generation,
            })
        except Exception as exc:
            logger.exception(traceback.format_exc())
            span.record_exception(exc)
            span.set_attribute('traceback', traceback.format_exc())
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            return JSONResponse(content={
                'status': 'error',
                'message': traceback.format_exc(),
            }, headers={'X-Error': str(exc)})


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(api, host='0.0.0.0', port=8080)