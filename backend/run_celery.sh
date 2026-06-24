# RUn celery with 4 workers
clear
echo "Running celery"
celery -A core.celery_tasks.c_app worker --loglevel=info