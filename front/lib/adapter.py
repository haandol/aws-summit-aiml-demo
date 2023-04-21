import requests

from .logger import logger
from .prompt import PROMPT, CATEGORIES, CATEGORY_UNKNOWN


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
        body = {
            'prompt': prompt,
            'top_k': top_k,
            'top_p': top_p,
            'max_new_tokens': max_new_tokens,
            'temperature': temperature,
            'do_sample': do_sample,
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
        logger.info(f'q: {q}')
        resp = requests.get(self._endpoint, params={'q': q}, timeout=10)
        if resp.status_code != 200:
            raise Exception('failed to request to search server..')

        lines = []
        for article in resp.json():
            title = article['title']
            link = article['link']
            lines.append(f'<li><a href="{link}" target="_blank">{title}</a></li>')
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
            max_new_tokens=32,
        )
        logger.info(f'classify generation: {generation}')
        return 'question' in generation.lower()


class CategoryClassifier(object):
    def __init__(self, adapter: ChatbotAdapter) -> None:
        self.adapter = adapter

    def classify( self, user_input: str) -> str:
        prompt = PROMPT['category'].format(user_input=user_input, categories=CATEGORIES)
        generation = self.adapter.generate(
            prompt=prompt,
            max_new_tokens=32,
        )
        category = generation.strip().replace('.', '')
        logger.info(f'biz generation and category: {generation} => {category}')

        if category and category in CATEGORIES:
            return category
        else:
            logger.warning(f'not found category: {category}')
            return CATEGORY_UNKNOWN


class ChatGenerator(object):
    def __init__(self, adapter: ChatbotAdapter) -> None:
        self.adapter = adapter
        self.ID_SYMBOL = '[|'

    def refine(self, generation: str):
        sindex = generation.find(self.ID_SYMBOL)
        if sindex > 0:
            generation = generation[:sindex]
        return generation

    def generate(self, user_input: str, context: str = ''):
        prompt = PROMPT['chat'].format(user_input=user_input, context=context)
        generation = self.adapter.generate(
            prompt=prompt,
            top_k=50,
            top_p=0.92,
            max_new_tokens=256,
            temperature=0.4,
            do_sample=True,
        )
        refined = self.refine(generation)
        logger.info(f'chat generation and refined: {generation} => {refined}')
        return refined


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

            if category != CATEGORY_UNKNOWN:
                return self.search_adapter.search(category.lower().replace('.', ''))

        generation = self.chat_generator.generate(user_input=user_input, context=context)
        logger.info(f'generation: {generation}')
        return generation