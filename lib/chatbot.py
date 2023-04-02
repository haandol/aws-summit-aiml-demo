import torch
from transformers import LlamaForCausalLM, LlamaTokenizer

PROMPT_DICT = {
    "prompt_input": (
        "Below is an instruction that describes a task, paired with an input that provides further context.\n"
        "아래는 작업을 설명하는 명령어와 추가적 맥락을 제공하는 입력이 짝을 이루는 예제입니다.\n\n"
        "Write a response that appropriately completes the request.\n요청을 적절히 완료하는 응답을 작성하세요.\n\n"
        "### Instruction(명령어):\n{instruction}\n\n### Input(입력):\n{context}\n\n### Response(응답):"
    ),
    "prompt_no_input": (
        "Below is an instruction that describes a task.\n"
        "아래는 작업을 설명하는 명령어입니다.\n\n"
        "Write a response that appropriately completes the request.\n명령어에 따른 요청을 적절히 완료하는 응답을 작성하세요.\n\n"
        "### Instruction(명령어):\n{instruction}\n\n### Response(응답):"
    ),
}


def setup_model(model_name: str, cache_dir: str = None):
    tokenizer = LlamaTokenizer.from_pretrained(
        model_name,
        cache_dir=cache_dir
    )
    model = LlamaForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        load_in_8bit=True,
        device_map='auto',
        cache_dir=cache_dir,
    )
    return tokenizer, model


def generate(
    tokenizer: LlamaTokenizer,
    model: LlamaForCausalLM,
    prompt: str,
    context: str = None,
    max_new_tokens: int = 128,
    temperature: float = 0.5
):
    if context:
        x = PROMPT_DICT['prompt_input'].format(instruction=prompt, context=context)
    else:
        x = PROMPT_DICT['prompt_no_input'].format(instruction=prompt)
    
    input_ids = tokenizer.encode(x, return_tensors="pt").to(model.device)
    gen_tokens = model.generate(
        input_ids, 
        max_new_tokens=max_new_tokens, 
        num_return_sequences=1, 
        temperature=temperature,
        no_repeat_ngram_size=6,
        do_sample=True,
    )
    return tokenizer.decode(gen_tokens[0], skip_special_tokens=True)[len(x):]


if __name__ == '__main__':
    cache_dir='/home/ec2-user/SageMaker/.cache'
    model_name = 'beomi/KoAlpaca'
    tokenizer, model = setup_model(model_name, cache_dir)

    prompt = "Python으로 uptime을 찾는 코드"
    generation = generate(tokenizer, model, prompt)
    print(generation)