from __future__ import annotations

import time

import openai

from autogpt.config import Config

import requests
import json

from urllib.parse import quote

config = Config()

openai.api_key = config.openai_api_key
u_cookie = config.u_cookie


class GPT4Model:
    def __init__(self):
        self.url = "https://chatgpt-4-bing-ai-chat-api.p.rapidapi.com/chatgpt-4-bing-ai-chat-api/0.2/async-send-message/"
        self.headers = {
            "content-type": "application/x-www-form-urlencoded",
            "X-RapidAPI-Key": f"{config.rapid_api_key}",
            "X-RapidAPI-Host": "chatgpt-4-bing-ai-chat-api.p.rapidapi.com"
        }

    def create_chat_completion(self, messages: list, temperature: float = config.temperature,
                               max_tokens: int | None = None,
                               command: str | None = None) -> str:
        first_dict = messages[0]
        second_dict = messages[1]

        y = json.loads(json.dumps(first_dict))
        z = y["content"]
        splits = z.split('\n')
        cool_text = splits[0] + splits[1]
        cool_text = quote(cool_text)
        if command is None:
            another_cool_text = " You should only respond in JSON format as described below Response Format: { 'thoughts': { 'text': 'thought', 'reasoning': 'reasoning', 'plan': '- short bulleted - list that conveys - long-term plan', 'criticism': 'constructive self-criticism', 'speak': 'thoughts summary to say to user' }, 'command': { 'name': 'command name', 'args': { 'arg name': 'value' } } } Ensure the response can be parsed by Python json.loads"
            another_cool_text = quote(another_cool_text)
            payload = f"bing_u_cookie={u_cookie}&question=" + cool_text + another_cool_text

        payload = f"bing_u_cookie={u_cookie}&question=" + cool_text
        response = requests.request("POST", self.url, data=payload, headers=self.headers)
        response = response.text
        response = json.loads(response)
        request_id = response["request_id"]
        print("Request id: " + request_id)

        url = "https://chatgpt-4-bing-ai-chat-api.p.rapidapi.com/chatgpt-4-bing-ai-chat-api/0.2/async-get-response/"
        payload = f"request_id={request_id}"
        while True:
            response = requests.request("POST", url, data=payload, headers=self.headers)
            response = json.loads(response.text)
            if not response.has_key("status"):
                print(response)
                raise RuntimeError(f"Failed to process response")
            if response["status"] != "RUNNING":
                break
            time.sleep(3)

        response = response["data"]

        response = json.dumps(response)
        if response.find("'messages'") != -1:
            response = response.replace("'messages'", "\"messages\"")
        if response.find("'text_response'") != -1:
            response = response.replace("'text_response'", "\"text_response\"")
        if response.find("'sources'") != -1:
            response = response.replace("'sources'", "\"sources\"")
        if response.find("'suggested_queries'") != -1:
            response = response.replace("'suggested_queries'", "\"suggested_queries\"")
        if response.find("\n") != -1:
            response = response.replace("\n", "")
        json_response = json.loads(response)
        json_response = json_response["text_response"]
        json_response = json.dumps(json_response)
        if response.find("```json") != -1:
            json_response = json_response.replace("```json", "")
        if response.find("```") != -1:
            json_response = json_response.replace("```", "")
        json_response = json.loads(json_response)
        json_response = json.loads(json_response)
        return json.dumps(json_response)
