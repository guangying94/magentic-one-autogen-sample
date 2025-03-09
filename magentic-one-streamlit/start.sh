#!/bin/sh

# Start the Streamlit app in the background
streamlit run Home.py &

# Start the FastAPI app using uvicorn
uvicorn api.main:app --host 0.0.0.0 --port 8000