# Magentic-One, implementation via Microsoft Autogen 0.4 Extension
This is a sample implementation of Magentic-One, using Microsoft Autogen 0.4 Extension. Streamlit serve as frontend and it shows the progress of Magentic-One in real time.

## Introduction of Magentic-One
Microsoft Magentic-One is an innovative generalist multi-agent system designed to tackle various open-ended web and file-based tasks. Launched to enhance generative AI capabilities, it facilitates the automation and coordination of multiple specialized agents, enabling efficient problem-solving in both work and personal settings. This system aims to replicate the complexities users encounter, making it a valuable asset for developers and businesses seeking streamlined operations.

Magentic-One consists of a collection of agents that work together to complete tasks:
- **Orchestrator**: The Task Agent is responsible for defining the task and managing the overall process.
- **FileSurfer**: The File Agent is in charge of file operations, such as reading, writing, and processing files.
- **WebSurfer**: The Web Agent is responsible for web operations, such as scraping, searching, and interacting with websites.
- **Coder**: The Code Agent is designed to generate code snippets and scripts to automate tasks.
- **ComputerTerminal**: The Terminal Agent is responsible for executing commands and interacting with the terminal.

## Introduction of Microsoft Autogen
Microsoft Autogen 0.4 represents a significant advancement in the AutoGen framework, supporting the development of multi-agent applications. This version introduces enhanced functionalities that simplify the creation and management of AI agents, allowing them to collaborate effectively on complex tasks. The updates focus on improving automation processes and expanding the framework’s capabilities, fostering a robust ecosystem for AI application development.

## Pre-requisites
- Azure OpenAI account, or OpenAI account
- LiteLLM (optional)
- PostgreSQL database (optional)
  
## How to run locally
1. Create a python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```
2. Install the required packages
```bash
pip install -r requirements.txt
```

3. Set the environment variables
The code requires several environment variables to be set. You can set them in a `.env` file in the root directory of the project. The `.env` file should look like sample `.env.sample`. More explanation on the environment variables can be found below.

4. Run the Streamlit app
```bash
streamlit run Home.py
```

5. Open the browser and go to `http://localhost:8501` to see the app.
6. On the home page, you can provide the task definition and the app will show the progress of the task.
7. To stop the app, press `Ctrl+C` in the terminal.
8. To containerize the app, you can use the Dockerfile provided in the root directory. Run the following command to build the image.
```bash
docker build -t magentic-one-streamlit .
```
9. To run the container, use the following command.
```bash
docker run -p 8501:8501 magentic-one-streamlit
```

## Environment Variables
| Variable Name                | Description                                      | Example Value                              |
|------------------------------|--------------------------------------------------|--------------------------------------------|
| `POSTGRESQL_HOST`            | Host address for the PostgreSQL database         | `xxxx.database.azure.com`                  |
| `POSTGRESQL_DB`              | Name of the PostgreSQL database                  | `ai_demo`                                    |
| `POSTGRESQL_USER`            | Username for the PostgreSQL database             | `user`                                      |
| `POSTGRESQL_PASSWORD`        | Password for the PostgreSQL database             | `password`                                      |
| `POSTGRESQL_PORT`            | Port number for the PostgreSQL database          | `5432`                                     |
| `LLM_MODEL_NAME`             | Name of the language model                       | `phi3.5:latest`                           |
| `LITELLM_HOST`               | Host address for the LiteLLM service             | `https://sample.litellm.com`                         |
| `LITE_LLM_KEY`               | API key for the LiteLLM service                  | `sk-12345678`                                  |
| `AZURE_OPEN_AI_ENDPOINT`     | Endpoint for Azure OpenAI service                | `https://xxxxx.openai.azure.com/`     |
| `AZURE_OPEN_AI_KEY`          | API key for Azure OpenAI service                 | `xxxxx`                   |
| `AZURE_OPEN_AI_MODEL_NAME`   | Model name for Azure OpenAI service              | `gpt-4o-mini`                              |
| `OPEN_AI_MODEL_NAME`         | Model name for OpenAI service                  | `gpt-4o-mini-2024-07-18`                                |
| `OPEN_AI_API_KEY`            | API key for OpenAI service                       | `sk-xxxxx`                                     |

## References
- [Streamlit](https://streamlit.io/)
- [Magentic-One](https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/)
- [Microsoft Autogen 0.4](https://microsoft.github.io/autogen/stable/)
- [Autogen Extension - Magentic-One](https://microsoft.github.io/autogen/stable/reference/python/autogen_ext.teams.magentic_one.html)
- [LiteLLM](https://docs.litellm.ai/docs/)