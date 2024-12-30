FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    ffmpeg \
    audacity \
    xvfb \
    pulseaudio \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create upload directory
RUN mkdir -p app/static/uploads

# Set environment variables
ENV DISPLAY=:99
ENV FLASK_APP=app/main.py
ENV FLASK_ENV=development

# Copy and set up start script
COPY start.sh /start.sh
RUN chmod +x /start.sh

CMD ["/start.sh"]












# # Dockerfile
# FROM ubuntu:20.04

# ENV DEBIAN_FRONTEND=noninteractive

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     python3 \
#     python3-pip \
#     audacity \
#     xvfb \
#     && rm -rf /var/lib/apt/lists/*

# # Set up working directory
# WORKDIR /app

# # Copy requirements and install Python dependencies
# COPY requirements.txt .
# RUN pip3 install --no-cache-dir -r requirements.txt

# # Copy application code
# COPY . .

# # Create upload directory
# RUN mkdir -p app/static/uploads

# # Set environment variables
# ENV DISPLAY=:99
# ENV FLASK_APP=app/main.py
# ENV FLASK_ENV=development

# # Command to run the application
# CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x16 & python3 -m flask run --host=0.0.0.0"]
