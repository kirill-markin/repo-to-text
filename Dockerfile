FROM python:3.14.7-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN useradd -m -s /bin/bash user

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tree \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./

COPY repo_to_text ./repo_to_text

RUN python -m pip install --no-cache-dir --upgrade "pip @ https://files.pythonhosted.org/packages/3f/06/3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/pip-26.2.2-py3-none-any.whl#sha256=fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70" \
    && python -m pip install --no-cache-dir -e .

COPY . .

USER user

ENTRYPOINT ["repo-to-text"]
