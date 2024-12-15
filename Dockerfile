FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tree \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash user

WORKDIR /app
COPY . .
RUN pip install -e . && pip install pyperclip

ENTRYPOINT ["repo-to-text"]
