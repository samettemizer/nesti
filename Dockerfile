# Orchestrator image – runs the Python AI Developer agent
FROM python:3.12-slim

WORKDIR /orchestrator

# System dependencies (git is required by GitPython)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Phase 8: bake the ~65 MB ONNX embedding model into the image so the first
# issue of a fresh deployment never stalls on a silent download in node_plan.
ENV FASTEMBED_CACHE_PATH=/opt/fastembed
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

COPY . .
RUN echo '#!/bin/bash\npython /orchestrator/scripts/oauth.py "$@"' > /usr/local/bin/nesti && chmod +x /usr/local/bin/nesti

ENTRYPOINT ["python", "main.py"]
CMD ["--loop"]
