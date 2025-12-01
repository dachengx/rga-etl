# Use a lightweight official Python image
FROM python:3.11-slim

# Create a working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the mqtt bridge script
COPY mqtt_bridge.py .

# Expose your HTTP port (change if not 8080)
EXPOSE 8080

# Improve signal handling so Docker stop works properly
STOPSIGNAL SIGINT

# Run your bridge
CMD [ "python", "mqtt_bridge.py" ]
