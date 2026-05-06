#!/bin/sh

# Wait for DB if necessary (optional but good)
echo "Running migrations..."
python manage.py migrate --noinput

# Start Gunicorn
echo "Starting server..."
exec gunicorn --bind :8080 stockpot.wsgi:application
