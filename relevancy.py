import json
import re
import utils
import tqdm
from datetime import datetime


# Function to encode prompt instructions
def encode_prompt(topic, search_results, num_result_in_prompt):
    """Encode multiple prompt instructions into a single string."""
    prompt = f"Relevance score calculation for the topic: {topic}\n\n"

    for idx, result in enumerate(search_results):
        title = result.get("title", "")
        summary = result.get("summary", "")
        id = result.get("id", "")

        prompt += f"###\n"
        prompt += f"{idx + 1}. Title: {title}\n"
        prompt += f"{idx + 1}. Summary: {summary}\n"
        prompt += f"{idx + 1}. Id: {id}\n"

    prompt += f"\nGenerate response for relevance scores:\n1."
    return prompt


# Function to process GPT-3 response and generate relevance scores
def generate_relevance_scores(
    topic,
    search_results,
    model_name,
    threshold_score,
    num_result_in_prompt,
    temperature,
):
    ans_data = []
    for idx in tqdm.tqdm(range(0, len(search_results), num_result_in_prompt)):
        batch_results = search_results[idx : idx + num_result_in_prompt]
        prompt = encode_prompt(topic, batch_results, num_result_in_prompt)

        decoding_args = utils.OpenAIDecodingArguments(
            temperature=temperature,
            n=1,
            max_tokens=128
            * num_result_in_prompt,  # Response for each paper should be less than 128 tokens
            top_p=1.0,
        )

        response = utils.openai_completion(
            prompts=prompt,
            model_name=model_name,
            batch_size=1,
            decoding_args=decoding_args,
            logit_bias={"100257": -100},  # Prevent the token from being generated
        )

        batch_data = post_process_gpt_response(batch_results, response, threshold_score)
        ans_data.extend(batch_data)

    ans_data = sorted(ans_data, key=lambda x: int(x["Relevancy score"]), reverse=True)
    return ans_data


# Function to post-process GPT-3 response and filter results based on threshold score
def post_process_gpt_response(search_results, response, threshold_score):
    selected_data = []
    if response is None:
        return []

    json_items = response["message"]["content"].replace("\n\n", "\n").split("\n")
    pattern = r"^\d+\. |\\"

    score_items = [
        json.loads(re.sub(pattern, "", line))
        for line in json_items
        if "relevancy score" in line.lower()
    ]

    scores = []
    for item in score_items:
        temp = item.get("Relevancy score")
        if isinstance(temp, str) and "/" in temp:
            scores.append(int(temp.split("/")[0]))
        else:
            scores.append(int(temp))

    for idx, inst in enumerate(score_items):
        if scores[idx] < threshold_score:
            continue

        output_str = "Title: " + search_results[idx].get("title", "") + "\n"
        output_str += "Summary: " + search_results[idx].get("summary", "") + "\n"
        output_str += "Id: " + search_results[idx].get("id", "") + "\n"

        for key, value in inst.items():
            search_results[idx][key] = value
            output_str += str(key) + ": " + str(value) + "\n"

        search_results[idx]["summarized_text"] = output_str
        selected_data.append(search_results[idx])

    return selected_data


# Function to run relevance score generation for search results
def run_relevance_scoring(
    topic,
    search_results,
    model_name="gpt-3.5-turbo-16k",
    threshold_score=8,
    num_result_in_prompt=4,
    temperature=0.4,
):
    """
    Run relevance scoring for search results based on the specified topic.

    Parameters:
    - topic: The specific topic for relevance scoring (e.g., "Machine Learning").
    - search_results: List of dictionaries containing search results.
    - model_name: Name of the GPT model to use for scoring (default: "gpt-3.5-turbo-16k").
    - threshold_score: The minimum score for relevance (default: 8).
    - num_result_in_prompt: Number of results to include in each prompt (default: 4).
    - temperature: Temperature parameter for generating responses (default: 0.4).

    Returns:
    - ans_data: List of dictionaries containing the scored and processed search results.
    """
    date = datetime.today().strftime("%a, %d %b %y")
    print("Date for the search data is:", date)

    print(f"Total search results: {len(search_results)}")
    ans_data = generate_relevance_scores(
        topic,
        search_results,
        model_name,
        threshold_score,
        num_result_in_prompt,
        temperature,
    )

    # Write the results to an output file or perform further processing
    # Example: utils.write_ans_to_file(ans_data, date, output_dir="../outputs")

    return ans_data


# Example usage:
if __name__ == "__main__":
    # Sample search results (list of dictionaries)
    search_results = [
        {
            "id": "1546743444",
            "title": "Title 1",
            "summary": "summary of the ...",
        },
        {
            "id": "762456758",
            "title": "Title 2",
            "summary": "summary of the ...",
        },
        # Add more search result dictionaries here...
    ]

    # Define parameters
    topic = "Machine Learning"
    model_name = "gpt-3.5-turbo-16k"
    threshold_score = 8
    num_result_in_prompt = 4
    temperature = 0.5

    # Run relevance scoring for search results
    relevance_scores = run_relevance_scoring(
        topic,
        search_results,
        model_name,
        threshold_score,
        num_result_in_prompt,
        temperature,
    )
