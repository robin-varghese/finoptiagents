import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent,LoopAgent,BaseAgent
from langchain_community.tools import DuckDuckGoSearchRun
import requests
import json

def delete_vm_instance(project_id: str, instance_id: str, zone: str):
    """Deletes a VM instance using the /delete_vms endpoint.

    Args:
        project_id: The Google Cloud project ID.
        instance_id: The ID of the instance to delete.
        zone: The zone where the instance is located.
        service_url: The URL of the Cloud Run service.

    Returns:
        The JSON response from the API, or None if an error occurs.
    """
    print(f" I am inside delete_vm_instances")
    headers = {'Content-Type': 'application/json'}
    data = {'instance_id': instance_id, 'project_id': project_id, 'zone': zone}
    url = f"https://agent-tools-912533822336.us-central1.run.app/delete_vms"

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error deleting instance: {e}")
        return None


def list_vm_instances(project_id: str, zone: str):
    """Lists VM instances based on domain, project ID, and zone using the /list_vms endpoint.

    Args:
        project_id: The Google Cloud project ID.
        zone: The zone where the instances are located.
        service_url: The URL of the Cloud Run service.

    Returns:
        The JSON response from the API, or None if an error occurs.
    """
    print(f" I am inside list_vm_instances 'project_id': {project_id}, 'zone': {zone}")
    headers = {'Content-Type': 'application/json'}
    data = {'project_id': project_id, 'zone': zone}
    url = f"https://agent-tools-912533822336.us-central1.run.app/list_vms"

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error listing instances: {e}")
        return None

# Create a DuckDuckGo search tool
def search_tool(query: str):
    # --- Configuration ---
    # The URL of your deployed Cloud Run service endpoint
    # Ensure it includes the specific path (/search)
    CLOUD_RUN_URL = "https://ddsearchlangcagent-qcdyf5u6mq-uc.a.run.app/search"

    # The query you want to send to the agent
    #search_query = "What are the latest developments in AI regulation in Europe?"

    # Optional: If your agent uses chat history, prepare it
    # This should match the structure expected by your format_chat_history helper
    chat_history_example = [
        {"role": "user", "content": "Tell me about large language models."},
        {"role": "assistant", "content": "Large language models are advanced AI systems..."}
    ]

    # --- Prepare the Request ---
    # This structure MUST match the Pydantic model `SearchRequest` in your FastAPI app
    payload = {
        "query": query,
        # Uncomment and include if your agent uses history:
        # "chat_history": chat_history_example
    }

    # Set the headers for sending JSON data
    headers = {
        "Content-Type": "application/json"
    }

    # --- Make the API Call ---
    print(f"Sending POST request to: {CLOUD_RUN_URL}")
    print(f"Payload: {json.dumps(payload, indent=2)}") # Log the payload being sent

    try:
        # Send the POST request
        response = requests.post(CLOUD_RUN_URL, headers=headers, json=payload, timeout=120) # Set a reasonable timeout (in seconds)

        # --- Handle the Response ---
        # Check if the request was successful (status code 2xx)
        response.raise_for_status() # This will raise an HTTPError for bad responses (4xx or 5xx)

        # Parse the JSON response from the server
        result_data = response.json() # This should match the `SearchResponse` model

        # Extract the result
        #agent_response = result_data.get("result", "No 'result' field found in response.")

        print("\n--- Agent Response ---")
        print(result_data)
        return result_data

    except requests.exceptions.Timeout:
        print(f"Error: The request to {CLOUD_RUN_URL} timed out.")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        print(f"Status Code: {response.status_code}")
        # Try to print the error detail from the server response if available
        try:
            error_detail = response.json()
            print(f"Server Error Detail: {error_detail}")
        except json.JSONDecodeError:
            print(f"Server Response (non-JSON): {response.text}")
    except requests.exceptions.RequestException as req_err:
        # Catch other potential errors like connection errors, etc.
        print(f"An error occurred during the request: {req_err}")
    except json.JSONDecodeError:
        print("Error: Failed to decode the JSON response from the server.")
        print(f"Response Text: {response.text}") # Print raw text if JSON decoding fails
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

delete_multiple_ins_loop = LoopAgent(
    name="delete_multiple_ins_loop",
    description=
    """This agent should use the delete_vm_instance and run it in loop to delete multiple VMs
            tool: delete_vm_instance(project_id, instance_id, zone).
            Either agent or the end user can call this loop agent.
            Agent can provide the entire list of VMs in List of Json
            User can provide the necessay info in text format and agent can send it to the tool as a List of Json
            can all this loopagent to delete the multiple VMs in a Google project
            Delete the compute instances and return the status in a json format
            """,
    
    )

root_agent = Agent(
    name="finops_optimization_agent",
    model="gemini-2.0-flash",
    description=(
        """Agent is provided with tools to search the Google compute instances running in Google cloud. 
        This is an API list_vm_instances(project_id, zone). 
        When user instructs, delete them using the api call which is provided as an tool delete_vm_instance(project_id, instance_id, zone).
        Any other question related to finops can be searched using the tool search_tool"""
    ),
    instruction=(
        """You are a helpful agent who can answer user questions about cloud finops. 
        Also, when given instructons by user, you can take actions on the cloud. 
        for eg: list the Google compte engines which are running in cloud. 
        Delete the compute instances and return the status in a json format """
        
    ),
    tools=[delete_vm_instance, list_vm_instances, search_tool],
    sub_agents=[delete_multiple_ins_loop]
)

