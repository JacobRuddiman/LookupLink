from flask import Flask, request, jsonify


import langchain
from langchain.schema import HumanMessage, SystemMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

import os
from dotenv import load_dotenv
import yaml, json

import tool_calling
import call_model

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

    routing_response = tool_calling.route_calls(query)
    
    tool_responses = tool_calling.route_calls(routing_response) 

    return tool_responses


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)