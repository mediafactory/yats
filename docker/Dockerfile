# Base image: Python 3.12 slim. NOTE: pinned to 3.12 (NOT 3.13) — pydub imports
# the stdlib `audioop` module, which was removed in Python 3.13.
FROM python:3.12-slim AS builder

# Set working directory for all subsequent commands
WORKDIR /app

# Python environment variables:
# Prevents Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Ensures Python output is sent straight to terminal without buffering
ENV PYTHONUNBUFFERED=1

# Upgrade pip to latest version
RUN pip install --upgrade pip

# Install system dependencies:
# libpq-dev: Required for psycopg2 (PostgreSQL adapter)
# gcc: Required for compiling some Python packages
RUN apt-get update \
    && apt-get -y install memcached locales-all libjpeg62-turbo libjpeg-dev libpng-dev screen apache2 sqlite3 gettext ant wget ntp clamav clamav-daemon libreoffice curl build-essential libmagickwand-dev python3-xapian libxapian-dev python3-xapian-haystack ffmpeg

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .
# Install Python dependencies without storing pip cache
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of application code to container
COPY . .

# Document that the container listens on port 8000
EXPOSE 8000

# Make the entrypoint script executable
RUN chmod +x  /app/entrypoint.prod.sh

# Set the entrypoint script as the default command
# This will run migrations, collect static files, and start Gunicorn
CMD ["/app/entrypoint.prod.sh"]
