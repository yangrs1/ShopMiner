# Stage 1: Build frontend
FROM node:20-alpine AS builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2: Production image
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY run.py .
COPY migrations/ ./migrations/
COPY --from=builder /frontend/dist/ ./frontend/dist/

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
