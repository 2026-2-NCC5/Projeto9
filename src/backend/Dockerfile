FROM python:3.11-slim

WORKDIR /app

# Dependencias do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar codigo
COPY . .

# Criar diretorios necessarios
RUN mkdir -p chroma_db knowledge_base/demo knowledge_base/official

# Pre-download do modelo MiniLM para evitar latencia ou falha de rede no startup
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Garantir greenlet para SQLAlchemy AsyncIO
RUN pip install --no-cache-dir greenlet==3.5.6

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

