FROM python:3.11-slim

# Install system dependencies: ffmpeg for audio, nodejs/npm for YouTube signatures
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the script named app.py
CMD ["python", "app.py"]
