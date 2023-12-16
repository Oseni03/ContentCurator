"""
run:
python -m relevancy run_all_results \
  --output_dir ./data \
  --model_name="gpt-3.5-turbo-16k" \
"""
import time
import json
import os
import random
import re
import string
from datetime import datetime

import numpy as np
import tqdm
import utils


def encode_prompt(query, prompt_results):
    """Encode multiple prompt instructions into a single string."""
    prompt = open("relevancy_prompt.txt").read() + "\n"
    prompt += query['topic']

    for idx, task_dict in enumerate(prompt_results):
        (title, keywords, site_name) = task_dict["title"], task_dict["keywords"], task_dict["site_name"]
        if not title:
            raise
        prompt += f"###\n"
        prompt += f"{idx + 1}. Title: {title}\n"
        prompt += f"{idx + 1}. keywords: {keywords}\n"
        prompt += f"{idx + 1}. site name: {site_name}\n"
    prompt += f"\n Generate response:\n1."
    print(prompt)
    return prompt


def post_process_chat_gpt_response(paper_data, response, threshold_score=8):
    selected_data = []
    if response is None:
        return []
    json_items = response['message']['content'].replace("\n\n", "\n").split("\n")
    pattern = r"^\d+\. |\\"
    import pprint
    try:
        score_items = [
            json.loads(re.sub(pattern, "", line))
            for line in json_items if "relevancy score" in line.lower()]
    except Exception:
        pprint.pprint([re.sub(pattern, "", line) for line in json_items if "relevancy score" in line.lower()])
        raise RuntimeError("failed")
    pprint.pprint(score_items)
    scores = []
    for item in score_items:
        temp = item["Relevancy score"]
        if isinstance(temp, str) and "/" in temp:
            scores.append(int(temp.split("/")[0]))
        else:
            scores.append(int(temp))
    if len(score_items) != len(paper_data):
        score_items = score_items[:len(paper_data)]
        hallucination = True
    else:
        hallucination = False

    for idx, inst in enumerate(score_items):
        # if the decoding stops due to length, the last example is likely truncated so we discard it
        if scores[idx] < threshold_score:
            continue
        output_str = "Title: " + paper_data[idx]["title"] + "\n"
        output_str += "keywords: " + paper_data[idx]["keywords"] + "\n"
        output_str += "Link: " + paper_data[idx]["link"] + "\n"
        for key, value in inst.items():
            paper_data[idx][key] = value
            output_str += str(key) + ": " + str(value) + "\n"
        paper_data[idx]['summarized_text'] = output_str
        selected_data.append(paper_data[idx])
    return selected_data, hallucination


def find_word_in_string(w, s):
    return re.compile(r"\b({0})\b".format(w), flags=re.IGNORECASE).search(s)


def process_subject_fields(keywords):
    all_keywords = keywords.split(";")
    all_keywords = [s.split(" (")[0] for s in all_keywords]
    return all_keywords

def generate_relevance_score(
    results,
    query,
    model_name="gpt-3.5-turbo-16k",
    threshold_score=8,
    num_result_in_prompt=4,
    temperature=0.4,
    top_p=1.0,
    sorting=True
):
    ans_data = []
    request_idx = 1
    hallucination = False
    for id in tqdm.tqdm(range(0, len(results), num_result_in_prompt)):
        prompt_results = results[id:id+num_result_in_prompt]
        # only sampling from the seed tasks
        prompt = encode_prompt(query, prompt_results)

        decoding_args = utils.OpenAIDecodingArguments(
            temperature=temperature,
            n=1,
            max_tokens=128*num_result_in_prompt, # The response for each paper should be less than 128 tokens. 
            top_p=top_p,
        )
        request_start = time.time()
        response = utils.openai_completion(
            prompts=prompt,
            model_name=model_name,
            batch_size=1,
            decoding_args=decoding_args,
            logit_bias={"100257": -100},  # prevent the <|endoftext|> from being generated
        )
        print ("response", response['message']['content'])
        request_duration = time.time() - request_start

        process_start = time.time()
        batch_data, hallu = post_process_chat_gpt_response(prompt_results, response, threshold_score=threshold_score)
        hallucination = hallucination or hallu
        ans_data.extend(batch_data)

        print(f"Request {request_idx+1} took {request_duration:.2f}s")
        print(f"Post-processing took {time.time() - process_start:.2f}s")

    if sorting:
        ans_data = sorted(ans_data, key=lambda x: int(x["Relevancy score"]), reverse=True)
    
    return ans_data, hallucination

def run_all_results(
    query={"topic":"", "keywords":["Computation and Language", "Artificial Intelligence"]},
    date=None,
    results=[],
    model_name="gpt-3.5-turbo-16k",
    threshold_score=8,
    num_result_in_prompt=10,
    temperature=0.4,
    top_p=1.0
):
    if date is None:
        date = datetime.today().strftime('%a, %d %b %y')
        # string format such as Wed, 10 May 23
    print ("the date for the search data is: ", date)

    all_results_in_keywords = [
        t for t in results
        if bool(set(process_subject_fields(t['keywords'])) & set(query['keywords']))
    ]
    print(f"After filtering keywords, we have {len(all_results_in_keywords)} search results left.")
    ans_data = generate_relevance_score(all_results_in_keywords, query, model_name, threshold_score, num_result_in_prompt, temperature, top_p)
    utils.write_ans_to_file(ans_data, date, output_dir="../outputs")
    return ans_data


if __name__ == "__main__":
    query = {"topic":"future of Artificial Intelligence",
    "keywords":["Computation and Language"]}
    ans_data = run_all_results(query)