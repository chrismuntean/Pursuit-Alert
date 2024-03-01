# Use official Python 3 base image
FROM python:3

# Set the working directory in the container
WORKDIR /usr/src/app

# Copy the current directory contents into the container
COPY . .

# Update and upgrade the system
RUN apt-get update && apt-get upgrade -y libgl1-mesa-glx && \
    apt-get install -y usbutils

RUN pip install --upgrade pip

# Install requirements.txt
RUN pip install -r requirements.txt

# Make port 8501 available to the world outside this container
EXPOSE 8501

# Run app.py when the container launches
CMD ["streamlit", "run", "Pursuit_Alert.py"]