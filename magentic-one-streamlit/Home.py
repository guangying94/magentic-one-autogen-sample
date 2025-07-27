import streamlit as st
import asyncio
import time
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient, AzureOpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

# Import Azure storage utilities
from store_result_util import storage_manager

load_dotenv()

def display_stored_result(document):
    """Display a stored run result from Cosmos DB with images from Blob Storage."""
    st.title('🧠🤖 Magentic-One Demo - Stored Result')
    
    st.write(f"**Run ID:** {document['id']}")
    st.write(f"**Original Prompt:** {document['prompt']}")
    st.write(f"**Model:** {document['model_name']}")
    st.write(f"**Azure OpenAI:** {'Yes' if document['use_azure_openai'] else 'No'}")
    st.write(f"**Created At:** {document['created_at']}")
    st.write(f"**Elapsed Time:** {document['elapsed_time']:.2f} seconds")
    st.write(f"**Prompt Tokens:** {document['prompt_tokens']}")
    st.write(f"**Completion Tokens:** {document['completion_tokens']}")
    
    # Show document size if available
    if 'document_size_mb' in document:
        st.write(f"**Stored Size:** {document['document_size_mb']:.2f} MB")
    
    # Show image count if available
    if 'total_images' in document and document['total_images'] > 0:
        st.write(f"**Images:** {document['total_images']} stored in blob storage")
    
    # Show warning if metadata only
    if document.get('is_metadata_only', False):
        st.warning("⚠️ This result was too large for storage. Only metadata is available.")
    
    st.write("---")
    st.write("**Execution Results:**")
    
    for result in document['results']:
        # Handle different result types
        if result.get('type') == 'TruncationNote':
            st.warning(f"⚠️ {result['content']}")
            continue
            
        if result.get('type') == 'MetadataOnly':
            st.info(f"ℹ️ {result['content']}")
            continue
        
        if result['source']:
            st.write(f"**{format_source_display(result['source'])}**")
        
        if isinstance(result['content'], dict) and result['content'].get('type') == 'image':
            # Display image from blob storage or show note
            blob_url = result['content'].get('blob_url')
            if blob_url:
                try:
                    # Download image from blob storage using authenticated client
                    with st.spinner("Loading image from secure storage..."):
                        image_bytes = storage_manager.download_image_from_blob(blob_url)
                    
                    if image_bytes:
                        # Display the downloaded image
                        st.image(image_bytes, caption=f"Image ({result['content'].get('size_kb', 'Unknown')} KB)")
                    else:
                        st.error("Failed to download image from blob storage")
                        st.write(f"Image URL: {blob_url}")
                except Exception as e:
                    st.error(f"Failed to load image from blob storage: {e}")
                    st.write(f"Image URL: {blob_url}")
            elif 'note' in result['content']:
                st.info(f"🖼️ {result['content']['note']}")
            else:
                st.info("🖼️ Image content not available")
        elif result['content'] and isinstance(result['content'], str):
            # Display text content
            content = result['content']
            if "[Content truncated due to size limits]" in content:
                st.warning("⚠️ Content was truncated due to size limits")
            st.markdown(content)

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
    if storage_manager.is_enabled() and run_id:
        elapsed_time = results[-1][1] if results[-1] is not None else 0
        storage_manager.store_run_result(
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
    
    if run_id and storage_manager.is_enabled():
        # Display stored result
        stored_result = storage_manager.load_run_result(run_id)
        if stored_result:
            display_stored_result(stored_result)
            return
        else:
            st.error(f"Run with ID {run_id} not found")
            st.write("Continuing to main interface...")
    
    st.title('🧠🤖 Magentic-One Demo')
    st.write('Implementation using Autogen and Streamlit')
    
    if storage_manager.is_enabled():
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
        
        if storage_manager.is_enabled():
            st.write(f"**Run ID:** `{new_run_id}`")
        
        results = asyncio.run(collect_results(prompt, USE_AOAI, selected_model, new_run_id if storage_manager.is_enabled() else None))
        st.session_state.elapsed = results[-1][1] if results[-1] is not None else None
        
        # Display full shareable URL after task completion
        if storage_manager.is_enabled():
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