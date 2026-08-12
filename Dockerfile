FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src:/app \
    CHROMA_DIR=/app/.chroma \
    ANONYMIZED_TELEMETRY=False

WORKDIR /app

# Dependencies first so the layer caches across code edits.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake the MiniLM ONNX embedding model into the image so runs need no network
# and every run embeds with byte-identical weights.
RUN python -c "from chromadb.utils import embedding_functions as ef; \
    ef.DefaultEmbeddingFunction()(['warm the model cache'])"

COPY . .

CMD ["python", "scripts/run_all.py"]
