ARG BASE=aictrl-harness-bench:base
FROM ${BASE}
USER root
# Native GNU release needs libxcb even for --version; this dependency belongs to Goose's increment.
RUN apt-get update && apt-get install -y --no-install-recommends libxcb1 libdbus-1-3 libssl3 \
    && rm -rf /var/lib/apt/lists/*
COPY --chmod=755 goose /usr/local/bin/goose
RUN ldd /usr/local/bin/goose > /usr/local/share/goose-ldd.txt \
    && ! grep 'not found' /usr/local/share/goose-ldd.txt
USER runner
