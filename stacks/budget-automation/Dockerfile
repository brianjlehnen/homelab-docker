# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Install system dependencies including cron
RUN apt-get update && apt-get install -y \
    cron \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY budget_automation.py .

# Create necessary directories with proper permissions
RUN mkdir -p /app/reports /app/logs /app/config && \
    chmod 755 /app/reports /app/logs /app/config

# Make the script executable
RUN chmod +x budget_automation.py

# Set timezone
ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Default command (overridden in compose.yaml)
CMD ["python", "budget_automation.py"]