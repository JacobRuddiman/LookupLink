import json
import jsonschema
import requests
import yaml
import dotenv

import call_model
import os


def extract_json_from_response(response_text):
    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1

        if start != -1 and end != -1:
            json_string = response_text[start:end]
            return json.loads(json_string)
        else:
            raise ValueError("No valid JSON array found in the response.")

    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error extracting JSON: {e}")
        return None


def validate_json(json_tool_call):
    with open("../json/routing_schema.json", "r") as file:
        schema = json.load(file)

    try:
        jsonschema.validate(instance=json_tool_call, schema=schema)
        return True

    except jsonschema.ValidationError as e:
        print(f"Validation error: {e}")
        return False


def route_calls(response_tool_call):
    json_tool_call = extract_json_from_response(response_tool_call)

    if json_tool_call is None:
        return {"error": "Model response contains invalid JSON"}

    if not validate_json(json_tool_call):
        return {"error": "Invalid JSON schema"}

    tool_calls = json_tool_call.get("tool_calls", [])
    api_names = []

    for call in tool_calls:
        api_name = call.get("api")
        if api_name:
            api_names.append(api_name)

    print("API Names:", api_names)

    # Call the appropriate API based on the extracted API names
    responses = []

    if "google_search" in api_names:
        google_search_json = extract_tool_info(json_tool_call, "google_search")
        google_search_response = google_search_api(google_search_json[0], "../config.yaml")
        responses.append(google_search_response)
    return responses




def extract_tool_info(json_tool_call, target_api):
    if not isinstance(json_tool_call, dict) or "tool_calls" not in json_tool_call:
        print("Invalid JSON structure: Missing 'tool_calls'")
        return []

    tool_calls = json_tool_call.get("tool_calls", [])
    print("TOOL CALLS:", tool_calls)
    filtered_tools = [tool for tool in tool_calls if tool.get("api") == target_api]

    return filtered_tools

def  google_search_api(search_json, yaml_config_path):
    # Load config from YAML
    with open(yaml_config_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)

    # Extract static parameters from YAML
    safe = config.get("safe", "off")  # Default to "off" if not defined
    cx = config.get("cx")  # Custom search engine ID (must be in the YAML file)

    if not cx:
        raise ValueError("The 'cx' parameter (custom search engine ID) is missing in the YAML configuration.")

    print("SEARCH_JSON:", search_json)
    # Extract dynamic parameters from JSON
    query = search_json.get("parameters", {}).get("query")  
    num = search_json.get("parameters", {}).get("num", 10)  # Default to 10 if not provided

    # Ensure valid range for 'num'
    if not (1 <= num <= 10):
        num = 10

    dotenv.load_dotenv()

    if "GOOGLE_SEARCH_KEY" not in os.environ:
        raise ValueError("The 'GOOGLE_SEARCH_KEY' environment variable is not set.")
    
    google_search_api_key = os.environ["GOOGLE_SEARCH_KEY"]


    # Prepare request parameters
    params = {
        "q": query,
        "num": num,
        "safe": safe,
        "key": google_search_api_key,  # API key from YAML
        "cx": cx
    }

    print("PARAMS:", params)


    # Remove any parameters that are None
    params = {k: v for k, v in params.items() if v is not None}

    # Call the API
    try:
        base_url = "https://www.googleapis.com/customsearch/v1"
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Google Search API: {e}")
        return {"error": str(e)}