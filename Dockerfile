FROM python:3.11-slim

# Install system dependencies including ripgrep and fd-find
RUN apt-get update && apt-get install -y \
    ripgrep \
    fd-find \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s $(which fdfind) /usr/local/bin/fd

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install project dependencies
RUN pip install -e ".[test]"

# Set the default command
CMD ["agent-test-harness"]
