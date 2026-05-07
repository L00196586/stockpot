#!/bin/sh

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating cache table"
python manage.py createcachetable

# Start Gunicorn
echo "Starting server..."
exec gunicorn --bind :8080 stockpot.wsgi:application
