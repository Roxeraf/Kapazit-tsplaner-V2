FROM python:3.11-slim

# Node wird für den PPTX-Export (export/PLX_generate_pptx.js) benötigt.
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .

WORKDIR /app/export
COPY export/package.json export/package-lock.json* ./
RUN npm install --omit=dev
COPY export/ .

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
