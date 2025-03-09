from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import asyncio
import uuid
import sqlite3
import json
import time
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient, OpenAIChatCompletionClient
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor

load_dotenv()

app = FastAPI()

# Define the SQLite database setup
DB_NAME = "magentic_one_tasks.db"

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        prompt TEXT NOT NULL,
        result TEXT,
        created_at TIMESTAMP NOT NULL,
        updated_at TIMESTAMP NOT NULL,
        model_name TEXT,
        use_aoai BOOLEAN NOT NULL,
        prompt_tokens INTEGER DEFAULT 0,
        completion_tokens INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()

# Initialize the database at application startup
init_db()

# Pydantic models
class TaskRequest(BaseModel):
    prompt: str
    use_aoai: bool = True
    model_name: Optional[str] = "gpt-4o"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str

class TaskStatus(BaseModel):
    task_id: str
    status: str
    prompt: str
    created_at: str
    updated_at: str

class TaskResult(BaseModel):
    task_id: str
    status: str
    result: Dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    created_at: str
    updated_at: str

# Background task processing function
async def process_task(task_id: str, prompt: str, use_aoai: bool, model_name: Optional[str] = None):
    # Update task status to running
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
        ("running", datetime.now().isoformat(), task_id)
    )
    conn.commit()
    conn.close()
    
    try:
        # Setup client based on API choice
        if use_aoai:
            client = AzureOpenAIChatCompletionClient(
                azure_endpoint=os.getenv('AZURE_OPEN_AI_ENDPOINT'),
                model=model_name,
                api_version="2024-12-01-preview",
                api_key=os.getenv('AZURE_OPEN_AI_KEY')
            )
        else:
            client = OpenAIChatCompletionClient(
                model=os.getenv('OPEN_AI_MODEL_NAME'),
                api_key=os.getenv('OPEN_AI_API_KEY')
            )

        # Initialize MagenticOne and run the task
        m1 = MagenticOne(client=client,code_executor=LocalCommandLineCodeExecutor())
        print("Running task...")
        
        # Collect results
        results = []
        prompt_tokens = 0
        completion_tokens = 0
        
        async for chunk in m1.run_stream(task=prompt):
            if chunk.__class__.__name__ == 'TaskResult':
                # Process the final result
                for message in chunk.messages:
                    if message.source != "user" and message.models_usage:
                        prompt_tokens += message.models_usage.prompt_tokens
                        completion_tokens += message.models_usage.completion_tokens
                results.append(chunk)
            else:
                # Print intermediate messages
                print(f"Message from {chunk.source}[{chunk.type}]: {chunk.content}")
        
        # Process and structure the results
        structured_result = {
            "messages": [],
            "task_result": None,
            "execution_time": None
        }
        
        for result in results:
            if isinstance(result, dict) and result.get("type") == "message":
                # For intermediate messages
                structured_result["messages"].append({
                    "source": result["source"],
                    "content": result["content"],
                    "type": result["message_type"]
                })
            elif result.__class__.__name__ == 'TaskResult':
                # Extract messages and structure them
                for message in result.messages:
                    if hasattr(message, 'type') and message.type == "MultiModalMessage":
                        msg_data = {
                            "source": message.source,
                            "content": message.content[0],
                            "type": message.type if hasattr(message, 'type') else None
                        }
                        structured_result["messages"].append(msg_data)
                        msg_data = {
                            "source": message.source,
                            "content": message.content[1].to_base64(),
                            "type": "base64_image"
                        }
                        structured_result["messages"].append(msg_data)
                    else:
                        msg_data = {
                            "source": message.source,
                            "content": message.content if hasattr(message, 'type') else None,
                            "type": message.type if hasattr(message, 'type') else None
                        }
                        structured_result["messages"].append(msg_data)
                
                # Set the task result
                structured_result["task_result"] = {
                    "status": "completed"
                }
                structured_result["execution_time"] = result.execution_time if hasattr(result, 'execution_time') else None
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Update the database with completed status and results
        cursor.execute(
            "UPDATE tasks SET status = ?, result = ?, updated_at = ?, prompt_tokens = ?, completion_tokens = ? WHERE id = ?",
            (
                "completed", 
                json.dumps(structured_result), 
                datetime.now().isoformat(),
                prompt_tokens,
                completion_tokens,
                task_id
            )
        )
        conn.commit()
        conn.close()
        
    except Exception as e:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        # Handle exceptions and update status to failed
        cursor.execute(
            "UPDATE tasks SET status = ?, result = ?, updated_at = ? WHERE id = ?",
            ("failed", json.dumps({"error": str(e)}), datetime.now().isoformat(), task_id)
        )
        conn.commit()
        conn.close()

# API Endpoints
@app.post("/tasks", response_model=TaskResponse)
async def create_task(task_request: TaskRequest, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    
    # Store the new task in the database
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO tasks (id, status, prompt, created_at, updated_at, model_name, use_aoai) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (task_id, "pending", task_request.prompt, created_at, created_at, task_request.model_name, task_request.use_aoai)
    )
    conn.commit()
    conn.close()
    
    # Start the task in the background
    background_tasks.add_task(
        process_task, 
        task_id, 
        task_request.prompt,
        task_request.use_aoai,
        task_request.model_name
    )
    
    return TaskResponse(
        task_id=task_id,
        status="pending",
        created_at=created_at
    )

@app.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, status, prompt, created_at, updated_at FROM tasks WHERE id = ?",
        (task_id,)
    )
    task = cursor.fetchone()
    conn.close()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatus(
        task_id=task[0],
        status=task[1],
        prompt=task[2],
        created_at=task[3],
        updated_at=task[4]
    )

@app.get("/tasks/{task_id}/result", response_model=TaskResult)
async def get_task_result(task_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, status, result, created_at, updated_at, prompt_tokens, completion_tokens FROM tasks WHERE id = ?",
        (task_id,)
    )
    task = cursor.fetchone()
    conn.close()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task[1] not in ["completed", "failed"]:
        raise HTTPException(status_code=202, detail="Task still in progress")
    
    result = json.loads(task[2]) if task[2] else {}
    
    return TaskResult(
        task_id=task[0],
        status=task[1],
        result=result,
        prompt_tokens=task[5] or 0,
        completion_tokens=task[6] or 0,
        created_at=task[3],
        updated_at=task[4]
    )

@app.get("/")
async def root():
    return {"message": "Magentic-One API is running"}

