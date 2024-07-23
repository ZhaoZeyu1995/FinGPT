from sklearn.metrics import accuracy_score, f1_score
from pathlib import Path
import torch
import datasets
from tqdm import tqdm
from datasets import load_dataset, load_from_disk
import warnings
from math import ceil
warnings.filterwarnings("ignore")


dic = {
    'strong negative': "negative",
    'moderately negative': "negative",
    'mildly negative': "neutral",
    'strong positive': "positive",
    'moderately positive': "positive",
    'mildly positive': 'neutral',
    'neutral': 'neutral',
}


def format_example(example: dict) -> dict:
    context = f"Instruction: {example['instruction']}\n"
    if example.get("input"):
        context += f"Input: {example['input']}\n"
    context += "Answer: "
    target = example["output"]
    return {"context": context, "target": target}


def change_target(x):
    if 'positive' in x or 'Positive' in x:
        return 'positive'
    elif 'negative' in x or 'Negative' in x:
        return 'negative'
    else:
        return 'neutral'


def test_nwgi(args, model, tokenizer, prompt_fun=None):
    batch_size = args.batch_size
    # dataset = load_dataset('oliverwang15/news_with_gpt_instructions')
    dataset = load_from_disk(
        Path(__file__).parent.parent / 'data/news_with_gpt_instructions/')["test"]
    dataset = dataset.to_pandas()
    dataset['output'] = dataset['label'].apply(lambda x: dic[x])

    if prompt_fun is None:
        dataset["instruction"] = "What is the sentiment of this news? Please choose an answer from {negative/neutral/positive}."
        # dataset["instruction"] = "What is the sentiment of this news? Please choose an answer from {strong negative/moderately negative/mildly negative/neutral/mildly positive/moderately positive/strong positive}."
    else:
        dataset["instruction"] = dataset.apply(prompt_fun, axis=1)
    dataset["input"] = dataset["news"]

    dataset = dataset[['input', 'output', 'instruction']]
    dataset[["context", "target"]] = dataset.apply(
        format_example, axis=1, result_type="expand")

    # print example
    print(f"\n\nPrompt example:\n{dataset['context'][0]}\n\n")

    context = dataset['context'].tolist()

    total_steps = ceil(dataset.shape[0]/batch_size)
    print(
        f"Total len: {len(context)}. Batchsize: {batch_size}. Total steps: {total_steps}")

    def context_to_prompt(x: str):
        """
        Transform a string like

        Instruction: What is the sentiment of this tweet? Please choose an answer from {negative/neutral/positive}.
        Input: Still short $LNG from $11.70 area...next stop could be down through $9.00. Someone slammed it hard with 230,000 shs this am! More to follow
        Answer:

        to the corresponding prompt string by applying the tokenizer's chat_template
        """
        if tokenizer.chat_template is None or "system" not in tokenizer.chat_template:
            messages = [
                {
                    "role": "user",
                    "content": x,
                },
            ]
        else:
            instruction, inputs, answer = x.split("\n")
            messages = [
                {
                    "role": "system",
                    "content": instruction,
                },
                {
                    "role": "user",
                    "content": inputs + '\n' + answer,
                },
            ]
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    out_text_list = []
    for i in tqdm(range(total_steps)):
        tmp_context = context[i * batch_size:min((i+1) * batch_size, len(context))]
        if args.base_model in ["phi3mini", "phi3small", "phi3medium"]:
            tmp_prompt = [context_to_prompt(x) for x in tmp_context]
            tokens = tokenizer(tmp_prompt, return_tensors='pt', padding=True, max_length=512, return_token_type_ids=False)
        else:
            tokens = tokenizer(tmp_context, return_tensors='pt', padding=True, max_length=512, return_token_type_ids=False)
        # tokens.pop('token_type_ids')
        for k in tokens.keys():
            tokens[k] = tokens[k].cuda()
        res = model.generate(**tokens, max_new_tokens=128,
                             eos_token_id=tokenizer.eos_token_id)
        res_sentences = [tokenizer.decode(
            i, skip_special_tokens=True) for i in res]
        tqdm.write(f'{i}: {res_sentences[0]}')
        out_text = [o.split("Answer: ")[1] for o in res_sentences]
        out_text_list += out_text
        torch.cuda.empty_cache()

    dataset["out_text"] = out_text_list
    dataset["new_target"] = dataset["target"].apply(change_target)
    dataset["new_out"] = dataset["out_text"].apply(change_target)

    acc = accuracy_score(dataset["new_target"], dataset["new_out"])
    f1_macro = f1_score(dataset["new_target"],
                        dataset["new_out"], average="macro")
    f1_micro = f1_score(dataset["new_target"],
                        dataset["new_out"], average="micro")
    f1_weighted = f1_score(dataset["new_target"],
                           dataset["new_out"], average="weighted")

    print(f"Acc: {acc}. F1 macro: {f1_macro}. F1 micro: {f1_micro}. F1 weighted: {f1_weighted}. ")

    return dataset
