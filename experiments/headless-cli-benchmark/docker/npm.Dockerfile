# A harness installed from npm the way the executor does it: `npm install -g <pkg>@<version>`.
# HOME=/root so postinstall scripts and the npm cache cannot leave files in runner's empty HOME.
ARG BASE=bench-cmp:base
FROM ${BASE}
USER root
ARG PKG
RUN HOME=/root npm install -g --no-audit --no-fund "$PKG" && rm -rf /root/.npm /root/.cache /root/.local /root/.config
USER runner
