"""
SQLAlchemy моделі для бази даних.

Цей модуль визначає структуру таблиць PostgreSQL
для зберігання даних про Yield продукти.
"""

from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean, DateTime, Text, 
    ForeignKey, Index, JSON
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, UTC

# Базовий клас для всіх моделей
Base = declarative_base()


class YieldProductDB(Base):
    """
    Таблиця для зберігання Yield продуктів.
    
    Основна таблиця для зберігання нормалізованих даних
    про всі Yield продукти з усіх бірж.
    """
    __tablename__ = "yield_products"
    
    # Первинний ключ
    id = Column(String(100), primary_key=True, comment="Унікальний ідентифікатор продукту")
    
    # Основні дані
    symbol = Column(String(20), nullable=False, index=True, comment="Символ токену (BTC, ETH)")
    name = Column(String(200), nullable=False, comment="Назва продукту")
    provider = Column(String(50), nullable=False, index=True, comment="Провайдер (Binance, Bybit)")
    apy = Column(Float, nullable=False, index=True, comment="APY у відсотках")
    is_cefi = Column(Boolean, default=True, comment="CeFi чи DeFi")
    
    # Фінансові параметри
    min_amount = Column(Float, default=0.0, comment="Мінімальна сума")
    max_amount = Column(Float, nullable=True, comment="Максимальна сума")
    lock_period_days = Column(Integer, default=0, comment="Період блокування в днях")
    
    # Додаткові поля
    max_apy = Column(Float, nullable=True, comment="Максимальний APY")
    risk_level = Column(String(20), default="Medium", comment="Рівень ризику")
    is_active = Column(Boolean, default=True, index=True, comment="Активний продукт")
    website_url = Column(String(500), nullable=True, comment="Посилання на платформу")
    description = Column(Text, nullable=True, comment="Опис продукту")
    product_type = Column(String(50), nullable=True, comment="Тип продукту (Flexible, Fixed, Bonded)")
    
    # Часові мітки
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час створення")
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час оновлення")
    last_checked = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час останньої перевірки")
    
    # Сирі дані з API
    raw_data = Column(JSON, nullable=True, comment="Сирі дані з API біржі")
    
    # Зв'язки
    exchange_data = relationship("ExchangeDataDB", back_populates="product", cascade="all, delete-orphan")
    
    # Індекси для оптимізації
    __table_args__ = (
        Index('idx_symbol_apy', 'symbol', 'apy'),
        Index('idx_provider_active', 'provider', 'is_active'),
        Index('idx_apy_desc', 'apy', postgresql_using='btree'),
        Index('idx_created_at', 'created_at'),
        Index('idx_updated_at', 'updated_at'),
        Index('idx_last_checked', 'last_checked'),
    )
    
    def __repr__(self):
        return f"<YieldProductDB(id='{self.id}', symbol='{self.symbol}', provider='{self.provider}', apy={self.apy})>"


class ExchangeDataDB(Base):
    """
    Таблиця для зберігання сирих даних з API бірж.
    
    Зберігає оригінальні дані з API для аналізу та дебагу.
    """
    __tablename__ = "exchange_data"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ідентифікатор")
    
    # Зв'язок з продуктом
    product_id = Column(String(100), ForeignKey("yield_products.id", ondelete="CASCADE"), nullable=False, comment="ID продукту")
    
    # Дані з біржі
    exchange = Column(String(50), nullable=False, index=True, comment="Назва біржі")
    raw_data = Column(JSON, nullable=False, comment="Сирі дані з API")
    api_endpoint = Column(String(200), nullable=True, comment="API endpoint")
    
    # Метадані запиту
    request_timestamp = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час запиту")
    response_status = Column(Integer, nullable=True, comment="HTTP статус відповіді")
    response_time_ms = Column(Integer, nullable=True, comment="Час відповіді в мілісекундах")
    
    # Зв'язки
    product = relationship("YieldProductDB", back_populates="exchange_data")

    # Індекси та обмеження
    __table_args__ = (
        # Унікальний індекс - тільки один запис на продукт + біржу
        Index('idx_exchange_timestamp', 'exchange', 'request_timestamp'),
        Index('idx_product_exchange', 'product_id', 'exchange'),
        Index('idx_response_status', 'response_status'),
        Index('idx_request_timestamp', 'request_timestamp'),
        # Унікальне обмеження для запобігання дублям
        Index('unique_product_exchange', 'product_id', 'exchange', unique=True),
    )
    
    def __repr__(self):
        return f"<ExchangeDataDB(id={self.id}, exchange='{self.exchange}', product_id='{self.product_id}')>"


