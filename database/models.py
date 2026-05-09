from sqlalchemy import Column, Integer, String, Float, DateTime, BigInteger, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class User(Base):
    """Modelo para representar os utilizadores interagindo com o bot."""
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    name = Column(String, nullable=True)
    
    wallets = relationship("MileWallet", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("SearchAlert", back_populates="user", cascade="all, delete-orphan")

class SearchAlert(Base):
    """Modelo para rastrear os alertas e intenções de busca."""
    __tablename__ = 'search_alerts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Array Macro-para-Micro e Open Jaw (Múltiplas Origens e Destinos)
    origins = Column(ARRAY(String), nullable=False)
    destinations = Column(ARRAY(String), nullable=False)
    
    # Datas da busca (Sniper de Calendário ou Janelas de Ouro)
    date_start = Column(DateTime, nullable=False)
    date_end = Column(DateTime, nullable=False)
    
    # Lógica Bidirecional: Is Award vs Is Cash
    is_award = Column(Boolean, default=False, nullable=False)
    is_cash = Column(Boolean, default=True, nullable=False)
    
    # Anti-Pattern: Pesquisa em Bloco. Default é sempre 1 passageiro adulto.
    adults = Column(Integer, default=1, nullable=False)
    
    # Motor de Custo Fiduciário
    target_price_fiat = Column(Float, nullable=True) # Preço máximo fiduciário aceitável (já com mala e taxas)
    target_cpm = Column(Float, nullable=True) # CPM máximo aceitável se for Award
    
    # Anti-Patterns Flags (Marcadores para ignorar buscas)
    ignore_last_minute_cash = Column(Boolean, default=True, nullable=False) # Evita janela < 15 dias para pagantes
    ignore_advanced_cash = Column(Boolean, default=True, nullable=False) # Evita janela > 11 meses para pagantes
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="alerts")
    results = relationship("FlightResult", back_populates="alert", cascade="all, delete-orphan")

class FlightResult(Base):
    """
    Motor de Custo Real e Bagagem: Resultado processado pelas rotinas de Playwright.
    Só salva os resultados após ir ao fundo do funil e extrair todos os custos.
    """
    __tablename__ = 'flight_results'
    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey('search_alerts.id'), nullable=False)
    
    airline = Column(String, nullable=False)
    origin = Column(String, nullable=False)  # IATA
    destination = Column(String, nullable=False) # IATA
    departure_time = Column(DateTime, nullable=False)
    arrival_time = Column(DateTime, nullable=False)
    
    # Flags Bidirecionais
    is_award = Column(Boolean, default=False, nullable=False)
    is_cash = Column(Boolean, default=True, nullable=False)
    
    # Motor de Custo Real e Bagagem
    base_price = Column(Float, default=0.0)      # Tarifa nua
    baggage_price = Column(Float, default=0.0)   # Preço real da mala (cabine/porão) raspado do funil
    boarding_taxes = Column(Float, default=0.0)  # Taxas de embarque
    
    # Arbitragem de Milhas
    miles_required = Column(Integer, nullable=True)
    cpm_used = Column(Float, nullable=True)      # Snapshot do CPM no momento do cálculo
    
    # Anti-Pattern: Falso Alerta de Low-Cost resolvido pela soma matemática
    # Para Award = (miles_required / 1000 * cpm_used) + boarding_taxes
    # Para Cash = base_price + baggage_price + boarding_taxes
    total_fiat_cost = Column(Float, nullable=False) 
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    alert = relationship("SearchAlert", back_populates="results")

class MileWallet(Base):
    """Arbitragem de Milhas (CPM Engine): Registo de saldos e cálculo do CPM em tempo real."""
    __tablename__ = 'mile_wallets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    program_name = Column(String, nullable=False)
    balance = Column(Integer, nullable=False)
    
    # Custo Por Milheiro em tempo real (atualizado na Wallet para suportar simulação de transferência)
    current_cpm = Column(Float, nullable=False, default=0.0)
    
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="wallets")
