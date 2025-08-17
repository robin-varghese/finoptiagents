from google.adk.agents import Agent, LoopAgent, BaseAgent, LlmAgent
from google.adk.sessions import DatabaseSessionService, Session
from google.adk.runners import Runner
from google.adk.events import Event, EventActions
from google.adk.sessions import VertexAiSessionService
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset  # Correct import
from pydantic import BaseModel
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
import uuid
from .test_pg_vector_openai import generate_combined_embedding

load_dotenv()

GOOGLE_PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_ZONE = os.getenv("GOOGLE_ZONE")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_GENAI_USE_VERTEXAI = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")

# --- 1. Define Constants ---
APP_NAME = "agent_comparison_app"
USER_ID = "Robin Varghese"
BASE_SESSION_ID_TOOL_AGENT = "session_tool_agent_xyz"
SESSION_ID_SCHEMA_AGENT = "session_schema_agent_xyz"
current_session_id_tool_agent = BASE_SESSION_ID_TOOL_AGENT + str(time.time())
MODEL_NAME = "gemini-2.0-flash"

# Define a minimal Pydantic model for event content
class EmptyEventContent(BaseModel):
    pass

# Initialize MCPToolset
mcp_toolset = MCPToolset(mcp_url=os.getenv("MCP_TOOLBOX_URL"))
try:
    print("Attempting to load specific toolset 'my_googleaiagent_toolset'...")
    my_tools = mcp_toolset.load_toolset(os.getenv("TOOLSET_NAME_FOR_LOGGING"))
    useraction_insert_mcptool = os.getenv("LOGGING_TOOL_NAME")
    print("Successfully loaded toolset 'my_googleaiagent_toolset':", my_tools)
    print("Tool Name for logging:", useraction_insert_mcptool)
except Exception as e:
    print(f"Error loading toolset: {e}")
    import traceback
    traceback.print_exc()

#*************************START: TOOLS Section**************************************
def delete_vm_instance(project_id: str, instance_id: str, zone: str):
    """Deletes a VM instance using the /delete_vms endpoint."""
    print(f"I am inside delete_vm_instances")
    headers = {'Content-Type': 'application/json'}
    data = {'instance_id': instance_id, 'project_id': project_id, 'zone': zone}
    url = f"https://agent-tools-912533822336.us-central1.run.app/delete_vms"
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error deleting instance: {e}")
        return None

def list_vm_instances(project_id: str, zone: str):
    """Lists VM instances based on domain, project ID, and zone using the /list_vms endpoint."""
    print(f"I am inside list_vm_instances 'project_id': {project_id}, 'zone': {zone}")
    headers = {'Content-Type': 'application/json'}
    data = {'project_id': project_id, 'zone': zone}
    url = f"https://agent-tools-912533822336.us-central1.run.app/list_vms"
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error listing instances: {e}")
        return None