class CacheMetadataDB(Base):
    """
    Таблиця для метаданих кешу.
    
    Відстежує стан кешу та оптимізує оновлення.
    """
    __tablename__ = "cache_metadata"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ідентифікатор")
    
    # Ключ кешу
    cache_key = Column(String(200), unique=True, nullable=False, index=True, comment="Ключ кешу")
    cache_type = Column(String(50), nullable=False, index=True, comment="Тип кешу")
    
    # Метадані кешу
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час створення")
    expires_at = Column(DateTime, nullable=False, index=True, comment="Час закінчення")
    last_accessed = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час останнього доступу")
    access_count = Column(Integer, default=0, comment="Кількість доступів")
    
    # Статистика
    hit_count = Column(Integer, default=0, comment="Кількість попадань")
    miss_count = Column(Integer, default=0, comment="Кількість промахів")
    data_size_bytes = Column(Integer, nullable=True, comment="Розмір даних в байтах")
    
    # Індекси
    __table_args__ = (
        Index('idx_cache_expires', 'expires_at'),
        Index('idx_cache_type', 'cache_type'),
        Index('idx_last_accessed', 'last_accessed'),
        Index('idx_cache_key_type', 'cache_key', 'cache_type'),
    )
    
    def __repr__(self):
        return f"<CacheMetadataDB(id={self.id}, cache_key='{self.cache_key}', type='{self.cache_type}')>"


