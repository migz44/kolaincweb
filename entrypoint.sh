#!/bin/sh

echo "Waiting for MySQL..."

# Wait until the db service is ready
while ! nc -z db 3306; do
  sleep 1
done

echo "MySQL started"

# Run migrations and collect static files
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Start Gunicorn server
exec "$@"
