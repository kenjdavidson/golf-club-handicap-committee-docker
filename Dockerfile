FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    poppler-utils \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --break-system-packages \
    mcp \
    openpyxl \
    pandas \
    pypdf \
    requests \
    streamlit

RUN curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /workspace
EXPOSE 8080

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
