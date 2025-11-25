FROM python:3.11-slim

WORKDIR /app

# Install system dependencies required by python-docx
RUN apt-get update && apt-get install -y \
    libxml2 \
    libxslt1.1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
