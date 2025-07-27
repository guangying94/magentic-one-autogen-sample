# Use the official Python image from the Docker Hub
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Install ffmpeg and other dependencies
RUN apt-get update && apt-get install -y ffmpeg && apt-get clean

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Install playwright
RUN playwright install --with-deps chromium

# Copy the start script into the container
COPY start.sh .

RUN chmod +x start.sh

# Expose the ports for Streamlit and FastAPI
EXPOSE 8501 8000

# Command to run the start script
CMD ["./start.sh"]