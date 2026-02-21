FROM python:3.11-slim

# Install system FFmpeg (Professional Choice)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -U yt-dlp

# Copy app code
COPY . .

# Environment setup
ENV PORT=8000
EXPOSE 8000

# Start App
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