class UserAnalyticsDB(Base):
    """
    Таблиця для аналітики користувачів.
    
    Відстежує популярність продуктів та користувацьку поведінку.
    """
    __tablename__ = "user_analytics"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ідентифікатор")
    
    # Дані користувача
    user_id = Column(String(100), nullable=False, index=True, comment="ID користувача (Telegram ID)")
    session_id = Column(String(100), nullable=True, comment="ID сесії")
    
    # Дія користувача
    action_type = Column(String(50), nullable=False, index=True, comment="Тип дії")
    symbol = Column(String(10), nullable=True, index=True, comment="Символ токену")
    provider = Column(String(50), nullable=True, index=True, comment="Провайдер")
    
    # Метадані
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True, comment="Час дії")
    ip_address = Column(String(45), nullable=True, comment="IP адреса")
    user_agent = Column(String(500), nullable=True, comment="User Agent")
    
    # Індекси
    __table_args__ = (
        Index('idx_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_action_type', 'action_type', 'timestamp'),
        Index('idx_symbol_provider', 'symbol', 'provider'),
        Index('idx_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<UserAnalyticsDB(id={self.id}, user_id='{self.user_id}', action='{self.action_type}')>"


class SystemMetricsDB(Base):
    """
    Таблиця для системних метрик.
    
    Зберігає метрики продуктивності та моніторингу.
    """
    __tablename__ = "system_metrics"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ідентифікатор")
    
    # Метадані метрики
    metric_name = Column(String(100), nullable=False, index=True, comment="Назва метрики")
    metric_type = Column(String(50), nullable=False, comment="Тип метрики")
    value = Column(Float, nullable=False, comment="Значення метрики")
    unit = Column(String(20), nullable=True, comment="Одиниця вимірювання")
    
    # Метадані
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True, comment="Час метрики")
    tags = Column(JSON, nullable=True, comment="Теги метрики")
    
    # Індекси
    __table_args__ = (
        Index('idx_metric_name_timestamp', 'metric_name', 'timestamp'),
        Index('idx_metric_type', 'metric_type'),
        Index('idx_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<SystemMetricsDB(id={self.id}, metric='{self.metric_name}', value={self.value})>"


class CoinsPopularityDB(Base):
    """
    Таблиця для зберігання рейтингу популярності монет з CoinGecko API.

    Відповідно до ТЗ: Сортування продуктів у Telegram-боті за параметром "Популярні"
    """
    __tablename__ = "coins_popularity"

    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ідентифікатор")

    # Дані з CoinGecko API
    coin_id = Column(String(100), unique=True, nullable=False, comment="ID монети в CoinGecko (bitcoin, ethereum)")
    symbol = Column(String(20), unique=True, nullable=False, index=True, comment="Тикер монети в верхньому регістрі (BTC, ETH)")
    name = Column(String(100), nullable=False, comment="Повна назва монети")

    # Рейтинг популярності
    market_cap_rank = Column(Integer, nullable=False, index=True, comment="Рейтинг за ринковою капіталізацією (1 = найпопулярніша)")

    # Додаткові дані з CoinGecko
    current_price = Column(Float, nullable=True, comment="Поточна ціна в USD")
    market_cap = Column(Float, nullable=True, comment="Ринкова капіталізація")

    # Часові мітки
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час створення запису")
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час останнього оновлення")

    # Обмеження
    __table_args__ = (
        Index('idx_coins_popularity_rank', 'market_cap_rank'),
        Index('idx_coins_popularity_symbol', 'symbol'),
        Index('idx_coins_popularity_updated', 'updated_at'),
    )

    def __repr__(self):
        return f"<CoinsPopularityDB(id={self.id}, symbol='{self.symbol}', rank={self.market_cap_rank})>"


class APILogsDB(Base):
    """
    Таблиця для логів API запитів.

    Зберігає детальну інформацію про всі API запити.
    """
    __tablename__ = "api_logs"

    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ідентифікатор")

    # Метадані запиту
    request_id = Column(String(100), nullable=False, index=True, comment="ID запиту")
    endpoint = Column(String(200), nullable=False, comment="API endpoint")
    method = Column(String(10), nullable=False, comment="HTTP метод")
    status_code = Column(Integer, nullable=False, comment="HTTP статус")

    # Час виконання
    request_time = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час запиту")
    response_time = Column(DateTime, nullable=True, comment="Час відповіді")
    duration_ms = Column(Integer, nullable=True, comment="Тривалість в мілісекундах")

    # Метадані
    user_id = Column(String(100), nullable=True, comment="ID користувача")
    ip_address = Column(String(45), nullable=True, comment="IP адреса")
    user_agent = Column(String(500), nullable=True, comment="User Agent")

    # Індекси
    __table_args__ = (
        Index('idx_request_id', 'request_id'),
        Index('idx_endpoint', 'endpoint'),
        Index('idx_status_code', 'status_code'),
        Index('idx_request_time', 'request_time'),
        Index('idx_user_id', 'user_id'),
    )

    def __repr__(self):
        return f"<APILogsDB(id={self.id}, endpoint='{self.endpoint}', status={self.status_code})>"


class PriorityProductDB(Base):
    """
    Таблиця для зберігання основних продуктів (BTC, ETH, SOL, USDT) по біржах.
    
    Оптимізована таблиця для швидкого доступу до основних продуктів
    на сторінці 1 телеграм бота. Завжди містить 4 продукти для кожної біржі.
    """
    __tablename__ = "priority_products"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ідентифікатор")
    
    # Основні дані
    exchange = Column(String(50), nullable=False, index=True, comment="Назва біржі (binance, bybit)")
    symbol = Column(String(20), nullable=False, index=True, comment="Символ токену (BTC, ETH, SOL, USDT)")
    apy = Column(Float, nullable=False, default=0.0, comment="APY у відсотках")
    is_active = Column(Boolean, default=True, index=True, comment="Чи активний продукт")
    
    # Зв'язок з основною таблицею
    product_id = Column(String(100), nullable=True, comment="ID продукту з yield_products (для зв'язку)")
    lock_period_days = Column(Integer, default=0, comment="Період блокування в днях (0 = Flexible)")
    
    # Часові мітки
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час створення")
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час оновлення")
    
    # Індекси та обмеження
    __table_args__ = (
        Index('idx_priority_exchange_symbol', 'exchange', 'symbol'),
        Index('idx_priority_exchange', 'exchange'),
        Index('idx_priority_symbol', 'symbol'),
        Index('idx_priority_updated_at', 'updated_at'),
        # Унікальне обмеження - один запис на біржу + символ
        Index('unique_priority_exchange_symbol', 'exchange', 'symbol', unique=True),
    )
    
    def __repr__(self):
        return f"<PriorityProductDB(id={self.id}, exchange='{self.exchange}', symbol='{self.symbol}', apy={self.apy})>"


class TopProductDB(Base):
    """
    Таблиця TOP 10 трендових монет з CoinGecko + найкращий flexible APY по біржах.
    """
    __tablename__ = "top_products"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ідентифікатор")
    rank = Column(Integer, nullable=False, unique=True, comment="Позиція в топі (1-10)")
    symbol = Column(String(20), nullable=False, index=True, comment="Символ монети")
    coin_name = Column(String(100), nullable=True, comment="Назва монети")
    market_cap_rank = Column(Integer, nullable=True, comment="Ранг за ринковою капіталізацією")
    best_apy = Column(Float, nullable=False, default=0.0, comment="Найкращий flexible APY")
    best_exchange = Column(String(50), nullable=True, comment="Біржа з найкращим APY")
    product_id = Column(String(100), nullable=True, comment="ID продукту в yield_products")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час створення")
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Час оновлення")

    __table_args__ = (
        Index('idx_top_products_rank', 'rank'),
        Index('idx_top_products_symbol', 'symbol'),
        Index('idx_top_products_updated_at', 'updated_at'),
    )

    def __repr__(self):
        return f"<TopProductDB(rank={self.rank}, symbol='{self.symbol}', apy={self.best_apy})>"


# Утилітарні функції для роботи з моделями

def get_table_names():
    """Повертає список назв всіх таблиць."""
    return [
        YieldProductDB.__tablename__,
        ExchangeDataDB.__tablename__,
        CacheMetadataDB.__tablename__,
        UserAnalyticsDB.__tablename__,
        SystemMetricsDB.__tablename__,
        CoinsPopularityDB.__tablename__,
        APILogsDB.__tablename__,
        PriorityProductDB.__tablename__,
        TopProductDB.__tablename__,
        TrackingUser.__tablename__,
        TrackingClick.__tablename__,
        SimpleClick.__tablename__,
        TrackingCampaign.__tablename__,
        TrackingSession.__tablename__,
        TrackingLog.__tablename__,
    ]


def get_model_by_table_name(table_name: str):
    """Повертає модель за назвою таблиці."""
    models = {
        YieldProductDB.__tablename__: YieldProductDB,
        ExchangeDataDB.__tablename__: ExchangeDataDB,
        CacheMetadataDB.__tablename__: CacheMetadataDB,
        UserAnalyticsDB.__tablename__: UserAnalyticsDB,
        SystemMetricsDB.__tablename__: SystemMetricsDB,
        CoinsPopularityDB.__tablename__: CoinsPopularityDB,
        APILogsDB.__tablename__: APILogsDB,
        PriorityProductDB.__tablename__: PriorityProductDB,
        TopProductDB.__tablename__: TopProductDB,
        TrackingUser.__tablename__: TrackingUser,
        TrackingClick.__tablename__: TrackingClick,
        SimpleClick.__tablename__: SimpleClick,
        TrackingCampaign.__tablename__: TrackingCampaign,
        TrackingSession.__tablename__: TrackingSession,
        TrackingLog.__tablename__: TrackingLog,
    }
    return models.get(table_name)


def get_foreign_key_relationships():
    """Повертає інформацію про зв'язки між таблицями."""
    return {
        'yield_products': {
            'exchange_data': 'one-to-many'
        },
        'exchange_data': {
            'yield_products': 'many-to-one'
        }
    }


# =============================================================================
# TRACKING SYSTEM MODELS - Система трекінгу дій користувачів
# =============================================================================

class TrackingUser(Base):
    """
    Таблиця користувачів для системи трекінгу.
    
    Зберігає інформацію про користувачів з джерелами входу (deep linking).
    Використовує UUID для анонімізації та безпеки.
    """
    __tablename__ = "tracking_users"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ID")
    
    # Ідентифікатори користувача
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True, comment="Telegram ID користувача")
    user_uuid = Column(String(36), unique=True, nullable=False, index=True, comment="UUID для анонімізації")
    
    # Джерело входу
    acquisition_source = Column(String(255), nullable=False, index=True, comment="Джерело входу (ad_platform_campaignID або organic)")
    
    # Часові мітки
    joined_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False, comment="Час реєстрації")
    last_activity = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False, comment="Остання активність")
    
    # Індекси
    __table_args__ = (
        Index('idx_tracking_telegram_id', 'telegram_id'),
        Index('idx_tracking_user_uuid', 'user_uuid'),
        Index('idx_tracking_source', 'acquisition_source'),
        Index('idx_tracking_joined_at', 'joined_at'),
    )
    
    def __repr__(self):
        return f"<TrackingUser(id={self.id}, telegram_id={self.telegram_id}, uuid={self.user_uuid}, source={self.acquisition_source})>"


