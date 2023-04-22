from .o11y import tracer
from .logger import logger
from .adapter import ChatbotAdapter
from .prompt import PROMPT, CATEGORIES, CATEGORY_UNKNOWN


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
    ) -> None:
        self.question_classifier = QuestionClassifier(chatbot_adapter)
        self.category_classifier = CategoryClassifier(chatbot_adapter)
        self.chat_generator = ChatGenerator(chatbot_adapter)

    def orchestrate(self, user_input: str, context: str = ''):
        with tracer.start_as_current_span('orchestrate') as span:
            span.set_attribute('type', 'chat')

            if not user_input:
                span.set_attribute('no_input', True)
                return 'chat', 'You must input something.'

            logger.info(f'user_input: {user_input}')
            span.set_attribute('user_input', user_input)

            is_question = self.question_classifier.classify(user_input)
            logger.info(f'is_question: {is_question}')
            span.set_attribute('is_question', is_question)

            if is_question:
                category = self.category_classifier.classify(user_input)
                logger.info(f'category: {category}')
                span.set_attribute('category', category)

                if category != CATEGORY_UNKNOWN:
                    query = category.lower().replace('.', '')
                    span.set_attribute('type', 'search')
                    span.set_attribute('query', query)
                    return 'search', query

            generation = self.chat_generator.generate(user_input=user_input, context=context)
            logger.info(f'generation: {generation}')
            span.set_attribute('chat generation', generation)
            return 'chat', generation