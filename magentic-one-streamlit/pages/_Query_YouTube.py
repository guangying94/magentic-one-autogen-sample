import streamlit as st
import os
import yt_dlp
from datetime import datetime
import asyncio
import time
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_ext.agents.video_surfer import VideoSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from dotenv import load_dotenv

load_dotenv()

# Ensure the download directory exists
DOWNLOAD_DIR = "./tmp/video"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_video(url, download_dir):
    current_time = datetime.now().strftime("%H-%M-%d%m%y")
    ydl_opts = {
        'format': 'best',
        'outtmpl': os.path.join(download_dir, f'{current_time}.%(ext)s'),
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        video_file = ydl.prepare_filename(info_dict)
    return video_file

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
        2. Generate a transcription of the video and display the full transcription in English if the transcribed language is not English.\n
        3. Use the transcription to find which part of the video the question is referring to.\n
        4. In addition, you can use video timestamp to answer question. If no timestamp given, you use timestamp of every 5 seconds to analyse and answer user question. \n
        5. Provide a detailed answer to the question.\n
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
    for result in results:
        if result is not None and result.__class__.__name__ == 'TaskResult':
            print(result)
            for message in result.messages:
                if message.source != "user":
                    if message.models_usage:
                        st.session_state.prompt_token = message.models_usage.prompt_tokens + st.session_state.prompt_token
                        st.session_state.completion_token = message.models_usage.completion_tokens + st.session_state.completion_token
    return results

st.title("Autogen Video Surfer Agent - Query YouTube")

st.sidebar.title("Settings")
USE_AOAI = st.sidebar.checkbox("Use Azure OpenAI", value=True)

st.write("Provide the URL of the YouTube video")
video_url = st.text_input("Video URL", value="")

st.session_state.prompt_token = 0
st.session_state.completion_token = 0

if video_url:
    st.write("Enter the task definition for the video surfer agent.")
    task_definition = st.text_area("Task Definition", value="")

    if st.button("Execute Task"):
        video_path = None
        if video_url:
            try:
                st.info('Downloading video...', icon="ℹ️")
                video_file = download_video(video_url, DOWNLOAD_DIR)
                st.success(f"Video downloaded successfully: {video_file}")
                st.video(video_file)
                video_path = video_file
            except Exception as e:
                st.error(f"Error downloading video: {e}")
        else:
            st.warning("Please enter a video URL.")
        
        if video_path:
            st.info('Processing video, please wait...', icon="ℹ️")
            results = asyncio.run(collect_video_results(f"The videos can be found in {video_path}. {task_definition}"))
            st.write("Done processing video!")
            st.write(f"**Prompt tokens: {st.session_state.prompt_token}**")
            st.write(f"**Completion tokens: {st.session_state.completion_token}**")

            st.write("Cleaning up...")
            os.remove(video_path)
            st.write("Done cleaning up!")