class TrackingClick(Base):
    """
    Таблиця кліків на реферальні посилання.
    
    Зберігає всі кліки користувачів на реферальні посилання бірж
    через redirect server для аналітики конверсій.
    """
    __tablename__ = "tracking_clicks"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ID")
    
    # UUID користувача (зв'язок з tracking_users)
    user_uuid = Column(String(36), ForeignKey("tracking_users.user_uuid", ondelete="CASCADE"), nullable=False, index=True, comment="UUID користувача")
    
    # Контекст кліку
    source = Column(String(255), nullable=False, index=True, comment="Джерело входу користувача")
    page = Column(String(50), nullable=False, index=True, comment="Сторінка бота (1=головна, 2=продукти, N=список бірж)")
    exchange = Column(String(100), nullable=False, index=True, comment="Назва біржі (lowercase)")
    
    # Часова мітка
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False, index=True, comment="Час кліку")
    
    # Технічні дані
    ip_address = Column(String(45), nullable=True, comment="IP адреса користувача (IPv4/IPv6)")
    user_agent = Column(Text, nullable=True, comment="User Agent браузера")
    ref_code = Column(String(100), nullable=True, comment="Реферальний код біржі")
    
    # Індекси для аналітики
    __table_args__ = (
        Index('idx_tracking_click_uuid', 'user_uuid'),
        Index('idx_tracking_click_source', 'source'),
        Index('idx_tracking_click_page', 'page'),
        Index('idx_tracking_click_exchange', 'exchange'),
        Index('idx_tracking_click_timestamp', 'timestamp'),
        Index('idx_tracking_click_source_exchange', 'source', 'exchange'),
        Index('idx_tracking_click_page_exchange', 'page', 'exchange'),
    )
    
    def __repr__(self):
        return f"<TrackingClick(id={self.id}, uuid={self.user_uuid}, exchange={self.exchange}, page={self.page})>"