def search_tool(query: str):
    """Performs a DuckDuckGo search using a Cloud Run endpoint."""
    CLOUD_RUN_URL = "https://ddsearchlangcagent-qcdyf5u6mq-uc.a.run.app/search"
    payload = {"query": query}
    headers = {"Content-Type": "application/json"}
    print(f"Sending POST request to: {CLOUD_RUN_URL}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    try:
        response = requests.post(CLOUD_RUN_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result_data = response.json()
        print("\n--- Agent Response ---")
        print(result_data)
        return result_data
    except requests.exceptions.Timeout:
        print(f"Error: The request to {CLOUD_RUN_URL} timed out.")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        try:
            error_detail = response.json()
            print(f"Server Error Detail: {error_detail}")
        except json.JSONDecodeError:
            print(f"Server Response (non-JSON): {response.text}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred during the request: {req_err}")
    except json.JSONDecodeError:
        print("Error: Failed to decode the JSON response from the server.")
        print(f"Response Text: {response.text}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

#*************************END: TOOLS Section**************************************
#*************************START: Call Back ***************************************
def simple_before_model_modifier(callback_context: CallbackContext, llm_request: LlmRequest) -> Optional[LlmResponse]:
    """Inspects/modifies the LLM request or skips the call."""
    agent_name = callback_context.agent_name
    print(f"[Callback] Before model call for agent: {agent_name}")
    last_user_message = ""
    if llm_request.contents:
        for content_item in reversed(llm_request.contents):
            if content_item.role == 'user' and content_item.parts:
                if content_item.parts[0].text is not None:
                    last_user_message = content_item.parts[0].text
                    break
    print(f"[Callback] Inspecting last user message: '{last_user_message}'")
    original_instruction = llm_request.config.system_instruction or types.Content(role="system", parts=[])
    if not isinstance(original_instruction, types.Content):
        original_instruction = types.Content(role="system", parts=[types.Part(text=str(original_instruction))])
    if not original_instruction.parts:
        original_instruction.parts.append(types.Part(text=""))
    modified_text = "[Modified by Callback] " + (original_instruction.parts[0].text or "")
    original_instruction.parts[0].text = modified_text
    llm_request.config.system_instruction = original_instruction
    print(f"[Callback] Modified system instruction to: '{modified_text}'")
    if "BLOCK" in last_user_message.upper():
        print("[Callback] 'BLOCK' keyword found. Skipping LLM call.")
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part(text="LLM call was blocked by before_model_callback.")]
            )
        )
    else:
        print("[Callback] Proceeding with LLM call.")
        return None

def log_interaction_after_model(callback_context: CallbackContext, llm_response: LlmResponse) -> None:
    """Logs the LLM response and available context."""
    print("[Callback] After model call triggered.")
    if not mcp_toolset:
        print("[Callback] MCPToolset not initialized. Skipping logging.")
        return
    actual_logging_tool_name = os.getenv("LOGGING_TOOL_NAME", "insert-user-action-and-result")
    if not actual_logging_tool_name:
        print("[Callback] LOGGING_TOOL_NAME not set. Skipping logging.")
        return
    try:
        user_id_to_log = USER_ID
        session_id_to_log = "unknown_session"
        if hasattr(callback_context, 'invocation_context') and \
           hasattr(callback_context.invocation_context, 'session_id'):
            session_id_to_log = callback_context.invocation_context.session_id
        elif hasattr(callback_context, 'session_id'):
            session_id_to_log = callback_context.session_id
        else:
            print(f"[Callback] WARN: Could not determine session_id from CallbackContext. Attributes: {dir(callback_context)}")
        action_details = {
            "prompt_context": f"LLM response generated for agent {callback_context.agent_name}",
            "timestamp": datetime.datetime.now().isoformat(),
            "agent_name": callback_context.agent_name,
            "invocation_id": callback_context.invocation_id,
            "session_id": session_id_to_log,
            "interaction_id": str(uuid.uuid4())
        }
        action_json_string = json.dumps(action_details)
        llm_result_text = "No text response from LLM."
        llm_function_call_details = None
        if llm_response.content and llm_response.content.parts:
            text_parts = [part.text for part in llm_response.content.parts if part.text]
            if text_parts:
                llm_result_text = " ".join(text_parts).strip()
            for part in llm_response.content.parts:
                if part.function_call:
                    args_for_json = part.function_call.args
                    if hasattr(args_for_json, 'items'):
                        args_for_json = dict(args_for_json.items())
                    llm_function_call_details = {"name": part.function_call.name, "args": args_for_json}
                    break
        result_details = {
            "response_text": llm_result_text,
            "function_call": llm_function_call_details,
            "llm_response_id": llm_response.id if hasattr(llm_response, 'id') else str(uuid.uuid4())
        }
        result_json_string = json.dumps(result_details)
        text_for_embedding1_action_context = f"Agent {callback_context.agent_name} responded in session {session_id_to_log} (invocation {callback_context.invocation_id})."
        text_for_embedding2_result = llm_result_text
        if llm_function_call_details:
            text_for_embedding2_result += f" (Function Call: {llm_function_call_details['name']})"
        vector_list = generate_combined_embedding(user_id_to_log, text_for_embedding1_action_context, text_for_embedding2_result)
        vector_string = "[" + ",".join(map(str, vector_list)) + "]"
        tool_params = {
            "user_id": user_id_to_log,
            "action": action_json_string,
            "result": result_json_string,
            "vector_value": vector_string
        }
        print(f"[Callback] Calling MCP tool '{actual_logging_tool_name}' with params: {json.dumps(tool_params, indent=2)}")
        response = mcp_toolset.call_tool(
            tool_name=actual_logging_tool_name,
            tool_input=tool_params
        )
        print(f"[Callback] MCP tool call response: {response}")
    except Exception as e:
        print(f"[Callback] Error during after_model_callback logging: {e}")
        import traceback
        traceback.print_exc()

