import streamlit as st
import asyncio
import time
import os
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient, AzureOpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

# Conditional import for Azure Cosmos DB
STORE_RUN_RESULT = os.getenv('STORE_RUN_RESULT', '').lower() == 'true'
if STORE_RUN_RESULT:
    from azure.cosmos import CosmosClient
    from azure.identity import DefaultAzureCredential

load_dotenv()

def get_cosmos_client():
    """Initialize and return Azure Cosmos DB client if enabled."""
    if not STORE_RUN_RESULT:
        return None
    
    endpoint = os.getenv('COSMOS_ENDPOINT')
    database_name = os.getenv('COSMOS_DATABASE', 'magentic_one_results')
    container_name = os.getenv('COSMOS_CONTAINER', 'run_results')
    
    if not endpoint:
        st.error("Cosmos DB endpoint must be set in COSMOS_ENDPOINT environment variable")
        return None
    
    try:
        # Use Azure Identity for authentication
        credential = DefaultAzureCredential()
        client = CosmosClient(endpoint, credential)
        database = client.get_database_client(database_name)
        container = database.get_container_client(container_name)
        return container
    except Exception as e:
        st.error(f"Failed to connect to Cosmos DB: {e}")
        return None

def store_run_result(run_id: str, prompt: str, results: list, model_name: str, use_aoai: bool, elapsed_time: float, prompt_tokens: int, completion_tokens: int):
    """Store run result in Azure Cosmos DB."""
    if not STORE_RUN_RESULT:
        return
    
    container = get_cosmos_client()
    if not container:
        return
    
    # Convert results to serializable format
    serialized_results = []
    for chunk in results:
        if chunk is None:
            continue
        if hasattr(chunk, '__class__'):
            chunk_data = {
                'type': chunk.__class__.__name__,
                'source': getattr(chunk, 'source', None),
                'content': None,
                'timestamp': datetime.now().isoformat()
            }
            
            if chunk.__class__.__name__ == 'TaskResult':
                # Store task completion info
                chunk_data['content'] = f"Task completed in {elapsed_time:.2f} seconds"
            elif hasattr(chunk, 'type') and chunk.type == 'MultiModalMessage':
                # Store image data
                chunk_data['content'] = {
                    'type': 'image',
                    'image_data': chunk.content[1].to_base64() if len(chunk.content) > 1 else None
                }
            elif hasattr(chunk, 'content'):
                # Store text content
                chunk_data['content'] = str(chunk.content)
            
            serialized_results.append(chunk_data)
    
    document = {
        'id': run_id,
        'prompt': prompt,
        'model_name': model_name,
        'use_azure_openai': use_aoai,
        'elapsed_time': elapsed_time,
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'results': serialized_results,
        'created_at': datetime.now().isoformat()
    }
    
    try:
        container.create_item(document)
        st.success(f"Run result stored with ID: {run_id}")
    except Exception as e:
        st.error(f"Failed to store run result: {e}")

def load_run_result(run_id: str):
    """Load run result from Azure Cosmos DB."""
    if not STORE_RUN_RESULT:
        return None
    
    container = get_cosmos_client()
    if not container:
        return None
    
    try:
        document = container.read_item(item=run_id, partition_key=run_id)
        return document
    except Exception as e:
        st.error(f"Failed to load run result: {e}")
        return None

def display_stored_result(document):
    """Display a stored run result from Cosmos DB."""
    st.title('🧠🤖 Magentic-One Demo - Stored Result')
    
    st.write(f"**Run ID:** {document['id']}")
    st.write(f"**Original Prompt:** {document['prompt']}")
    st.write(f"**Model:** {document['model_name']}")
    st.write(f"**Azure OpenAI:** {'Yes' if document['use_azure_openai'] else 'No'}")
    st.write(f"**Created At:** {document['created_at']}")
    st.write(f"**Elapsed Time:** {document['elapsed_time']:.2f} seconds")
    st.write(f"**Prompt Tokens:** {document['prompt_tokens']}")
    st.write(f"**Completion Tokens:** {document['completion_tokens']}")
    
    st.write("---")
    st.write("**Execution Results:**")
    
    for result in document['results']:
        if result['source']:
            st.write(f"**{format_source_display(result['source'])}**")
        
        if isinstance(result['content'], dict) and result['content'].get('type') == 'image':
            # Display image
            image_data = result['content']['image_data']
            if image_data:
                image = f'data:image/png;base64,{image_data}'
                st.image(image)
        elif result['content'] and isinstance(result['content'], str):
            # Display text content
            st.markdown(result['content'])

def format_source_display(source):
    """
    Converts a source identifier into a user-friendly display string with an appropriate emoji.
    
    Args:
        source (str): The message source identifier
        
    Returns:
        str: Formatted string with emoji representing the source
    """
    if source == "user":
        return "👤 User"
    elif source == "MagenticOneOrchestrator":
        return "🤖 MagenticOneOrchestrator"
    elif source == "WebSurfer":
        return "🌐 WebSurfer"
    elif source == "FileSurfer":
        return "📁 FileSurfer"
    elif source == "Coder":
        return "💻 Coder"
    else:
        return f"💻 Terminal"

