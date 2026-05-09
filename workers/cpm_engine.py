from workers.celery_app import celery_app

@celery_app.task(name='workers.cpm_engine.calculate_cpm')
def calculate_cpm(user_id: int, program_name: str):
    """
    Motor de Custo Fiduciário e Arbitragem (CPM Engine):
    Calcula o Custo Por Milheiro em tempo real.
    Suporta a simulação de promoções de transferência (ex: Bônus 100%).
    Atualiza a `MileWallet` correspondente.
    """
    pass
