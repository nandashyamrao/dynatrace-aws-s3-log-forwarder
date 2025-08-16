import requests
import json
import time

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

# Parameters for the request, including the page size
params = {
    "pageSize": 50
}

all_dashboards = []
next_page_key = None
request_count = 0

print("Starting to fetch all dashboards...")

try:
    while True:
        request_count += 1
        # If a next_page_key exists, add it to the request parameters
        if next_page_key:
            params["nextPageKey"] = next_page_key
        else:
            # If it's the first request, remove the key just in case
            params.pop("nextPageKey", None)

        # Make the GET request to the Dynatrace API
        response = requests.get(DASHBOARDS_API_URL, headers=headers, params=params)

        # Check for HTTP errors
        response.raise_for_status()

        # Parse the JSON response
        dashboards_data = response.json()

        # Add the dashboards from the current page to the main list
        current_dashboards = dashboards_data.get("dashboards", [])
        all_dashboards.extend(current_dashboards)

        # Check for a nextPageKey to see if there are more results
        next_page_key = dashboards_data.get("nextPageKey")

        print(f"  - Fetched {len(current_dashboards)} dashboards. Total so far: {len(all_dashboards)}")

        # Break the loop if there's no next page
        if not next_page_key:
            print("Finished pagination. No more dashboards to fetch.")
            break

        # Optional: Add a small delay between requests to avoid hitting rate limits
        time.sleep(1)

    print("\n--- Summary ---")
    print(f"Total dashboards fetched: {len(all_dashboards)}")
    print(f"Total API requests made: {request_count}")

except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
    print(f"Response content: {response.text}")
except Exception as err:
    print(f"An error occurred: {err}")

# You can now process the 'all_dashboards' list, for example, by saving it to a file
if all_dashboards:
    with open("all_dynatrace_dashboards.json", "w") as f:
        json.dump(all_dashboards, f, indent=4)
    print("All dashboards saved to all_dynatrace_dashboards.json")
