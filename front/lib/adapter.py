import re
import requests

from .logger import logger
from .prompt import PROMPT


class ChatbotAdapter(object):
    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint

    def generate(self,
        prompt: str,
        top_p: float = 0.8,
        max_new_tokens: int = 128,
        temperature: float = 0.2,
    ) -> str:
        body = {
            'prompt': prompt,
            'top_p': top_p,
            'max_new_tokens': max_new_tokens,
            'temperature': temperature,
        }
        resp = requests.post(self._endpoint, json=body, timeout=30)
        if resp.status_code != 200:
            raise Exception('failed to request to chat server..')

        data = resp.json()
        logger.info(f'resp: {data}')
        if data['status'] == 'error':
            raise Exception('failed to generate text..')

        return data['generation']

        
class SearchAdapter(object):
    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
    
    def search(self, q: str) -> str:
        resp = requests.get(self._endpoint, params={'q': q}, timeout=30)
        if resp.status_code != 200:
            raise Exception('failed to request to search server..')

        lines = []
        for article in resp.json():
            title = article['title'][0]
            link = article['link'][0]
            lines.append(f'<li><a href="{link}">{title}</a></li>')
        logger.info(f'lines: {lines}') 
        if lines:
            articles = ''.join(lines)
            return f'''
            <div>
                <p>Here are some articles I found about {q}:</p>
                <ul class="articles">
                    {articles}
                </ul>
            </div>
            '''.strip()
        else:
            return '''<p>No articles found.</p>'''


class QuestionClassifier(object):
    def __init__(self, adapter: ChatbotAdapter) -> None:
        self.adapter = adapter

    def classify(self, user_input: str) -> bool:
        prompt = PROMPT['question'].format(user_input=user_input)
        generation = self.adapter.generate(
            prompt=prompt,
            top_p=0.95,
            max_new_tokens=8,
            temperature=0.02,
        )
        logger.info(f'classify generation: {generation}')
        return 'question' in generation


class CategoryClassifier(object):
    def __init__(self, adapter: ChatbotAdapter) -> None:
        self.adapter = adapter
        self.pattern = re.compile(r'Category: (\w+)')

    def classify( self, user_input: str) -> str:
        prompt = PROMPT['category'].format(user_input=user_input)
        generation = self.adapter.generate(
            prompt=prompt,
            top_p=0.95,
            max_new_tokens=8,
            temperature=0.02,
        )
        logger.info(f'biz generation: {generation}')

        founds = self.pattern.findall(generation)
        logger.info(f'founds: {founds}')
        if founds:
            return founds[0]
        else:
            logger.warning('not found category')
            return 'Unknown'


class ChatGenerator(object):
    def __init__(self, adapter: ChatbotAdapter) -> None:
        self.adapter = adapter

    def generate( self, user_input: str, context: str = ''):
        prompt = PROMPT['chat'].format(user_input=user_input, context=context)
        generation = self.adapter.generate(
            prompt=prompt,
            top_p=0.8,
            max_new_tokens=128,
            temperature=0.2,
        )
        logger.info(f'chat generation: {generation}')
        return generation


class ArchitectureWhisperer(object):
    def __init__(self,
        chatbot_adapter: ChatbotAdapter,
        search_adapter: SearchAdapter,
    ) -> None:
        self.search_adapter = search_adapter
        self.question_classifier = QuestionClassifier(chatbot_adapter)
        self.category_classifier = CategoryClassifier(chatbot_adapter)
        self.chat_generator = ChatGenerator(chatbot_adapter)
        
    def orchestrate(self, user_input: str, context: str = ''):
        if not user_input:
            return 'You must input something.'

        logger.info(f'user_input: {user_input}')
        is_question = self.question_classifier.classify(user_input)
        logger.info(f'is_question: {is_question}')
        if is_question:
            category = self.category_classifier.classify(user_input)
            logger.info(f'category: {category}')
            if category != 'Unknown':
                return self.search_adapter.search(category)

        return self.chat_generator.generate(user_input=user_input, context=context)