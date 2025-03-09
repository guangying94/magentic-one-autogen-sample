# Magentic-One API

This project provides a FastAPI-based backend to handle long-running tasks using the Magentic-One library. It includes three main API endpoints to create tasks, check their status, and retrieve results. The results are stored in a SQLite database.

## Setup

1. **Run the FastAPI application:**
   ```sh
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

## API Endpoints

### 1. Create a Task

**Endpoint:** `POST /tasks`

**Description:** Creates a new task with the given prompt and starts processing it in the background.

**Request Body:**
```json
{
  "prompt": "Tell me a short story about AI",
  "use_aoai": true,
  "model_name": "gpt-4o"
}
```

**Response:**
```json
{
  "task_id": "unique-task-id",
  "status": "pending",
  "created_at": "2023-10-10T10:00:00"
}
```

### 2. Check Task Status

**Endpoint:** `GET /tasks/{task_id}`

**Description:** Retrieves the status of the specified task.

**Response:**
```json
{
  "task_id": "unique-task-id",
  "status": "running",
  "prompt": "Tell me a short story about AI",
  "created_at": "2023-10-10T10:00:00",
  "updated_at": "2023-10-10T10:05:00"
}
```

### 3. Get Task Result

**Endpoint:** `GET /tasks/{task_id}/result`

**Description:** Retrieves the result of the specified task if it is completed.

**Response:**
```json
{
  "task_id": "unique-task-id",
  "status": "completed",
  "result": {
    "messages": [
      {
        "source": "MagenticOneOrchestrator",
        "content": "Once upon a time...",
        "type": "text"
      }
    ],
    "task_result": {
      "status": "completed"
    },
    "execution_time": 300
  },
  "prompt_tokens": 50,
  "completion_tokens": 150,
  "created_at": "2023-10-10T10:00:00",
  "updated_at": "2023-10-10T10:05:00"
}
```

## How It Works

1. **Database Initialization:**
   - The SQLite database is initialized at application startup to store task information.

2. **Task Creation:**
   - When a new task is created via the `POST /tasks` endpoint, it is stored in the database with a status of "pending".
   - The task is then processed in the background using the `process_task` function.

3. **Task Processing:**
   - The `process_task` function updates the task status to "running" and initializes the appropriate client (Azure OpenAI or OpenAI).
   - The Magentic-One library is used to run the task, and results are streamed and collected.
   - Intermediate messages and the final result are structured and stored in the database.

4. **Task Status and Result Retrieval:**
   - The `GET /tasks/{task_id}` endpoint retrieves the current status of the task.
   - The `GET /tasks/{task_id}/result` endpoint retrieves the final result of the task if it is completed.

## Additional Information

- The `main.py` file contains the complete implementation of the FastAPI application, including database setup, Pydantic models, background task processing, and API endpoints.
- The results are structured as JSON and stored in the SQLite database for easy retrieval and processing.

Feel free to explore and modify the code to suit your needs. If you encounter any issues, please refer to the FastAPI and SQLite documentation for further assistance.