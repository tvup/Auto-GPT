from __future__ import annotations

from ast import List
import time

import openai
from openai.error import APIError, RateLimitError
from colorama import Fore

from autogpt.config import Config

import requests
import json

from urllib.parse import quote
from ast import literal_eval

CFG = Config()

openai.api_key = CFG.openai_api_key


def call_ai_function(
    function: str, args: list, description: str, model: str | None = None
) -> str:
    """Call an AI function

    This is a magic function that can do anything with no-code. See
    https://github.com/Torantulino/AI-Functions for more info.

    Args:
        function (str): The function to call
        args (list): The arguments to pass to the function
        description (str): The description of the function
        model (str, optional): The model to use. Defaults to None.

    Returns:
        str: The response from the function
    """
    if model is None:
        model = CFG.smart_llm_model
    # For each arg, if any are None, convert to "None":
    args = [str(arg) if arg is not None else "None" for arg in args]
    # parse args to comma separated string
    args = ", ".join(args)
    messages = [
        {
            "role": "system",
            "content": f"You are now the following python function: ```# {description}"
            f"\n{function}```\n\nOnly respond with your `return` value.",
        },
        {"role": "user", "content": args},
    ]

    return create_chat_completion(model=model, messages=messages, temperature=0)


# Overly simple abstraction until we create something better
# simple retry mechanism when getting a rate error or a bad gateway
def create_chat_completion(
    messages: list,  # type: ignore
    model: str | None = None,
    temperature: float = CFG.temperature,
    max_tokens: int | None = None,
) -> str:
    """Create a chat completion using the OpenAI API

    Args:
        messages (list[dict[str, str]]): The messages to send to the chat completion
        model (str, optional): The model to use. Defaults to None.
        temperature (float, optional): The temperature to use. Defaults to 0.9.
        max_tokens (int, optional): The max tokens to use. Defaults to None.

    Returns:
        str: The response from the chat completion
    """
    response = None
    num_retries = 10
    if CFG.debug_mode:
        print(
            Fore.GREEN
            + f"Creating chat completion with model {model}, temperature {temperature},"
            f" max_tokens {max_tokens}" + Fore.RESET
        )
    for attempt in range(num_retries):
        backoff = 2 ** (attempt + 2)
        try:
            if CFG.use_azure:
                response = openai.ChatCompletion.create(
                    deployment_id=CFG.get_azure_deployment_id_for_model(model),
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            else:
                if model == "gpt-4":
                    url = "https://chatgpt-4-bing-ai-chat-api.p.rapidapi.com/chatgpt-4-bing-ai-chat-api/0.2/async-send-message/"

                    første_ordbog = messages[0]
                    anden_ordbog = messages[1]
                    tredje_ordbog = messages[2]
                    fjerde_ordbog = messages[3]

                    y = json.loads(json.dumps(første_ordbog))
                    z = y["content"]
                    splits = z.split('\n')
                    cooltext = splits[0] + splits[1]
                    cooltext = quote(cooltext)
                    anothercooltext = " You should only respond in JSON format as described below Response Format: { 'thoughts': { 'text': 'thought', 'reasoning': 'reasoning', 'plan': '- short bulleted - list that conveys - long-term plan', 'criticism': 'constructive self-criticism', 'speak': 'thoughts summary to say to user' }, 'command': { 'name': 'command name', 'args': { 'arg name': 'value' } } } Ensure the response can be parsed by Python json.loads"
                    #                anothercooltext = " You should only respond in JSON format as described below Response Format: { \"thoughts\": { \"text\": \"thought\", \"reasoning\": \"reasoning\", \"plan\": \"- short bulleted\n-- list that conveys\n- long-term plan\", \"criticism\": \"constructive self-criticism\", \"speak\": \"thoughts summary to say to user\" }, \"command\": { \"name\": \"command name\", \"args\": { \"arg name\": \"value\" } } } Ensure the response can be parsed by Python json.loads"
                    anothercooltext = quote(anothercooltext)
                    payload = "bing_u_cookie=12aC2PWJcRqeE9MFHUEeXK_rmTgJbUXiiHVRmwzBQ5pQItsJGJzT_-FaSoxgHvrlk2lgVgH1YUsEh_1w5B_WcRcv7rAd76htUuUWVRWxfR3797n3WImT5RCxsaq0xz-TuAP66R1muPEjy2cspZHy8hm95UUrapTAFEfh3-mZOQciGhIQUtJ8U8xPA6M4VpmhzIyS8AWkNFq8AwjdB2U0OIiJSLZsmgg9NMAEoQy0Ns-U&question=" + cooltext + anothercooltext
                    headers = {
                        "content-type": "application/x-www-form-urlencoded",
                        "X-RapidAPI-Key": f"{CFG.rapid_api_key}",
                        "X-RapidAPI-Host": "chatgpt-4-bing-ai-chat-api.p.rapidapi.com"
                    }
                    response = requests.request("POST", url, data=payload, headers=headers)
                    response = response.text
                    response = json.loads(response)
                    request_id = response["request_id"]
                    print("Request id: " + request_id)

                    url = "https://chatgpt-4-bing-ai-chat-api.p.rapidapi.com/chatgpt-4-bing-ai-chat-api/0.2/async-get-response/"
                    payload = f"request_id={request_id}"
                    while True:
                        response = requests.request("POST", url, data=payload, headers=headers)
                        response = json.loads(response.text)
                        if response["status"] != "RUNNING":
                            break
                        time.sleep(3)

                    response = response["data"]

                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            break
        except RateLimitError:
            if CFG.debug_mode:
                print(
                    Fore.RED + "Error: ",
                    f"Reached rate limit, passing..." + Fore.RESET,
                )
        except APIError as e:
            if e.http_status == 502:
                pass
            else:
                raise
            if attempt == num_retries - 1:
                raise
        if CFG.debug_mode:
            print(
                Fore.RED + "Error: ",
                f"API Bad gateway. Waiting {backoff} seconds..." + Fore.RESET,
            )
        time.sleep(backoff)
    if response is None:
        raise RuntimeError(f"Failed to get response after {num_retries} retries")

    if model != "gpt-4":
        return response.choices[0].message["content"]

    response = json.dumps(response)
    response = response.replace("'messages'", "\"messages\"")
    response = response.replace("'text_response'", "\"text_response\"")
    response = response.replace("'sources'", "\"sources\"")
    response = response.replace("'suggested_queries'", "\"suggested_queries\"")
    response = response.replace("\n", "")
    jsonresponse = json.loads(response)
    jsonresponse = jsonresponse["text_response"]
    jsonresponse = json.dumps(jsonresponse)
    jsonresponse = jsonresponse.replace("```json", "")
    jsonresponse = jsonresponse.replace("```", "")
    jsonresponse = json.loads(jsonresponse)
    jsonresponse = json.loads(jsonresponse)
    return json.dumps(jsonresponse)


def create_embedding_with_ada(text) -> list:
    """Create a embedding with text-ada-002 using the OpenAI SDK"""
    num_retries = 10
    for attempt in range(num_retries):
        backoff = 2 ** (attempt + 2)
        try:
            if CFG.use_azure:
                return openai.Embedding.create(
                    input=[text],
                    engine=CFG.get_azure_deployment_id_for_model(
                        "text-embedding-ada-002"
                    ),
                )["data"][0]["embedding"]
            else:
                return openai.Embedding.create(
                    input=[text], model="text-embedding-ada-002"
                )["data"][0]["embedding"]
        except RateLimitError:
            pass
        except APIError as e:
            if e.http_status == 502:
                pass
            else:
                raise
            if attempt == num_retries - 1:
                raise
        if CFG.debug_mode:
            print(
                Fore.RED + "Error: ",
                f"API Bad gateway. Waiting {backoff} seconds..." + Fore.RESET,
            )
        time.sleep(backoff)
