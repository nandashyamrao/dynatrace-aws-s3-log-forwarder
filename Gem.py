import requests
import json

# Replace with your actual environment URL and API token
DYNATRACE_ENV_URL = "YOUR_DYNATRACE_ENV_URL"
DYNATRACE_API_TOKEN = "YOUR_DYNATRACE_API_TOKEN"

# The API endpoint for fetching dashboards
DASHBOARDS_API_URL = f"{DYNATRACE_ENV_URL}/api/v2/dashboards"

# Headers for the API request, including the API token
headers = {
    "Authorization": f"Api-Token {DYNATRACE_API_TOKEN}",
    "Accept": "application/json"
}

try:
    # Make the GET request to the Dynatrace API
    response = requests.get(DASHBOARDS_API_URL, headers=headers)

    # Check if the request was successful
    response.raise_for_status()

    # Parse the JSON response
    dashboards_data = response.json()

    # Print the list of dashboards
    print("Successfully fetched Dynatrace dashboards:")
    for dashboard in dashboards_data.get("dashboards", []):
        print(f"  - Name: {dashboard['name']}, ID: {dashboard['id']}")

except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
except Exception as err:
    print(f"An error occurred: {err}")

