import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, StoppingCriteria, StoppingCriteriaList
from lib.logger import logger

if torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"


class StopOnTokens(StoppingCriteria):
    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        stop_ids = [50278, 50279, 50277, 1, 0]
        for stop_id in stop_ids:
            if input_ids[0][-1] == stop_id:
                return True
        return False


def setup_model(model_name: str, cache_dir: str, load_in_8bit=False):
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        cache_dir=cache_dir
    )
    if device == "cuda":
        logger.info(f"Model loaded on GPU for device: {device}")
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            load_in_8bit=load_in_8bit,
            device_map='auto',
            cache_dir=cache_dir,
        )
    else:
        logger.info(f"Model loaded on CPU")
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
    top_p: float = 0.8,
    max_new_tokens: int = 128,
    temperature: float = 0.2,
):
    inputs = tokenizer(prompt, return_tensors='pt').to(model.device)
    with torch.no_grad():
        gen_tokens = model.generate(
            **inputs,
            labels=inputs['input_ids'],
            top_p=top_p,
            max_new_tokens=max_new_tokens, 
            temperature=temperature,
            do_sample=True,
            stopping_criteria=StoppingCriteriaList([StopOnTokens()]),
            num_return_sequences=1,
            no_repeat_ngram_size=6,
            pad_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(gen_tokens[0], skip_special_tokens=True)[len(prompt):]


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