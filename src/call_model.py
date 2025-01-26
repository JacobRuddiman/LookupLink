import langchain
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

import os
from dotenv import load_dotenv
import yaml, json

#Read from config
def call_model(query, system_prompt_file):

    def load_config(config_path="../config.yaml"):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    config = load_config()

    intended_provider = config["model_provider"]
    intended_model = config["model"]

    #Get system prompts
    with open(system_prompt_file, "r") as f:
        routing_sys_prompt = f.read()


    #Model selection
    if(str(intended_provider).lower() == "openai"):
        load_dotenv()

        if not os.environ.get("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is not set. Add it to your .env file.")

        openai_api_key = os.environ["OPENAI_API_KEY"]

        model = ChatOpenAI(openai_api_key=openai_api_key, model_name=intended_model)

    elif(str(intended_provider).lower() == "anthropic"):
        load_dotenv()

        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise ValueError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

        anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]

        model = ChatAnthropic(anthropic_api_key=anthropic_api_key, model_name=intended_model)


    #Call model 
    system_prompt = SystemMessage(content=routing_sys_prompt)
    user_prompt = HumanMessage(content=query)

    conversation = [system_prompt, user_prompt]

    response = model.invoke(conversation)
    if(response.content == None):
        return {"error": "No response from model"}
    print("RESPONSE=======\n", response.content, "\n========")
    return response.content