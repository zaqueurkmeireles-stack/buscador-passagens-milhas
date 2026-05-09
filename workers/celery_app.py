import os
from celery import Celery
from core.config import config

# Configuração Base do Celery
# Redis ou RabbitMQ como Broker, PostgreSQL como Result Backend
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', config.REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', config.REDIS_URL)

celery_app = Celery(
    'travel_engine',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        'workers.sniper_calendario',
        'workers.golden_windows',
        'workers.positioning',
        'workers.cpm_engine'
    ]
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

if __name__ == '__main__':
    celery_app.start()
