from flask import Flask, request, jsonify


import langchain
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

import os
from dotenv import load_dotenv
import yaml, json

app =Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status":"OK"})

@app.route('/query', methods=['POST'])
def handle_query():
    data = request.get_json()
    if not data or "query" not in data:
        return jsonify({"error": "Invalid request, 'query' is required"}), 400

    user_query = data["query"]

    response = process_query(user_query)
    return jsonify(response)

def process_query(query):

    #Read from config
    def load_config(config_path="config.yaml"):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    config = load_config()

    intended_provider = config["model_provider"]
    intended_model = config["model"]

    #Get system prompts
    with open("../prompts/routing_sys_prompt_v1.txt", "r") as f:
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
    try:
        response_json = json.loads(response.content)
        print(json.dumps(response_json, indent=4))

        tool_response_json = tool_calls(response_json)

    except:
        return {"error": "Model response contains invalid JSON"}

    return tool_response_json


#Tool Calls
def tool_calls(response_json):
     
    return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)