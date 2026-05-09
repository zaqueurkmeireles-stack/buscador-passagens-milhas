from workers.celery_app import celery_app

@celery_app.task(name='workers.golden_windows.monitor_cash_tickets')
def monitor_cash_tickets(alert_id: int):
    """
    Monitorização de Janelas de Ouro (Dinheiro / Cash Tickets):
    Intensifica requisições apenas nos períodos estatísticos:
    - Voos Nacionais (Baixa): 40-25 dias.
    - Voos Nacionais (Alta): 90-60 dias.
    - Voos Int. (Baixa): 60-30 dias.
    - Voos Int. (Alta): 120-60 dias.
    
    Aplica o Anti-Pattern 'Compra Antecipada Cega' ignorando viagens > 11 meses.
    Aplica o Anti-Pattern 'Zona de Risco' ignorando viagens < 15 dias.
    """
    pass
