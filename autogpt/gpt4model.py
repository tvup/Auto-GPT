from __future__ import annotations

import time

import openai

from autogpt.config import Config

import requests
import json

from urllib.parse import quote

CFG = Config()

openai.api_key = CFG.openai_api_key
ucookie = CFG.u_cookie

class GPT4Model:
    def __init__(self):
        self.url = "https://chatgpt-4-bing-ai-chat-api.p.rapidapi.com/chatgpt-4-bing-ai-chat-api/0.2/async-send-message/"
        self.headers = {
            "content-type": "application/x-www-form-urlencoded",
            "X-RapidAPI-Key": f"{CFG.rapid_api_key}",
            "X-RapidAPI-Host": "chatgpt-4-bing-ai-chat-api.p.rapidapi.com"
        }

    def create_chat_completion(self, messages: list, temperature: float = CFG.temperature, max_tokens: int | None = None) -> str:
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
        anothercooltext = quote(anothercooltext)
        payload = f"bing_u_cookie={ucookie}&question=" + cooltext + anothercooltext

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
            if response["status"] != "RUNNING":
                break
            time.sleep(3)

        response = response["data"]

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