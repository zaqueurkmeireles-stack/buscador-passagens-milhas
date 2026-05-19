import os
from celery import Celery
from celery.schedules import crontab, timedelta
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
        'workers.cpm_engine',
        'workers.tasks',
    ]
)

# Intervalo de verificação de arbitragem (em horas, configurado no .env)
_arbitrage_interval_h = config.ARBITRAGE_CHECK_INTERVAL_HOURS

celery_app.conf.beat_schedule = {
    # Worker de Arbitragem de Milhas (CPM Engine)
    'arbitrage-check-every-n-hours': {
        'task': 'workers.cpm_engine.run_arbitrage_check',
        'schedule': timedelta(hours=_arbitrage_interval_h),
    },
    # Sync de carteiras de milhas — diariamente às 03:00
    'sync-miles-every-day-3am': {
        'task': 'workers.tasks.sync_mileage_wallets',
        'schedule': crontab(hour=3, minute=0),
    },
}

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='America/Sao_Paulo',
    enable_utc=True,
)

if __name__ == '__main__':
    celery_app.start()
