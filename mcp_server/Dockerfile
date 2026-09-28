# Nesti MCP server image – exposes graph/tools.py over the Model Context Protocol.
#
# Build context is the project ROOT (see docker-compose.yml nesti-mcp service):
#   docker build -t nesti-mcp -f mcp_server/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Phase 8: the memory tools embed in-process, same as the orchestrator — bake
# the ONNX embedding model in so no MCP call waits on a download.
ENV FASTEMBED_CACHE_PATH=/opt/fastembed
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

COPY . .

CMD ["python", "-m", "mcp_server.server"]
