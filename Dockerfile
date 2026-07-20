FROM python:3.11-slim

# Hugging Face Spaces run as user 1000
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"

WORKDIR /app/backend

# Install system dependencies if required for PyMuPDF/faiss
USER root
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
USER user

# Copy backend requirements
COPY --chown=user backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the backend code and FAISS indices
COPY --chown=user backend/ .

# Hugging Face Spaces expose port 7860
EXPOSE 7860

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
