import torch
from random import choice
from transformers import AutoModelForCausalLM, AutoTokenizer
from lib.logger import logger

if torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"


def setup_model(model_name: str, cache_dir: str, load_in_8bit=False):
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=cache_dir
    )
    if device == "cuda":
        logger.info(f"Model is loading on GPU for device: {device}")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            load_in_8bit=load_in_8bit,
            device_map='auto',
            cache_dir=cache_dir,
        )
    else:
        logger.info(f"Model is loading on CPU")
        model = AutoModelForCausalLM.from_pretrained(
            model_name, device_map={"": device},
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True,
            cache_dir=cache_dir,
        )
    model.eval()
    return tokenizer, model


def generate(
    tokenizer: AutoTokenizer,
    model: AutoModelForCausalLM,
    prompt: str,
    top_k: int = 0,
    top_p: float = 1.0,
    max_new_tokens: int = 32,
    temperature: float = 0.5,
    num_return_sequences: int = 1,
    do_sample: bool = False,
    eos_token_id: int = 2,
):
    input_ids = tokenizer.encode(prompt, return_tensors='pt').to(model.device)
    with torch.no_grad():
        gen_tokens = model.generate(
            input_ids=input_ids,
            top_k=top_k,
            top_p=top_p,
            max_new_tokens=max_new_tokens, 
            temperature=temperature,
            do_sample=do_sample,
            num_return_sequences=num_return_sequences,
            eos_token_id=eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
            no_repeat_ngram_size=6,
        )
    gen_token = choice(gen_tokens)
    return tokenizer.decode(gen_token, skip_special_tokens=True)[len(prompt):]


if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()

    model_name = os.environ['MODEL_NAME']
    cache_dir = os.environ['CACHE_DIR']
    load_in_8bit = os.environ.get('LOAD_IN_8BIT', False)
    tokenizer, model = setup_model(model_name, cache_dir, load_in_8bit=load_in_8bit)

    prompt = "입력받은 숫자가 prime number 인지 검사하는 python 코드"
    generation = generate(tokenizer, model, prompt)
    print(generation)