# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS base

ARG USERNAME=edge
ARG USER_UID=1000
ARG USER_GID=1000

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends git make \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid ${USER_GID} ${USERNAME} \
    && useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME}

WORKDIR /workspace

# Pre-install dependencies for better layer caching
COPY requirements.txt requirements-dev.txt /tmp/deps/
COPY auto_patch/requirements.txt /tmp/deps/auto_patch/
RUN python -m pip install -r /tmp/deps/requirements-dev.txt \
    && rm -rf /tmp/deps

# Copy project files
COPY . /workspace

RUN chown -R ${USERNAME}:${USERNAME} /workspace

USER ${USERNAME}

CMD ["bash"]
