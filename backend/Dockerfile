# Optional -- local dev (README.md) is the faster iteration path.
FROM python:3.10-slim

# Open3D needs a few system libraries even in headless/CPU mode.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libgomp1 libusb-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
