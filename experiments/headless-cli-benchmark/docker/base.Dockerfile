# Matching runtime bases with the same tools, non-root user, empty HOME and fixture.
# Image increments are measured relative to each matching runtime base.
ARG NODE_IMAGE=node:20-slim
FROM ${NODE_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends git ripgrep ca-certificates time procps strace \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /var/empty && useradd -m -k /var/empty -u 10001 runner \
    && mkdir -p /workspace && chown runner /workspace
COPY measure.sh /usr/local/bin/measure.sh
USER runner
ENV HOME=/home/runner
WORKDIR /workspace
# Fixture repo: a small file and a ~50 KB file to read.
RUN git init -q . && printf 'alpha beta gamma\n%.0s' $(seq 20) > notes.txt \
    && for i in $(seq 1 800); do printf 'line %04d lorem ipsum dolor sit amet consectetur adipiscing\n' $i; done > big.txt \
    && test "$(wc -c < big.txt)" = 48000 \
    && git -c user.email=b@b -c user.name=b add . && git -c user.email=b@b -c user.name=b commit -qm init
