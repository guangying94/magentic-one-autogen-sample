import streamlit as st
import asyncio
import time
import os
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient, AzureOpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne

load_dotenv()

MAGENTIC_ONE_MODE=os.getenv('MAGENTIC_ONE_MODE')

def format_source_display(source):
    """
    Returns a formatted string with an emoji representing the source type.
    
    Args:
        source (str): The source type to format.
        
    Returns:
        str: A string with an emoji and the source type.
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

async def run_task(user_prompt: str):
    """
    Executes a task based on the user prompt using either OpenAI or Azure OpenAI client, together with Magentic-One via Autogen extension.
    Streams the results and displays them in the UI.
    
    Args:
        user_prompt (str): The prompt provided by the user.
        
    Yields:
        chunk: The result chunk from the task.
        float: The time taken to complete the task.
    """
    start_time = time.time()
    if(MAGENTIC_ONE_MODE == 'OAI'):
        client = OpenAIChatCompletionClient(
            model=os.getenv('OPEN_AI_MODEL_NAME'),
            api_key=os.getenv('OPEN_AI_API_KEY')
        )
    else:
        client = AzureOpenAIChatCompletionClient(
            azure_endpoint=os.getenv('AZURE_OPEN_AI_ENDPOINT'),
            model=os.getenv('AZURE_OPEN_AI_MODEL_NAME'),
            api_version="2024-05-01-preview",
            api_key=os.getenv('AZURE_OPEN_AI_KEY')
        )

    m1 = MagenticOne(client=client)
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

async def collect_results(user_prompt: str):
    """
    Collects and returns all result chunks from the run_task function.
    
    Args:
        user_prompt (str): The prompt provided by the user.
        
    Returns:
        list: A list of result chunks.
    """
    results = []
    async for chunk in run_task(user_prompt):
        results.append(chunk)
    return results

def main():
    st.title('🧠🤖 Magentic-One Demo')
    st.write('Implementation using Autogen and Streamlit')

    if 'output' not in st.session_state:
        st.session_state.output = None
        st.session_state.elapsed = None

    prompt = st.text_input('What is the task today?', value='')

    if st.button('Execute'):
        results = asyncio.run(collect_results(prompt))
        st.session_state.elapsed = results[-1][1] if results[-1] is not None else None

    if st.session_state.elapsed is not None:
        st.write(f"Elapsed time: {st.session_state.elapsed:.2f} seconds")

if __name__ == "__main__":
    main()