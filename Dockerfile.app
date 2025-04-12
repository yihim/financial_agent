FROM continuumio/miniconda3:latest

WORKDIR /app

RUN apt-get update && \
    apt-get install -y jq --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN conda create -n stapp python=3.10 -y && \
    echo "conda activate stapp" >> ~/.bashrc
SHELL ["bash", "-c"]

COPY requirements.txt .
RUN conda run -n stapp pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8090

# Create entrypoint script in the container
RUN echo '#!/bin/bash' > /app/entrypoint.sh && \
    echo 'exec conda run --no-capture-output -n stapp "$@"' >> /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Set the entrypoint to our script
ENTRYPOINT ["/app/entrypoint.sh"]