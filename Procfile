web: gunicorn revisia_backend.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 300 --keep-alive 2
release: python manage.py migrate && python manage.py collectstatic --noinput