class SimpleClick(Base):
    """
    Спрощена таблиця для трекінгу кліків без UUID.
    
    Використовує telegram_id напряму для простого та надійного трекінгу.
    Не потребує попередньої реєстрації користувача.
    """
    __tablename__ = "simple_clicks"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ID")
    
    # Telegram ID користувача (без Foreign Key для простоти)
    telegram_id = Column(BigInteger, nullable=False, index=True, comment="Telegram ID користувача")
    
    # Контекст кліку
    source = Column(String(255), nullable=False, default='organic', index=True, comment="Джерело входу")
    page = Column(String(50), nullable=False, index=True, comment="Сторінка бота (1=головна, 2=продукти, 3=список бірж)")
    exchange = Column(String(100), nullable=False, index=True, comment="Назва біржі (lowercase)")
    
    # Часова мітка
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False, index=True, comment="Час кліку")
    
    # Технічні дані
    ip_address = Column(String(45), nullable=True, comment="IP адреса користувача (IPv4/IPv6)")
    user_agent = Column(Text, nullable=True, comment="User Agent браузера")
    ref_code = Column(String(100), nullable=True, comment="Реферальний код біржі")
    
    # Індекси для аналітики
    __table_args__ = (
        Index('idx_simple_click_telegram_id', 'telegram_id'),
        Index('idx_simple_click_source', 'source'),
        Index('idx_simple_click_page', 'page'),
        Index('idx_simple_click_exchange', 'exchange'),
        Index('idx_simple_click_timestamp', 'timestamp'),
        Index('idx_simple_click_source_exchange', 'source', 'exchange'),
        Index('idx_simple_click_page_exchange', 'page', 'exchange'),
        Index('idx_simple_click_telegram_exchange', 'telegram_id', 'exchange'),
    )
    
    def __repr__(self):
        return f"<SimpleClick(id={self.id}, telegram_id={self.telegram_id}, exchange={self.exchange}, page={self.page})>"


