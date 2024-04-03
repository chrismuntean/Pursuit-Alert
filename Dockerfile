# DO NOT HAVE ANY VPN OR CLOUDFLARE WARP CONNECTED
# it waill not resolve debian network and sum other shit
# that may not actually be true - make sure system clock is correct 
# that resolves some issues too

# Stage 1: Build stage for installing system dependencies
FROM python:3-slim AS build-env

# Set the working directory in the container
WORKDIR /usr/src/app

# Install system dependencies
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends usbutils libgl1-mesa-glx libglib2.0-0 gcc g++ python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements.txt file into the image
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Stage 2: Final stage for running the application
FROM python:3-slim AS runtime

# Install only the necessary system dependencies in the runtime image
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the runtime container
WORKDIR /usr/src/app

# Copy installed Python packages from build-env
COPY --from=build-env /usr/local /usr/local

# Copy the rest of the application
COPY . .

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Run app when the container launches
CMD ["streamlit", "run", "Pursuit_Alert.py"]