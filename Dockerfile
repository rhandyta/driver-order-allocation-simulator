# Stage 1: Build Go high-performance simulator binary
FROM golang:1.20-alpine AS go-builder
WORKDIR /app
COPY go.mod ./
COPY internal/ ./internal/
COPY cmd/ ./cmd/
RUN go build -o /app/bin/simulator cmd/simulator/main.go

# Stage 2: Python runtime environment
FROM python:3.10-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy python requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code & compiled Go binary
COPY . .
COPY --from=go-builder /app/bin/simulator /app/bin/simulator

EXPOSE 8501 8000

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
