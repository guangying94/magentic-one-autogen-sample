import os
import asyncio
from dotenv import load_dotenv
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.azure import ACADynamicSessionsCodeExecutor

load_dotenv()


## Define the client used for the agent
aoai_client = AzureOpenAIChatCompletionClient(
    azure_endpoint=os.getenv('AZURE_OPEN_AI_ENDPOINT'),
    model=os.getenv('AZURE_OPEN_AI_MODEL_NAME'),
    api_version="2024-12-01-preview",
    api_key=os.getenv('AZURE_OPEN_AI_KEY')
)

credential = DefaultAzureCredential()

code_executor = ACADynamicSessionsCodeExecutor(
    pool_management_endpoint=os.getenv('ACA_POOL_MANAGEMENT_ENDPOINT'),
    credential=credential,
)

async def write_code_with_aca():
    m1 = MagenticOne(client=aoai_client, code_executor=code_executor)
    task = "Write an python code to calculate the nth fibonacci number, and also display the host name of the compute the codes being executed. Then, execute the code to calculate the 10th fibonacci number and reply user."
    result = await Console(m1.run_stream(task=task))
    print(result)


if __name__ == "__main__":
    asyncio.run(write_code_with_aca())