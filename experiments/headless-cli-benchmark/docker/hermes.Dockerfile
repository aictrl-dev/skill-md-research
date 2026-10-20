ARG BASE=aictrl-harness-bench:base-python314
FROM ${BASE}
USER root
# Core release dependencies only. Keep source tree for bundled skills/prompts and version provenance.
RUN --mount=type=bind,source=hermes-source.tar.gz,target=/tmp/hermes-source.tar.gz mkdir -p /opt/hermes && tar -xzf /tmp/hermes-source.tar.gz --strip-components=1 -C /opt/hermes \
    && python -m venv /opt/hermes-venv \
    && /opt/hermes-venv/bin/pip install --no-cache-dir -e /opt/hermes \
    && /opt/hermes-venv/bin/pip freeze > /usr/local/share/hermes-pip-freeze.txt \
    && ln -s /opt/hermes-venv/bin/hermes /usr/local/bin/hermes
ENV PATH=/opt/hermes-venv/bin:$PATH
USER runner
