## Use a lighter base image if GPU is not required
FROM python:3.10-slim

# Switch to root to install system dependencies
USER root

# Set working directory
WORKDIR /app

# Install required system dependencies for OpenCV and PaddleOCR
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1-mesa-glx \
      libglib2.0-0 \
      libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# (Optional) Preinstall paddlepaddle to reduce paddleocr install time
# RUN pip install --no-cache-dir paddlepaddle==<desired-version>

# Copy only the requirements file first to use Docker cache efficiently
COPY backend/requirements.txt ./requirements.txt

# Install Python dependencies (fastapi, paddleocr, etc.)
RUN pip install --no-cache-dir \
      torch==2.2.2+cpu \
      -f https://download.pytorch.org/whl/cpu/torch_stable.html \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY backend/ .

# Expose FastAPI default port
EXPOSE 8000

# Switch to non-root user if desired (e.g., 'torchserve')
# USER torchserve

# Run the FastAPI app
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
