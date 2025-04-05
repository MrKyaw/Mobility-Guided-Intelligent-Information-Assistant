
"""
Mobility-Guided-Intelligent-Assistant - Utility File

Authors			    :	Kyaw Kyaw Oo
Emails              :   ook1@mcmaster.ca
Student No          :   400551761
Group No			:   Sixth Smart Sense Generation<br>
Started Date        :   Jan 28, 2025<br>
Version             :   1<br>
Released Date    	: 	<br>>
Version             :   2 <br>

CopyRight@2024 by Sixth Smart Sense Generation<br>
"""
# Loading basic libraries
import os
import requests
import json
from io import BytesIO

# loading visual libraries
import matplotlib.pyplot as plt
from PIL import Image
from dotenv import load_dotenv, find_dotenv

def load_env():
    _ = load_dotenv(find_dotenv())

  # The right API to pass in a prompt (of type string) is the completions API https://docs.together.ai/reference/completions-1
  # The right API to pass in a messages (of type of list of message) is The chat completions API https://docs.together.ai/reference/chat-completions-1

def llama32(messages, model_size=11):
  model = f"meta-llama/Llama-3.2-{model_size}B-Vision-Instruct-Turbo"
  url = f"{os.getenv('DLAI_TOGETHER_API_BASE', 'https://api.together.xyz')}/v1/chat/completions"
  print(url)

  payload = {
    "model": model,
    "max_tokens": 4096,
    "temperature": 0.0,
    "stop": ["<|eot_id|>","<|eom_id|>"],
    "messages": messages
  }

  headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('TOGETHER_API_KEY')}"
  }
  res = json.loads(requests.request("POST", url, headers=headers, data=json.dumps(payload)).content)

  if 'error' in res:
    raise Exception(res['error'])

  return res['choices'][0]['message']['content']

def get_tavily_api_key():
    load_env()
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    return tavily_api_key

def disp_image(address):
    if address.startswith("http://") or address.startswith("https://"):
        response = requests.get(address)
        img = Image.open(BytesIO(response.content))
    else:
        img = Image.open(address)
    
    plt.imshow(img)
    plt.axis('off')
    plt.show()