class TrackingCampaign(Base):
    """
    Таблиця рекламних кампаній.
    
    Зберігає інформацію про рекламні кампанії для трекінгу ефективності.
    """
    __tablename__ = "tracking_campaigns"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ID")
    
    # Ідентифікатор кампанії
    campaign_id = Column(String(100), unique=True, nullable=False, index=True, comment="ID кампанії (nov2025_123)")
    platform = Column(String(50), nullable=False, index=True, comment="Платформа (xcom, telegram_ads, website_banner)")
    
    # Період дії
    start_date = Column(DateTime, nullable=False, comment="Дата початку кампанії")
    end_date = Column(DateTime, nullable=True, comment="Дата закінчення кампанії (NULL = активна)")
    
    # Опис
    description = Column(Text, nullable=True, comment="Опис кампанії для аналітики")
    
    # Метрики
    total_users = Column(Integer, default=0, comment="Загальна кількість користувачів з кампанії")
    total_clicks = Column(Integer, default=0, comment="Загальна кількість кліків від користувачів кампанії")
    
    # Часові мітки
    created_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False, comment="Час створення запису")
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False, comment="Час оновлення")
    
    # Індекси
    __table_args__ = (
        Index('idx_tracking_campaign_id', 'campaign_id'),
        Index('idx_tracking_campaign_platform', 'platform'),
        Index('idx_tracking_campaign_dates', 'start_date', 'end_date'),
    )
    
    def __repr__(self):
        return f"<TrackingCampaign(id={self.id}, campaign_id={self.campaign_id}, platform={self.platform})>"


class TrackingSession(Base):
    """
    Таблиця сесій користувачів.
    
    Групує дії користувачів в сесії для аналізу поведінки.
    """
    __tablename__ = "tracking_sessions"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ID")
    
    # UUID користувача
    user_uuid = Column(String(36), ForeignKey("tracking_users.user_uuid", ondelete="CASCADE"), nullable=False, index=True, comment="UUID користувача")
    
    # ID сесії
    session_id = Column(String(36), unique=True, nullable=False, index=True, comment="UUID сесії")
    
    # Контекст сесії
    source = Column(String(255), nullable=False, comment="Джерело входу користувача")
    
    # Часові мітки
    session_start = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False, comment="Початок сесії")
    session_end = Column(DateTime, nullable=True, comment="Кінець сесії")
    
    # Метрики сесії
    total_clicks = Column(Integer, default=0, comment="Кількість кліків в сесії")
    total_time = Column(Integer, default=0, comment="Загальний час сесії в секундах")
    
    # Індекси
    __table_args__ = (
        Index('idx_tracking_session_uuid', 'user_uuid'),
        Index('idx_tracking_session_id', 'session_id'),
        Index('idx_tracking_session_start', 'session_start'),
    )
    
    def __repr__(self):
        return f"<TrackingSession(id={self.id}, session_id={self.session_id}, clicks={self.total_clicks})>"


class TrackingLog(Base):
    """
    Таблиця логів системи трекінгу.
    
    Зберігає логи помилок та попереджень для моніторингу системи трекінгу.
    """
    __tablename__ = "tracking_logs"
    
    # Первинний ключ
    id = Column(Integer, primary_key=True, autoincrement=True, comment="Унікальний ID")
    
    # Тип події
    event_type = Column(String(50), nullable=False, index=True, comment="Тип події (error, warning, info)")
    
    # Повідомлення
    message = Column(Text, nullable=False, comment="Текст повідомлення")
    
    # Додаткові дані
    user_uuid = Column(String(36), nullable=True, index=True, comment="UUID користувача (якщо застосовно)")
    context = Column(JSON, nullable=True, comment="Додатковий контекст (JSON)")
    
    # Часова мітка
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False, index=True, comment="Час події")
    
    # Індекси
    __table_args__ = (
        Index('idx_tracking_log_type', 'event_type'),
        Index('idx_tracking_log_uuid', 'user_uuid'),
        Index('idx_tracking_log_timestamp', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<TrackingLog(id={self.id}, type={self.event_type}, timestamp={self.timestamp})>"
