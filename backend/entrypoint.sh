#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Run your existing database migration script
echo "Running database migrations..."
./scripts/fast db upgrade

# Start the application server using your server script
echo "Starting application server..."
exec ./server