from google.adk.agents import Agent,LoopAgent,BaseAgent,LlmAgent
from google.adk.sessions import DatabaseSessionService, Session
from google.adk.runners import Runner
from google.adk.events import Event, EventActions
from google.adk.sessions import VertexAiSessionService
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest

from pydantic import BaseModel # Or from wherever ADK makes it accessible
from typing import Optional
from google.genai import types 
from langchain_community.tools import DuckDuckGoSearchRun
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import requests
import json
import datetime
import time
import os


load_dotenv()

GOOGLE_PROJECT_ID=os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_ZONE=os.getenv("GOOGLE_ZONE")
GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")
GOOGLE_GENAI_USE_VERTEXAI=os.getenv("GOOGLE_GENAI_USE_VERTEXAI")


# --- 1. Define Constants ---
APP_NAME = "agent_comparison_app"
USER_ID = "Robin Varghese"
BASE_SESSION_ID_TOOL_AGENT = "session_tool_agent_xyz"
SESSION_ID_SCHEMA_AGENT = "session_schema_agent_xyz"
current_session_id_tool_agent = BASE_SESSION_ID_TOOL_AGENT + str(time.time())
MODEL_NAME = "gemini-2.0-flash"

# Define a minimal Pydantic model for event content if no specific fields are needed
class EmptyEventContent(BaseModel):
    pass


#*************************START: TOOLS Section**************************************

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

#*************************END: TOOLS Section**************************************
#*************************START: Call BAck ***************************************
def simple_before_model_modifier(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM request or skips the call."""
    agent_name = callback_context.agent_name
    print(f"[Callback] Before model call for agent: {agent_name}")

    # Inspect the last user message in the request contents
    last_user_message = ""
    if llm_request.contents:
        last_content_item = llm_request.contents[-1]
        if last_content_item.role == 'user' and last_content_item.parts:
            # Ensure the text part exists and is not None, otherwise keep empty string
            if last_content_item.parts[0].text is not None:
                last_user_message = last_content_item.parts[0].text
            # else: last_user_message_text remains ""

    print(f"[Callback] Inspecting last user message: '{last_user_message}'")

    # --- Modification Example ---
    # Add a prefix to the system instruction
    original_instruction = llm_request.config.system_instruction or types.Content(role="system", parts=[])
    prefix = "[Modified by Callback] "
    # Ensure system_instruction is Content and parts list exists
    if not isinstance(original_instruction, types.Content):
         # Handle case where it might be a string (though config expects Content)
         original_instruction = types.Content(role="system", parts=[types.Part(text=str(original_instruction))])
    if not original_instruction.parts:
        original_instruction.parts.append(types.Part(text="")) # Add an empty part if none exist

    # Modify the text of the first part
    modified_text = prefix + (original_instruction.parts[0].text or "")
    original_instruction.parts[0].text = modified_text
    llm_request.config.system_instruction = original_instruction
    print(f"[Callback] Modified system instruction to: '{modified_text}'")

    # --- Skip Example ---
    # Check if the last user message contains "BLOCK"
    if "BLOCK" in last_user_message.upper():
        print("[Callback] 'BLOCK' keyword found. Skipping LLM call.")
        # Return an LlmResponse to skip the actual LLM call
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="LLM call was blocked by before_model_callback.")],
            )
        )
    else:
        print("[Callback] Proceeding with LLM call.")
        # Return None to allow the (modified) request to go to the LLM
        return None
#**************************END: Call Back *****************************************
#*************************START: Agents Section**************************************
# Create a runner for EACH agent
greeting_agent = LlmAgent(
    name="Greeter",
    description=
    """This agent should greet the user when logged-in""",
    model="gemini-2.0-flash", # Use a valid model
    instruction="Generate a short, friendly greeting.",
    output_key="last_greeting"
)

delete_vm_instance_agent = Agent(
    name="delete_vm_instance_agent",
    description=
    """This agent should use the delete_vm_instance tool""",
    tools=[delete_vm_instance],
    before_model_callback=simple_before_model_modifier # Assign the function here
    )

delete_multiple_ins_loop_agent = LoopAgent(
    name="delete_multiple_ins_loop_agent",
    description=
    """This agent should use the delete_vm_instance and run it in loop to delete multiple VMs
            tool: delete_vm_instance(project_id, instance_id, zone).
            Either agent or the end user can call this loop agent.
            Agent can provide the entire list of VMs in List of Json
            User can provide the necessay info in text format and agent can send it to the tool as a List of Json
            can all this loopagent to delete the multiple VMs in a Google project
            Delete the compute instances and return the status in a json format
            """,
    sub_agents=[delete_vm_instance_agent],
    #TODO change max_iterations to variable instead of fixed value
    max_iterations=10
    )


root_agent = LlmAgent(
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
        When user logs-in greet the user with the tool greeting_agent.
        Also, when given instructons by user, you can take actions on the cloud. 
        for eg: list the Google compte engines which are running in cloud. 
        Use the tool to delete the compute instances and return the status in a json format.
        This agent should use the delete_multiple_ins_loop sub agent to delete multiple VMs in a loop
        """
    ),
    tools=[delete_vm_instance, list_vm_instances, search_tool],
    sub_agents=[delete_multiple_ins_loop_agent,greeting_agent],
    before_model_callback=simple_before_model_modifier # Assign the function here
)
#*************************END: Agents Section**************************************
#*************************START: Agent Common Section**************************************

