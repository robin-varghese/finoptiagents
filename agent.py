import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
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
    headers = {'Content-Type': 'application/json'}
    data = {'instance_id': instance_id, 'project_id': project_id, 'zone': zone}
    url = f"https://list-vms-qcdyf5u6mq-uc.a.run.app/delete_vms"

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error deleting instance: {e}")
        return None


def list_vm_instances(domain: str, project_id: str, zone: str):
    """Lists VM instances based on domain, project ID, and zone using the /list_vms endpoint.

    Args:
        domain: The domain to filter instances by.
        project_id: The Google Cloud project ID.
        zone: The zone where the instances are located.
        service_url: The URL of the Cloud Run service.

    Returns:
        The JSON response from the API, or None if an error occurs.
    """
    headers = {'Content-Type': 'application/json'}
    data = {'domain': domain, 'project_id': project_id, 'zone': zone}
    url = f"https://list-vms-qcdyf5u6mq-uc.a.run.app/list_vms"

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error listing instances: {e}")
        return None

# Create a DuckDuckGo search tool
def search_tool(query: str):

    search = DuckDuckGoSearchRun(output_format="json")
    search_result = search.invoke(str)
    print(f"Search Result: {search_result}")

root_agent = Agent(
    name="finops_optimization_agent",
    model="gemini-2.0-flash",
    description=(
        "Agent is provided with tools to search the Google compute instances running in Google cloud and delete them when user is requested"
    ),
    instruction=(
        "You are a helpful agent who can answer user questions about cloud finops. Also, when given instructons by user, you can take actions on the cloud. for eg: list the Google compte engines which are running in cloud. Delete the compte instances "
    ),
    tools=[delete_vm_instance, list_vm_instances, search_tool],
)

