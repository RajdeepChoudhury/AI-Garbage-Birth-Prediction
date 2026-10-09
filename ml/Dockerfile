FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Code and outputs live in the mounted ./ml folder so artifacts persist on the host
CMD ["sh", "-c", "python data/generate_synthetic.py --out data/garbage_synthetic.csv && python train.py"]