Initial_state = {
    "user_name": "Robin Varghese",
    "user_preferences": """
        I like to adress the organizational finops challenges is the best and efficient way.
        I use Google cloud services for my work and I usually suggest Google services to my customers.
        My LinkedIn profile can be found at https://www.linkedin.com/in/robinkoikkara/
        """
}

#Create A New Session

# Example using a local SQLite file:
db_url = "sqlite:///./my_agent_data.db"
session_service = DatabaseSessionService(db_url=db_url)
# Use REASONING_ENGINE_APP_NAME when calling service methods, e.g.:
# session_service.create_session(app_name=REASONING_ENGINE_APP_NAME, ...)



capital_runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service
)
session = session_service.create_session(
    app_name=APP_NAME,
    user_id=USER_ID,
    session_id=current_session_id_tool_agent,
    state={"user:login_count": 0, "task_status": "idle"}
)

print(f"Initial state for session {current_session_id_tool_agent}: {session.state}")

# --- Define State Changes ---
current_time = time.time()
state_changes = {
    "task_status": "active",              # Update session state
    "user:login_count": session.state.get("user:login_count", 0) + 1, # Update user state
    "user:last_login_ts": current_time,   # Add user state
    "temp:validation_needed": True        # Add temporary state (will be discarded)
}

# --- Create Event with Actions ---
actions_with_update = EventActions(state_delta=state_changes)

# This event might represent an internal system action, not just an agent response
system_event = Event(
    invocation_id="inv_login_update",
    author="system", # Or 'agent', 'tool' etc.
    actions=actions_with_update,
    timestamp=current_time,
    content=EmptyEventContent()  # <--- ADD THIS LINE
    # content might be None or represent the action taken
)

# --- Append the Event (This updates the state) ---
session_service.append_event(session, system_event)
print("`append_event` called with explicit state delta.")

# --- Check Updated State ---
updated_session = session_service.get_session(app_name=APP_NAME,
                                            user_id=USER_ID, 
                                            session_id=current_session_id_tool_agent)

if updated_session:
    print(f"State after event for session {current_session_id_tool_agent}: {updated_session.state}")
else:
    print(f"Could not retrieve session with ID: {current_session_id_tool_agent}")

# Expected: {'user:login_count': 1, 'task_status': 'active', 'user:last_login_ts': <timestamp>}
# Note: 'temp:validation_needed' is NOT present.
#*************************End: Agent Common Section**************************************