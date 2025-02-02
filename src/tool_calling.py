import json
import jsonschema
import requests
import yaml
import dotenv
import os

import call_model


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


def extract_tool_info(json_tool_call, target_api):
    if not isinstance(json_tool_call, dict) or "tool_calls" not in json_tool_call:
        print("Invalid JSON structure: Missing 'tool_calls'")
        return []

    tool_calls = json_tool_call.get("tool_calls", [])
    print("TOOL CALLS:", tool_calls)
    filtered_tools = [tool for tool in tool_calls if tool.get("api") == target_api]

    return filtered_tools


def google_search_api(search_json, yaml_config_path):
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
        "key": google_search_api_key,
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


def semantic_scholar_bulk_api(search_json, yaml_config_path):
    """
    Calls the Semantic Scholar Bulk Search API to retrieve a large batch of basic paper data.
    This function omits any pagination token and uses config defaults that can be overridden by the JSON input.
    
    Supported parameters:
      - query: text query with boolean logic (overwrites config if provided)
      - year: publication year or range (overwrites config if provided)
      - publicationTypes: comma-separated list of publication types (overwrites config if provided)
      - openAccessPdf: boolean/string flag for open access papers (overwrites config if provided)
      - minCitationCount: minimum number of citations (overwrites config if provided)
      - publicationDateOrYear: date or year range (overwrites config if provided)
      - venue: comma-separated list of publication venues (overwrites config if provided)
      - fields: comma-separated list of fields to return (default: "paperId,title")
      - sort: sorting field and order (default: "paperId:asc")
    """
    # Load config from YAML
    with open(yaml_config_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    
    bulk_config = config.get("semantic_scholar_bulk", {})

    # Merge parameters: JSON parameters override config defaults.
    parameters = search_json.get("parameters", {})
    query = parameters.get("query", bulk_config.get("query"))
    year = parameters.get("year", bulk_config.get("year"))
    publicationTypes = parameters.get("publicationTypes", bulk_config.get("publicationTypes"))
    openAccessPdf = parameters.get("openAccessPdf", bulk_config.get("openAccessPdf"))
    minCitationCount = parameters.get("minCitationCount", bulk_config.get("minCitationCount"))
    publicationDateOrYear = parameters.get("publicationDateOrYear", bulk_config.get("publicationDateOrYear"))
    venue = parameters.get("venue", bulk_config.get("venue"))
    fields = parameters.get("fields", bulk_config.get("fields", "paperId,title"))
    sort = parameters.get("sort", bulk_config.get("sort", "paperId:asc"))

    # Build parameters dictionary (note: no pagination token)
    params = {
        "query": query,
        "fields": fields,
        "sort": sort,
        "year": year,
        "publicationTypes": publicationTypes,
        "openAccessPdf": openAccessPdf,
        "minCitationCount": minCitationCount,
        "publicationDateOrYear": publicationDateOrYear,
        "venue": venue
    }
    # Remove any parameters that are None or empty
    params = {k: v for k, v in params.items() if v is not None and v != ""}
    
    print("Semantic Scholar Bulk Params:", params)
    
    endpoint = bulk_config.get("endpoint", "https://api.semanticscholar.org/graph/v1/paper/search/bulk")
    try:
        response = requests.get(endpoint, params=params)
        response.raise_for_status()
        print("SS RES:", response.json())
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Semantic Scholar Bulk API: {e}")
        return {"error": str(e)}


def route_calls(response_tool_call):
    json_tool_call = extract_json_from_response(response_tool_call)

    if json_tool_call is None:
        return {"error": "Model response contains invalid JSON"}

    if not validate_json(json_tool_call):
        return {"error": "Invalid JSON schema"}

    tool_calls = json_tool_call.get("tool_calls", [])
    api_names = [call.get("api") for call in tool_calls if call.get("api")]

    print("API Names:", api_names)

    # Call the appropriate API based on the extracted API names
    responses = []

    if "google_search" in api_names:
        google_search_json = extract_tool_info(json_tool_call, "google_search")
        google_search_response = google_search_api(google_search_json[0], "../config.yaml")
        responses.append(google_search_response)

    if "semantic_scholar_bulk" in api_names:
        bulk_json = extract_tool_info(json_tool_call, "semantic_scholar_bulk")
        bulk_response = semantic_scholar_bulk_api(bulk_json[0], "../config.yaml")
        responses.append(bulk_response)

    return responses
