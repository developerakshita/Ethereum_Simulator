# Use an official Python runtime as a parent image
FROM python:3.10.2-slim-buster

# Set the working directory in the container to /app
WORKDIR /app

# Install gcc, iproute2, and other build-essential tools
RUN apt-get update && apt-get install -y build-essential iproute2


# Install Flask and other required packages
RUN pip install Flask requests pysha3 jsonpickle ecdsa apscheduler


# Copy the current directory contents into the container at /app
COPY . /app/

# Optionally remove build tools to keep image slim
# RUN apt-get remove -y build-essential && apt-get autoremove -y

# Make the network limit script executable
RUN chmod +x limit_network.sh
