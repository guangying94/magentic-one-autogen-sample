import streamlit as st
import os
import asyncio
import time
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_ext.agents.video_surfer import VideoSurfer
from dotenv import load_dotenv

load_dotenv()

# Ensure the upload directory exists
UPLOAD_DIR = "../uploads/videos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.title("Autogen Video Surfer Agent")
st. write("Microsoft Autogen extension for video surfer agent")

st.sidebar.title("Settings")
USE_AOAI = st.sidebar.checkbox("Use Azure OpenAI", value=True)

# Video upload
uploaded_file = st.file_uploader("Upload a video", type=["mp4", "mov", "avi", "mkv"])

def format_source_display(source):
    if source == "user":
        return "👤 User"
    else:
        return f"💻 Video Surfer"

async def run_video_task(user_prompt: str):
    """Yield console output so we can display it in Streamlit."""
    start_time = time.time()

    # Define an agent
    if USE_AOAI:
        model_client = AzureOpenAIChatCompletionClient(
            azure_endpoint=os.getenv('AZURE_OPEN_AI_ENDPOINT'),
            model=os.getenv('AZURE_OPEN_AI_MODEL_NAME'),
            api_version="2024-05-01-preview",
            api_key=os.getenv('AZURE_OPEN_AI_KEY'),
        )
    else:
        model_client = OpenAIChatCompletionClient(
            model=os.getenv('OPEN_AI_MODEL_NAME'),
            api_key=os.getenv('OPEN_AI_API_KEY')
        )

    video_agent = VideoSurfer(
        name="VideoSurfer",
        model_client=model_client,
        system_message="""
        You are a helpful agent that is an expert at answering questions from a video. \n
        When asked to answer a question about a video, you should:\n
        1. Check if that video is available locally.\n
        2. Use the transcription to find which part of the video the question is referring to.\n
        3. In addition, you can use video timestamp to answer question. If no timestamp given, you use timestamp of every 5 seconds to analyse and answer user question. \n
        4. Provide a detailed answer to the question.\n
        Reply with TERMINATE when the task has been completed.\n
        """
    )

    # Define termination condition
    termination = TextMentionTermination("TERMINATE")

    # Define a team
    agent_team = RoundRobinGroupChat([video_agent], termination_condition=termination)

    # Stream messages from the agent
    stream = agent_team.run_stream(task=user_prompt)

    async for chunk in stream:
        # If this is not the final TaskResult, display the content
        if chunk.__class__.__name__ != 'TaskResult':
            if (chunk.__class__.__name__ != "ToolCallRequestEvent" and chunk.__class__.__name__ != "ToolCallExecutionEvent"):
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

async def collect_video_results(prompt: str):
    """Collect all chunks from run_video_task into a list and return it."""
    results = []
    async for chunk in run_video_task(prompt):
        results.append(chunk)
    return results

if uploaded_file is not None:
    # Save the uploaded file
    file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.success(f"File uploaded successfully: {uploaded_file.name}")

    # Display video preview
    st.video(file_path)

    # Text area for user question
    user_question = st.text_area("Enter the task definition here:")

    if st.button("Submit"):
        st.write("Task Defintion:")
        results = asyncio.run(collect_video_results(f"The videos can be found in {UPLOAD_DIR}. {user_question}"))
        st.write("Done processing video!")

