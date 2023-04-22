import json
import requests

from opentelemetry import trace

from .o11y import tracer
from .logger import logger


class ChatbotAdapter(object):
    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint

    def generate(self,
        prompt: str,
        top_k: int = 0,
        top_p: float = 1.0,
        max_new_tokens: int = 32,
        temperature: float = 0.5,
        do_sample: bool = False,
    ) -> str:
        with tracer.start_as_current_span('chatbot adapter') as span:
            body = {
                'prompt': prompt,
                'top_k': top_k,
                'top_p': top_p,
                'max_new_tokens': max_new_tokens,
                'temperature': temperature,
                'do_sample': do_sample,
            }
            span.set_attribute('body', json.dumps(body))

            headers = {}
            span_context = span.get_span_context()
            if span_context.is_valid:
                headers['X-Amzn-Trace-Id'] = f'Root={span_context.trace_id};Parent={span_context.span_id};Sampled=1'

            resp = requests.post(self._endpoint, json=body, headers=headers, timeout=30)
            if resp.status_code != 200:
                raise Exception('failed to request to chat server..')

            data = resp.json()
            logger.info(f'resp: {data}')
            span.set_attribute('response', json.dumps(data))
            if data['status'] == 'error':
                exc = Exception('failed to generate text..')
                span.record_exception(exc)
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                raise exc

            return data['generation']