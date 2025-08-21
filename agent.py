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
import vertexai  

import vertexai.agent_engines

import requests
import json
import datetime
import time
import os
import uuid # For generating unique IDs or for user_id if not available elsewhere
from toolbox_core import ToolboxClient
from .test_pg_vector_openai import generate_combined_embedding
import asyncio # <-- Add this import

#from toolbox_langchain import ToolboxClient

load_dotenv()

# Initialize Vertex AI SDK - This is crucial for ReasoningEngine to work
if os.getenv("GOOGLE_PROJECT_ID") and os.getenv("GOOGLE_ZONE"):
    # Reasoning Engines are regional, so we extract the region from the zone
    # e.g., 'us-central1-a' -> 'us-central1'
    google_region = "-".join(os.getenv("GOOGLE_ZONE").split("-")[:-1])
    vertexai.init(
        project=os.getenv("GOOGLE_PROJECT_ID"), location=google_region
    )
    print(f"Vertex AI initialized for project '{os.getenv('GOOGLE_PROJECT_ID')}' in region '{google_region}'")
else:
    print("Skipping Vertex AI initialization. GOOGLE_PROJECT_ID and/or GOOGLE_ZONE not set in .env file.")

GOOGLE_PROJECT_ID=os.getenv("GOOGLE_PROJECT_ID")
GOOGLE_ZONE=os.getenv("GOOGLE_ZONE")
GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")
GOOGLE_GENAI_USE_VERTEXAI=os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
REMOTE_CPU_AGENT_RESOURCE_NAME=os.getenv("REMOTE_CPU_AGENT_RESOURCE_NAME")

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

# Define at module scope so they are accessible in callbacks
my_tools = None
useraction_insert_mcptool = None

#load the MCP based toolset
# This will load all tools
# --- MODIFIED: ToolboxClient Setup ---

client = ToolboxClient(os.getenv("MCP_TOOLBOX_URL"))
# Define global variables to hold the loaded tools
my_tools = None
useraction_insert_mcptool = None


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

# Add this new helper function
# In your local orchestrator's agent.py file
# In your local orchestrator's agent.py file
def _get_streamed_response_sync(query: str, resource_name: str) -> str:
    """
    A synchronous helper that calls the agent and correctly parses the
    streaming response dictionaries to build the final response string.
    """
    print("Executing synchronous stream_query call in a new thread...")
    try:
        remote_agent = vertexai.agent_engines.get(resource_name)
        stream = remote_agent.stream_query(
            message=query,
            user_id="local-orchestrator-agent"
        )
        
        response_parts = []
        
        # Use a regular 'for' loop
        for event in stream:
            print(f"Received stream event: {event}")

            # --- FINAL FIX: Correctly parse the 'content' dictionary ---
            # Check if the 'content' key exists and is a dictionary
            if isinstance(event.get("content"), dict):
                content = event["content"]
                # Check if 'parts' exists and is a list
                if isinstance(content.get("parts"), list):
                    for part in content["parts"]:
                        # Check if the part is a dictionary and has a 'text' key
                        if isinstance(part, dict) and "text" in part:
                            text_chunk = part["text"]
                            if text_chunk:
                                print(f"Extracted text chunk: {text_chunk}")
                                response_parts.append(text_chunk)
        
        final_response = "".join(response_parts).strip()
        
        # Check if we actually got a response before returning
        if not final_response:
             print("WARNING: No text parts found in any event from the stream.")
             return "No text response could be parsed from the remote agent's stream."
        
        return final_response

    except Exception as e:
        print(f"Error inside synchronous stream helper: {e}")
        import traceback
        traceback.print_exc()
        return f"Error during synchronous stream call: {str(e)}"
