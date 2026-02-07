# Use a lightweight Python image
FROM python:3.11-slim

# Install system dependencies (FFmpeg is required for audio)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your bot code
COPY . .

# Run the bot (Using app.py)
CMD ["python", "app.py"]