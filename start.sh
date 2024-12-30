#!/bin/bash

# Start Xvfb
Xvfb :99 -screen 0 1024x768x16 &
sleep 2

# Start pulseaudio
pulseaudio --start --exit-idle-time=-1
sleep 2

# Set up audio
pacmd set-default-sink 0

# Create and set permissions for directories
mkdir -p /app/app/static/uploads
chmod -R 777 /app/app/static/uploads

# Clean up any existing Audacity processes
pkill audacity || true
sleep 1

# Start Flask application
python3 -m flask run --host=0.0.0.0