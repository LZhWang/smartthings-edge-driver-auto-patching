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

# Copy the project first: an editable install needs pyproject.toml and the
# package sources present, so dependencies cannot be pre-installed in isolation.
COPY . /workspace

RUN python -m pip install --no-cache-dir -e ".[dev]"

RUN chown -R ${USERNAME}:${USERNAME} /workspace

USER ${USERNAME}

CMD ["bash"]
