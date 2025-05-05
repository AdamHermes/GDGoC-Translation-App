# Use a smaller base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies (including fonts for PIL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements.txt first to leverage caching
COPY ui/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Streamlit app source
COPY ui/ .

# Expose the port Streamlit will use
EXPOSE 8501

# Run Streamlit app on all network interfaces
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