#**************************END: Call Back *****************************************
#*************************START: Agents Section**************************************
greeting_agent = LlmAgent(
    name="Greeter",
    description="This agent should greet the user when logged-in",
    model="gemini-2.0-flash",
    instruction="Generate a short, friendly greeting.",
    output_key="last_greeting"
)

delete_vm_instance_agent = Agent(
    name="delete_vm_instance_agent",
    description="This agent should use the delete_vm_instance tool",
    tools=[delete_vm_instance],
    before_model_callback=simple_before_model_modifier
)

delete_multiple_ins_loop_agent = LoopAgent(
    name="delete_multiple_ins_loop_agent",
    description="""This agent should use the delete_vm_instance and run it in loop to delete multiple VMs
            tool: delete_vm_instance(project_id, instance_id, zone).
            Either agent or the end user can call this loop agent.
            Agent can provide the entire list of VMs in List of Json
            User can provide the necessary info in text format and agent can send it to the tool as a List of Json
            can call this loopagent to delete the multiple VMs in a Google project
            Delete the compute instances and return the status in a json format""",
    sub_agents=[delete_vm_instance_agent],
    max_iterations=10
)

root_agent = LlmAgent(
    name="finops_optimization_agent",
    model="gemini-2.0-flash",
    description="""Agent is provided with tools to search the Google compute instances running in Google cloud.
        This is an API list_vm_instances(project_id, zone).
        When user instructs, delete them using the api call which is provided as an tool delete_vm_instance(project_id, instance_id, zone).
        Any other question related to finops can be searched using the tool search_tool""",
    instruction="""You are a helpful agent who can answer user questions about cloud finops.
        When user logs-in greet the user with the tool greeting_agent.
        Also, when given instructions by user, you can take actions on the cloud.
        for eg: list the Google compute engines which are running in cloud.
        Use the tool to delete the compute instances and return the status in a json format.
        This agent should use the delete_multiple_ins_loop sub agent to delete multiple VMs in a loop""",
    tools=[delete_vm_instance, list_vm_instances, search_tool],
    sub_agents=[delete_multiple_ins_loop_agent, greeting_agent],
    before_model_callback=simple_before_model_modifier,
    after_model_callback=log_interaction_after_model
)
#*************************END: Agents Section**************************************
#*************************START: Agent Common Section**************************************
Initial_state = {
    "user_name": "Robin Varghese",
    "user_preferences": """
        I like to address the organizational finops challenges in the best and efficient way.
        I use Google cloud services for my work and I usually suggest Google services to my customers.
        My LinkedIn profile can be found at https://www.linkedin.com/in/robinkoikkara/
        """
}

# Create a new session
db_url = "sqlite:///./my_agent_data.db"
session_service = DatabaseSessionService(db_url=db_url)
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
    "task_status": "active",
    "user:login_count": session.state.get("user:login_count", 0) + 1,
    "user:last_login_ts": current_time,
    "temp:validation_needed": True
}

# --- Create Event with Actions ---
actions_with_update = EventActions(state_delta=state_changes)
system_event = Event(
    invocation_id="inv_login_update",
    author="system",
    actions=actions_with_update,
    timestamp=current_time,
    content=EmptyEventContent()
)

# --- Append the Event ---
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
#*************************END: Agent Common Section**************************************