ARG UBUNTU_TAG=25.10

# ==========================
# Builder Stage
# ==========================
FROM ubuntu:${UBUNTU_TAG} AS builder

ARG PYTHON_VERSION=3.14

# Install uv seamlessly from its official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Define a clean explicit path for python installations so we can easily copy it
ENV UV_PYTHON_INSTALL_DIR=/opt/python

# Download and install a standalone Python natively using uv
RUN uv python install ${PYTHON_VERSION}

WORKDIR /app

# Copy dependency definitions
COPY pyproject.toml uv.lock ./

# Create a virtual environment using the downloaded python
RUN uv venv --python ${PYTHON_VERSION}

# Install dependencies into the local environment (.venv)
RUN uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY src src
COPY templates templates
COPY static static
COPY README.md README.md

# Install the project itself
RUN uv sync --frozen --no-dev


# ==========================
# Final Stage
# ==========================
FROM ubuntu:${UBUNTU_TAG}

ARG USER_NAME=richard
ARG GROUP_NAME=vibers

# Create user and group
RUN groupadd -r ${GROUP_NAME} && useradd -m -r -g ${GROUP_NAME} ${USER_NAME}

# Copy the portable python installation so .venv references resolve correctly
COPY --chown=${USER_NAME}:${GROUP_NAME} --from=builder /opt/python /opt/python

WORKDIR /app

# Copy the entire /app directory from the builder, including .venv
COPY --chown=${USER_NAME}:${GROUP_NAME} --from=builder /app /app

# Switch to the non-root user
USER ${USER_NAME}:${GROUP_NAME}

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Run uvicorn natively from the path
CMD [".venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
