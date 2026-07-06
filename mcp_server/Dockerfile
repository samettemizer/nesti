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

COPY . .

CMD ["python", "-m", "mcp_server.server"]
