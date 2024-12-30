FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Create non-root user
RUN useradd -m -s /bin/bash user

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tree \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all necessary files for package installation
COPY pyproject.toml README.md ./

# Copy the package source
COPY repo_to_text ./repo_to_text

# Install the package
RUN pip install --no-cache-dir -e .

# Copy remaining files
COPY . .

# Set default user
USER user

ENTRYPOINT ["repo-to-text"]