# This is the new, correct implementation that mimics your working notebook
# This tool remains an 'async def'
async def call_cpu_utilization_agent(project_id: str, zone: str) -> str:
    """
    Asynchronously calls the remote Agent Engine agent by running the
    synchronous stream iteration in a separate thread.
    """
    print(f"--> [Local Agent Tool] Calling remote agent via asyncio.to_thread")
    if not REMOTE_CPU_AGENT_RESOURCE_NAME:
        return "Error: REMOTE_CPU_AGENT_RESOURCE_NAME is not set in the environment."
        
    try:
        query = f"What is the CPU utilization for all VMs in project {project_id} and zone {zone}?"
        
        # Run the synchronous helper function in a separate thread
        final_response = await asyncio.to_thread(
            _get_streamed_response_sync,
            query,
            REMOTE_CPU_AGENT_RESOURCE_NAME
        )
        
        print(f"<-- [Remote Agent Final Response] {final_response}")
        return final_response

    except Exception as e:
        print(f"Error in async tool 'call_cpu_utilization_agent': {e}")
        return f"An unexpected error occurred in the async tool wrapper: {str(e)}"

# { ... your existing tools like delete_vm_instance, list_vm_instances, etc. ... }
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
    
#*************************START: Call Back ***************************************
# (Global initializations for client/my_tools, USER_ID, LOGGING_TOOL_NAME, generate_combined_embedding remain)
# Ensure 'client' is your initialized ToolboxClient instance, not 'my_tools' for calling methods.
# I've changed 'my_tools' back to 'client' in the logging check and call_tool.

# Ensure 'toolbox_client' is defined and initialized at the module level as previously discussed
# For example:
# try:
#     toolbox_client = ToolboxClient(os.getenv("MCP_TOOLBOX_URL"))
#     toolbox_client.load_toolset(os.getenv("TOOLSET_NAME_FOR_LOGGING", "my_googleaiagent_toolset"))
#     print("ToolboxClient initialized and toolset loaded.")
# except Exception as e:
#     print(f"CRITICAL: Failed to initialize ToolboxClient: {e}")
#     toolbox_client = None


# Find this function in your code and replace it completely with the following:

def log_interaction_after_model(
    callback_context: CallbackContext,
    llm_response: LlmResponse
) -> None:
    """
    Logs the LLM response. On the first run, it will load the async toolset.
    """
    global my_tools, useraction_insert_mcptool
    print("[Callback] After model call triggered.")

    # --- NEW LAZY-LOADING LOGIC ---
    # Check if the tools have been loaded. If not, load them now.
    if my_tools is None:
        print("[Callback] First run: Loading MCP toolset asynchronously...")
        try:
            # Use asyncio.run() to execute and wait for the async function
            # from this synchronous context.
            loaded_tools = asyncio.run(client.load_toolset(os.getenv("TOOLSET_NAME_FOR_LOGGING")))
            
            # This check is important because toolbox-core might return None on failure
            if loaded_tools:
                my_tools = loaded_tools
                useraction_insert_mcptool = os.getenv("LOGGING_TOOL_NAME")
                print(f"[Callback] MCP toolset loaded successfully: {my_tools}")
            else:
                # Use a sentinel value to indicate failure and prevent retries
                print("[Callback] MCP toolset loading returned None. Disabling logging.")
                my_tools = "FAILED_TO_LOAD" 
        except Exception as e:
            print(f"[Callback] CRITICAL ERROR loading MCP toolset: {e}")
            my_tools = "FAILED_TO_LOAD" # Mark as failed to prevent retrying every time
    
    # If loading failed or hasn't succeeded, skip the rest of the function.
    if not my_tools or my_tools == "FAILED_TO_LOAD" or not useraction_insert_mcptool:
        print("[Callback] MCP Toolset not available. Skipping logging.")
        return

    # --- Your original logging logic can now proceed safely ---
    try:
        user_id_to_log = USER_ID
        session_id_to_log = "unknown_session"
        if hasattr(callback_context, 'invocation_context') and hasattr(callback_context.invocation_context, 'session_id'):
            session_id_to_log = callback_context.invocation_context.session_id

        # ... (Your logic to prepare action_json_string, result_json_string, vector_string) ...
        # (This is just a placeholder for your actual logic which seems correct)
        action_json_string = json.dumps({"agent": callback_context.agent_name})
        result_json_string = json.dumps({"response": "..."})
        vector_list = generate_combined_embedding(user_id_to_log, action_json_string, result_json_string)
        vector_string = str(vector_list)

        tool_params = {
            "user_id": user_id_to_log,
            "action": action_json_string,
            "result": result_json_string,
            "vector_value": vector_string
        }
        
        py_tool_name = useraction_insert_mcptool.replace("-", "_")
        tool_to_call = getattr(my_tools, py_tool_name)
        
        # NOTE: If tool_to_call is ALSO async, you would need asyncio.run here too.
        # Assuming it is a synchronous method on the loaded toolset object.
        response = tool_to_call(**tool_params)
        print(f"[Callback] MCP tool call response: {response}")

    except AttributeError:
        py_tool_name = useraction_insert_mcptool.replace("-", "_")
        print(f"[Callback] Error: Tool '{py_tool_name}' not found in the loaded toolset object.")
    except Exception as e:
        print(f"[Callback] Error during logging execution: {e}")
        import traceback
        traceback.print_exc()


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
# Find your root_agent definition
# In your agent.py file, find the root_agent definition and replace it.