async def run_task(user_prompt: str, USE_AOAI, model_name=None):
    """
    Executes a task with the given user prompt using either Azure OpenAI or OpenAI.
    Streams and displays results in the Streamlit UI as they become available.
    
    Args:
        user_prompt (str): The task prompt from the user
        USE_AOAI (bool): Whether to use Azure OpenAI API
        
    Yields:
        Various message chunks and task results
    """
    start_time = time.time()
    if(USE_AOAI):
        client = AzureOpenAIChatCompletionClient(
            azure_endpoint=os.getenv('AZURE_OPEN_AI_ENDPOINT'),
            model=model_name,
            api_version="2024-12-01-preview",
            api_key=os.getenv('AZURE_OPEN_AI_KEY')
        )
    else:
        client = OpenAIChatCompletionClient(
            model=model_name,
            api_key=os.getenv('OPEN_AI_API_KEY')
        )

    m1 = MagenticOne(client=client, code_executor=LocalCommandLineCodeExecutor())
    async for chunk in m1.run_stream(task=user_prompt):
        if chunk.__class__.__name__ != 'TaskResult':
            st.write(f"**{format_source_display(chunk.source)}**")
            if chunk.type == 'MultiModalMessage':
                image = 'data:image/png;base64,' + chunk.content[1].to_base64()
                st.image(image)
            else:
                st.markdown(chunk.content)
        else:
            st.write(f"**Task completed in {(time.time() - start_time):.2f} s.**")
        yield chunk
    yield None, time.time() - start_time

async def collect_results(user_prompt: str, USE_AOAI, model_name=None, run_id=None):
    """
    Collects all results from run_task and accumulates token usage statistics.
    Updates session state with token counts and optionally stores in Cosmos DB.
    
    Args:
        user_prompt (str): The task prompt from the user
        USE_AOAI (bool): Whether to use Azure OpenAI API
        model_name (str): Model name to use
        run_id (str): Optional run ID for storing results
        
    Returns:
        list: Collection of all result chunks
    """
    results = []
    prompt_tokens = 0
    completion_tokens = 0
    
    async for chunk in run_task(user_prompt, USE_AOAI, model_name):
        results.append(chunk)
    
    for result in results:
        if result is not None and result.__class__.__name__ == 'TaskResult':
            print(result)
            for message in result.messages:
                if message.source != "user":
                    if message.models_usage:
                        prompt_tokens += message.models_usage.prompt_tokens
                        completion_tokens += message.models_usage.completion_tokens
    
    # Update session state
    st.session_state.prompt_token = prompt_tokens
    st.session_state.completion_token = completion_tokens
    
    # Store in Cosmos DB if enabled and run_id provided
    if STORE_RUN_RESULT and run_id:
        elapsed_time = results[-1][1] if results[-1] is not None else 0
        store_run_result(
            run_id=run_id,
            prompt=user_prompt,
            results=results[:-1],  # Exclude the timing tuple
            model_name=model_name,
            use_aoai=USE_AOAI,
            elapsed_time=elapsed_time,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        )
    
    return results

def main():
    # Check for run_id in URL parameters
    query_params = st.query_params
    run_id = query_params.get('run_id', None)
    
    if run_id and STORE_RUN_RESULT:
        # Display stored result
        stored_result = load_run_result(run_id)
        if stored_result:
            display_stored_result(stored_result)
            return
        else:
            st.error(f"Run with ID {run_id} not found")
            st.write("Continuing to main interface...")
    
    st.title('🧠🤖 Magentic-One Demo')
    st.write('Implementation using Autogen and Streamlit')
    
    if STORE_RUN_RESULT:
        st.info("💾 Run result storage is enabled - results will be saved to Azure Cosmos DB")

    st.sidebar.title('Settings')
    USE_AOAI = st.sidebar.checkbox("Use Azure OpenAI", value=True)

    if(USE_AOAI):
        aoai_model_options = ["gpt-4.1","gpt-4o", "gpt-4.1-mini","gpt-4o-mini", "o3-mini"]
        selected_model = st.sidebar.selectbox("Select Model", aoai_model_options)
    else:
        selected_model = st.sidebar.text_input("Enter OpenAI Model", value="gpt-4o", placeholder="e.g., gpt-4o, gpt-3.5-turbo")

    if 'output' not in st.session_state:
        st.session_state.output = None
        st.session_state.elapsed = None
        st.session_state.prompt_token = 0
        st.session_state.completion_token = 0

    prompt = st.text_input('What is the task today?', value='')

    if st.button('Execute'):
        # Generate a new run ID
        new_run_id = str(uuid.uuid4())
        st.write(f"**Task is submitted with {selected_model} model.**")
        
        if STORE_RUN_RESULT:
            st.write(f"**Run ID:** `{new_run_id}`")
        
        results = asyncio.run(collect_results(prompt, USE_AOAI, selected_model, new_run_id if STORE_RUN_RESULT else None))
        st.session_state.elapsed = results[-1][1] if results[-1] is not None else None
        
        # Display full shareable URL after task completion
        if STORE_RUN_RESULT:
            # Get the current URL and construct the shareable link
            current_url = st.get_option("browser.serverAddress") or "http://localhost"
            server_port = st.get_option("browser.serverPort") or 8501
            full_url = f"{current_url}:{server_port}?run_id={new_run_id}"
            
            st.success("🔗 **Shareable URL (copy and paste to share this result):**")
            st.code(full_url, language="text")

    if st.session_state.elapsed is not None:
        st.write(f"**Prompt tokens: {st.session_state.prompt_token}**")
        st.write(f"**Completion tokens: {st.session_state.completion_token}**")

if __name__ == "__main__":
    main()