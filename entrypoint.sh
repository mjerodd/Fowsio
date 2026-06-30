#!/bin/ash

echo "Apply database migrations"
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic

exec "$@"