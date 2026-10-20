# Equal payloads at distinct paths avoid native repeated-read guards in scripted turns.
# Applied identically to matching bases and every tool image after tool installation.
ARG BASE=aictrl-harness-bench:base
FROM ${BASE}
USER runner
RUN for i in 0 1 2; do cp notes.txt "notes-$i.txt"; done \
    && for i in $(seq 0 49); do cp big.txt "big-$i.txt"; done \
    && test "$(wc -c < notes-2.txt)" = 340 \
    && test "$(wc -c < big-49.txt)" = 48000 \
    && cmp notes.txt notes-2.txt && cmp big.txt big-49.txt
