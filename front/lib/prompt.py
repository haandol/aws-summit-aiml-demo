QUESTION_PROMPT = '''
Classify the following sentence into 'question', or 'statement'.

Sentence: I would like to build personalized sports observer system, but what should I do?
Answer: question.

Sentence: I want to create a online shop for selling cell-phones.
Answer: statement.

Sentence: {user_input}
'''.strip()

CATEGORY_PROMPT = '''
Please label the category towards the sentence.
Use 'Unknown' for all unknown categories.
Use the following list as only available Category. Do not make up new category other than the list.
- Unknown
- Advertising and Marketing
- Automotive
- Consumer Packaged Goods
- Education
- Energy
- Financial Services
- Games
- Government
- Health
- Industrial
- Manufacturing
- Media and Entertainment
- Nonprofits
- Power and Utilities
- Retail
- Semiconductor and Electronics
- Sports
- Telecom
- Travel and Hospitality

Sentence: What is the easiest way to build an application on Amazon Web Services (AWS)?
Category: Unknown.

Sentence: I want to optimize the delivery system for big super-markets, but what should I do?
Category: Retail.

Sentence: {user_input}
'''.strip()

CHAT_PROMPT = '''
The following is a conversation between a human and an AI assistant named ArchitectureWhisperer.
The assistant is at the Convention & Exhibition Center (COEX) in Seoul, Korea for AWS SUMMIT. The assistant tone is technical and scientific.
The human and the assistant take turns chatting.
The human statements start with [|Human|] and the assistant statements start with [|SA|].

Amazon Web Services (AWS) is the world's most comprehensive and broadly adopted cloud, offering over 200 fully featured services from data centers globally. Millions of customers—including the fastest-growing startups, largest enterprises, and leading government agencies—are using AWS to lower costs, become more agile, and innovate faster.

[|SA|]: Hi, I am ArchitectureWhisperer. Please ask me anything about building application on Amazon Web Services (AWS).

{context}

[|Human|]: {user_input}
'''.strip()

PROMPT = {
    'question': QUESTION_PROMPT,
    'category': CATEGORY_PROMPT,
    'chat': CHAT_PROMPT,
}