root_agent = LlmAgent(
    name="finops_optimization_agent",
    model="gemini-2.0-flash", # Or your preferred model
    description=(
        """Agent for Google Cloud finops tasks. Can list, delete, and check CPU utilization of VMs. 
        It can also perform multi-step operations like deleting VMs based on their CPU usage."""
    ),
    instruction=(
        """You are an advanced Google Cloud finops assistant. You can answer questions and execute tasks by calling tools.

        **Core Capabilities:**
        - Greet the user with the `greeting_agent`.
        - List running VMs using the `list_vm_instances` tool.
        - Delete a single VM using the `delete_vm_instance` tool.
        - Delete multiple VMs using the `delete_multiple_ins_loop_agent`.
        - Check CPU usage for all VMs in a zone using the `call_cpu_utilization_agent` tool.
        - Answer general finops questions using the `search_tool`.

        **IMPORTANT REASONING PROCESS for Deletion by CPU Utilization:**
        When a user asks you to delete VMs based on a condition like "CPU utilization below 30%", you MUST follow this multi-step process:

        1.  **Step 1: Gather Data.** You DO NOT have a tool to directly filter VMs by CPU. Your first action MUST be to call the `call_cpu_utilization_agent` tool with the correct `project_id` and `zone` to get the list of all VMs and their current CPU usage.

        2.  **Step 2: Analyze and Plan.** After you get the text output from `call_cpu_utilization_agent`, you must carefully read it. Parse the text to identify the `Instance ID` of every VM that meets the user's criteria (e.g., CPU percentage is less than 30). Create a list of these target Instance IDs. If no VMs meet the criteria, inform the user and stop.

        3.  **Step 3: Execute Deletion.** Based on the list of Instance IDs you created in Step 2:
            - If your list contains EXACTLY ONE `Instance ID`, your next action is to call the `delete_vm_instance` tool for that single instance.
            - If your list contains MORE THAN ONE `Instance ID`, your next action is to call the `delete_multiple_ins_loop_agent` sub-agent. When calling the loop agent, you must provide the necessary information for all target VMs.

        4.  **Step 4: Report to User.** After the deletion tools have finished, provide a clear summary of which VMs were deleted to the user.
        """
    ),
    tools=[
        delete_vm_instance, 
        list_vm_instances, 
        search_tool, 
        call_cpu_utilization_agent
    ],
    sub_agents=[delete_multiple_ins_loop_agent, greeting_agent],
    # Your callbacks remain the same
    before_model_callback=simple_before_model_modifier,
    after_model_callback=log_interaction_after_model
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
