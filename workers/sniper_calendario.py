from workers.celery_app import celery_app
from database.models import SearchAlert
# import sqlalchemy session etc.

@celery_app.task(name='workers.sniper_calendario.scan_330_days')
def scan_330_days(alert_id: int):
    """
    Sniper de Calendário (Milhas / Award):
    Exclusivo para emissões com milhas (principalmente Executiva).
    Varre os calendários com 330 a 360 dias de antecedência 
    para capturar o inventário restrito assim que este é libertado.
    """
    pass
