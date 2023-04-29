QUESTION_PROMPT = '''
Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
Classify the following sentence into 'question', or 'statement'.

### Input:
Sentence: How are you doign today?
Class: question.

Sentence: I would like to build personalized sports observer system, but what should I do?
Class: question.

Sentence: I am happy for you.
Class: statement.

Sentence: I want to create a online shop for selling cell-phones.
Class: statement.

### Response:
Sentence: {user_input}
Class:
'''.strip()

CATEGORY_PROMPT = '''
Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
Label the category towards the sentence.
Use 'Unknown' for all unknown categories.
Use the following list as only available Category. Do not make up new category other than the list.
{categories}

### Input:
Sentence: What is the easiest way to build an application on Amazon Web Services (AWS)?
Category: Unknown.

Sentence: Can you give me an advice for build a healthcare mobile application?
Category: Health.

Sentence: I want to optimize the delivery system for big super-markets, but what should I do?
Category: Retail.

### Response:
Sentence: {user_input}
Category:
'''.strip()

CHAT_PROMPT = '''
Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
The following is a conversation between a human and an AI assistant named ArchitectureWhisperer (or Archie).
The assistant is at the Convention & Exhibition Center (COEX) in Seoul, Korea for AWS SUMMIT. The assistant tone is technical and scientific.
The human and the assistant take turns chatting.
The human statements start with [|Human|] and the assistant statements start with [|SA|].

Amazon Web Services (AWS) is the world's most comprehensive and broadly adopted cloud, offering over 200 fully featured services from data centers globally. Millions of customers—including the fastest-growing startups, largest enterprises, and leading government agencies—are using AWS to lower costs, become more agile, and innovate faster.

### Input:
[|Human|]: Hi, What is your name?
[|SA|]: Hi, I am ArchitectureWhisperer. Please ask me anything about building application on Amazon Web Services (AWS).

[|Human|]: Could you list AWS Services related to AI/ML?
[|SA|]: Sure, Here are the services about Machine Learning (ML) and Artificial Intelligence (AI) on AWS. Amazon Augmented AI, Amazon CodeWhisperer, Amazon Comprehend, Amazon Forecast, Amazon Fraud Detector, Amazon Lex, Amazon Personalize, Amazon Polly, Amazon Rekognition, Amazon SageMaker, Amazon Textract, Amazon Transcribe, Amazon Translate.

[|Human|]: Could you list AWS Services related to AI/ML?
[|SA|]: Sure, Here are the services about Machine Learning (ML) and Artificial Intelligence (AI) on AWS. Amazon Augmented AI, Amazon CodeWhisperer, Amazon Comprehend, Amazon Forecast, Amazon Fraud Detector, Amazon Lex, Amazon Personalize, Amazon Polly, Amazon Rekognition, Amazon SageMaker, Amazon Textract, Amazon Transcribe, Amazon Translate.

{context}

### Response:
[|Human|]: {user_input}
[|SA|]:
'''.strip()

CATEGORY_UNKNOWN = 'Unknown'
CATEGORIES = '\n'.join([
    '- {CATEGORY_UNKNOWN}',
    # Industry Category
    '- Advertising and Marketing',
    '- Automotive',
    '- Consumer Packaged Goods',
    '- Education',
    '- Energy',
    '- Financial Services',
    '- Games',
    '- Government',
    '- Health',
    '- Industrial',
    '- Manufacturing',
    '- Media and Entertainment',
    '- Nonprofits',
    '- Power and Utilities',
    '- Retail',
    '- Semiconductor and Electronics',
    '- Sports',
    '- Telecom',
    '- Travel and Hospitality',
    # Service Category
    '- Analytics',
    '- Application Integration',
    '- AR and VR',
    '- Blockchain',
    '- Contact Center',
    '- End User Computing',
    '- Web and Mobile Services',
    '- Internet of Things (IoT)',
    '- Machine Learning (ML) and Artificial Intelligence (AI)',
    '- Management and Governance',
    '- Migration and Transfer',
    '- Networking and Content Delivery',
    '- Quantum Technologies',
    '- Robotics',
    '- Satellite',
    '- Security and Compliance',
])

PROMPT = {
    'question': QUESTION_PROMPT,
    'category': CATEGORY_PROMPT,
    'chat': CHAT_PROMPT,
}