# Reproducible Compact compiler for hosts without a native build (e.g. Windows).
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates xz-utils \
 && rm -rf /var/lib/apt/lists/*
RUN curl --proto '=https' --tlsv1.2 -LsSf \
      https://github.com/midnightntwrk/compact/releases/latest/download/compact-installer.sh | sh
ENV PATH="/root/.local/bin:${PATH}"
RUN compact update 0.31.1 && compact compile --version
WORKDIR /work
ENTRYPOINT ["compact"]
