from workers.celery_app import celery_app

@celery_app.task(name='workers.positioning.test_fragmentation')
def test_fragmentation(alert_id: int):
    """
    Voos de Posicionamento (Positioning Flights):
    Testa a fragmentação. 
    Exemplo: voar do aeroporto do utilizador para o Nordeste do Brasil
    de forma a aceder aos "Sweet Spots" da Iberia com destino à Europa.
    
    Aplica o Anti-Pattern 'Restrição Geográfica Absoluta' pesquisando 
    em aeroportos vizinhos/alternativos e rotas de posicionamento.
    """
    pass
