# ---- Builder Stage ----
# This stage installs dependencies, including build-time ones.
FROM python:alpine3.22 AS builder

# Set environment variables to prevent generating .pyc files and to run Python in unbuffered mode
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory
WORKDIR /usr/src/app

# Install system dependencies required for building Python packages (like asyncpg)
# --no-cache: Do not store the package index in the image
# build-base: A meta-package that includes gcc, make, etc.
# postgresql-dev: Required for building the asyncpg driver
RUN apk add --no-cache build-base postgresql-dev

# Create a virtual environment to isolate Python packages
RUN python -m venv /opt/venv

# Set the PATH to include the virtual environment's binaries
ENV PATH="/opt/venv/bin:$PATH"

# Copy the requirements file and install dependencies into the venv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Final Stage ----
# This is the lean, production-ready image.
FROM python:alpine3.22 AS final

# Set the working directory
WORKDIR /usr/src/app

# Create a non-root user and group for security
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

# Install runtime dependencies for postgresql
# libpq is the C application programmer's interface to PostgreSQL.
RUN apk add --no-cache libpq

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy the application code into the container
COPY . .

# Change the ownership of the application directory to the non-root user
RUN chown -R appuser:appgroup /usr/src/app

# Switch to the non-root user
USER appuser

# Set the PATH to use the virtual environment's executables
ENV PATH="/opt/venv/bin:$PATH"

# Command to run when the container launches
# First, it runs database migrations with Alembic, then it starts the bot.
CMD ["sh", "-c", "alembic upgrade head && python main.py"]
