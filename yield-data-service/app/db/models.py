from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, UTC


Base = declarative_base()


class YieldProductDB(Base):
    __tablename__ = "yield_products"

    id = Column(String(100), primary_key=True, comment="Id")

    symbol = Column(String(20), nullable=False, index=True, comment="Symbol")
    name = Column(String(200), nullable=False, comment="Name")
    provider = Column(String(50), nullable=False, index=True, comment="Provider")
    apy = Column(Float, nullable=False, index=True, comment="Apy")
    is_cefi = Column(Boolean, default=True, comment="Is cefi")

    min_amount = Column(Float, default=0.0, comment="Min amount")
    max_amount = Column(Float, nullable=True, comment="Max amount")
    lock_period_days = Column(Integer, default=0, comment="Lock period days")

    max_apy = Column(Float, nullable=True, comment="Max apy")
    risk_level = Column(String(20), default="Medium", comment="Risk level")
    is_active = Column(Boolean, default=True, index=True, comment="Is active")
    website_url = Column(String(500), nullable=True, comment="Website url")
    description = Column(Text, nullable=True, comment="Description")
    product_type = Column(String(50), nullable=True, comment="Product type")

    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Created at"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="Updated at",
    )
    last_checked = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Last checked"
    )

    raw_data = Column(JSON, nullable=True, comment="Raw data")

    exchange_data = relationship(
        "ExchangeDataDB", back_populates="product", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_symbol_apy", "symbol", "apy"),
        Index("idx_provider_active", "provider", "is_active"),
        Index("idx_apy_desc", "apy", postgresql_using="btree"),
        Index("idx_created_at", "created_at"),
        Index("idx_updated_at", "updated_at"),
        Index("idx_last_checked", "last_checked"),
    )

    def __repr__(self):
        return f"<YieldProductDB(id='{self.id}', symbol='{self.symbol}', provider='{self.provider}', apy={self.apy})>"


class ExchangeDataDB(Base):
    __tablename__ = "exchange_data"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    product_id = Column(
        String(100),
        ForeignKey("yield_products.id", ondelete="CASCADE"),
        nullable=False,
        comment="Product id",
    )

    exchange = Column(String(50), nullable=False, index=True, comment="Exchange")
    raw_data = Column(JSON, nullable=False, comment="Raw data")
    api_endpoint = Column(String(200), nullable=True, comment="API endpoint")

    request_timestamp = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="Request timestamp",
    )
    response_status = Column(Integer, nullable=True, comment="Response status")
    response_time_ms = Column(Integer, nullable=True, comment="Response time ms")

    product = relationship("YieldProductDB", back_populates="exchange_data")

    __table_args__ = (
        Index("idx_exchange_timestamp", "exchange", "request_timestamp"),
        Index("idx_product_exchange", "product_id", "exchange"),
        Index("idx_response_status", "response_status"),
        Index("idx_request_timestamp", "request_timestamp"),
        Index("unique_product_exchange", "product_id", "exchange", unique=True),
    )

    def __repr__(self):
        return f"<ExchangeDataDB(id={self.id}, exchange='{self.exchange}', product_id='{self.product_id}')>"


class CacheMetadataDB(Base):
    __tablename__ = "cache_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    cache_key = Column(String(200), unique=True, nullable=False, index=True, comment="Cache key")
    cache_type = Column(String(50), nullable=False, index=True, comment="Cache type")

    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Created at"
    )
    expires_at = Column(DateTime, nullable=False, index=True, comment="Expires at")
    last_accessed = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Last accessed"
    )
    access_count = Column(Integer, default=0, comment="Access count")

    hit_count = Column(Integer, default=0, comment="Hit count")
    miss_count = Column(Integer, default=0, comment="Miss count")
    data_size_bytes = Column(Integer, nullable=True, comment="Data size bytes")

    __table_args__ = (
        Index("idx_cache_expires", "expires_at"),
        Index("idx_cache_type", "cache_type"),
        Index("idx_last_accessed", "last_accessed"),
        Index("idx_cache_key_type", "cache_key", "cache_type"),
    )

    def __repr__(self):
        return f"<CacheMetadataDB(id={self.id}, cache_key='{self.cache_key}', type='{self.cache_type}')>"


class UserAnalyticsDB(Base):
    __tablename__ = "user_analytics"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    user_id = Column(String(100), nullable=False, index=True, comment="User id")
    session_id = Column(String(100), nullable=True, comment="Session id")

    action_type = Column(String(50), nullable=False, index=True, comment="Action type")
    symbol = Column(String(10), nullable=True, index=True, comment="Symbol")
    provider = Column(String(50), nullable=True, index=True, comment="Provider")

    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        index=True,
        comment="Timestamp",
    )
    ip_address = Column(String(45), nullable=True, comment="Ip address")
    user_agent = Column(String(500), nullable=True, comment="User Agent")

    __table_args__ = (
        Index("idx_user_timestamp", "user_id", "timestamp"),
        Index("idx_action_type", "action_type", "timestamp"),
        Index("idx_symbol_provider", "symbol", "provider"),
        Index("idx_user_analytics_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<UserAnalyticsDB(id={self.id}, user_id='{self.user_id}', action='{self.action_type}')>"


class SystemMetricsDB(Base):
    __tablename__ = "system_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    metric_name = Column(String(100), nullable=False, index=True, comment="Metric name")
    metric_type = Column(String(50), nullable=False, comment="Metric type")
    value = Column(Float, nullable=False, comment="Value")
    unit = Column(String(20), nullable=True, comment="Unit")

    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        index=True,
        comment="Timestamp",
    )
    tags = Column(JSON, nullable=True, comment="Tags")

    __table_args__ = (
        Index("idx_metric_name_timestamp", "metric_name", "timestamp"),
        Index("idx_metric_type", "metric_type"),
        Index("idx_system_metrics_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<SystemMetricsDB(id={self.id}, metric='{self.metric_name}', value={self.value})>"


class CoinsPopularityDB(Base):
    __tablename__ = "coins_popularity"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    coin_id = Column(String(100), unique=True, nullable=False, comment="Coin id")
    symbol = Column(String(20), unique=True, nullable=False, index=True, comment="Symbol")
    name = Column(String(100), nullable=False, comment="Name")

    market_cap_rank = Column(Integer, nullable=False, index=True, comment="Market cap rank")

    current_price = Column(Float, nullable=True, comment="Current price")
    market_cap = Column(Float, nullable=True, comment="Market cap")

    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Created at"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="Updated at",
    )

    __table_args__ = (
        Index("idx_coins_popularity_rank", "market_cap_rank"),
        Index("idx_coins_popularity_symbol", "symbol"),
        Index("idx_coins_popularity_updated", "updated_at"),
    )

    def __repr__(self):
        return f"<CoinsPopularityDB(id={self.id}, symbol='{self.symbol}', rank={self.market_cap_rank})>"


class APILogsDB(Base):
    __tablename__ = "api_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    request_id = Column(String(100), nullable=False, index=True, comment="Request id")
    endpoint = Column(String(200), nullable=False, comment="API endpoint")
    method = Column(String(10), nullable=False, comment="Method")
    status_code = Column(Integer, nullable=False, comment="Status code")

    request_time = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Request time"
    )
    response_time = Column(DateTime, nullable=True, comment="Response time")
    duration_ms = Column(Integer, nullable=True, comment="Duration ms")

    user_id = Column(String(100), nullable=True, comment="User id")
    ip_address = Column(String(45), nullable=True, comment="Ip address")
    user_agent = Column(String(500), nullable=True, comment="User Agent")

    __table_args__ = (
        Index("idx_request_id", "request_id"),
        Index("idx_endpoint", "endpoint"),
        Index("idx_status_code", "status_code"),
        Index("idx_request_time", "request_time"),
        Index("idx_user_id", "user_id"),
    )

    def __repr__(self):
        return f"<APILogsDB(id={self.id}, endpoint='{self.endpoint}', status={self.status_code})>"


class PriorityProductDB(Base):
    __tablename__ = "priority_products"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    exchange = Column(String(50), nullable=False, index=True, comment="Exchange")
    symbol = Column(String(20), nullable=False, index=True, comment="Symbol")
    apy = Column(Float, nullable=False, default=0.0, comment="Apy")
    is_active = Column(Boolean, default=True, index=True, comment="Is active")

    product_id = Column(String(100), nullable=True, comment="Product id")
    lock_period_days = Column(Integer, default=0, comment="Lock period days")

    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Created at"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="Updated at",
    )

    __table_args__ = (
        Index("idx_priority_exchange_symbol", "exchange", "symbol"),
        Index("idx_priority_exchange", "exchange"),
        Index("idx_priority_symbol", "symbol"),
        Index("idx_priority_updated_at", "updated_at"),
        Index("unique_priority_exchange_symbol", "exchange", "symbol", unique=True),
    )

    def __repr__(self):
        return f"<PriorityProductDB(id={self.id}, exchange='{self.exchange}', symbol='{self.symbol}', apy={self.apy})>"


class TopProductDB(Base):
    __tablename__ = "top_products"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")
    rank = Column(Integer, nullable=False, unique=True, comment="Rank")
    symbol = Column(String(20), nullable=False, index=True, comment="Symbol")
    coin_name = Column(String(100), nullable=True, comment="Coin name")
    market_cap_rank = Column(Integer, nullable=True, comment="Market cap rank")
    best_apy = Column(Float, nullable=False, default=0.0, comment="Best apy")
    best_exchange = Column(String(50), nullable=True, comment="Best exchange")
    product_id = Column(String(100), nullable=True, comment="Product id")
    created_at = Column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), comment="Created at"
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        comment="Updated at",
    )

    __table_args__ = (
        Index("idx_top_products_rank", "rank"),
        Index("idx_top_products_symbol", "symbol"),
        Index("idx_top_products_updated_at", "updated_at"),
    )

    def __repr__(self):
        return f"<TopProductDB(rank={self.rank}, symbol='{self.symbol}', apy={self.best_apy})>"


def get_table_names():
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
    return {
        "yield_products": {"exchange_data": "one-to-many"},
        "exchange_data": {"yield_products": "many-to-one"},
    }


# =============================================================================

# =============================================================================


class TrackingUser(Base):
    __tablename__ = "tracking_users"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True, comment="Telegram id")
    user_uuid = Column(String(36), unique=True, nullable=False, index=True, comment="User uuid")

    acquisition_source = Column(
        String(255), nullable=False, index=True, comment="Acquisition source"
    )

    joined_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        comment="Joined at",
    )
    last_activity = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        comment="Last activity",
    )

    __table_args__ = (
        Index("idx_tracking_telegram_id", "telegram_id"),
        Index("idx_tracking_user_uuid", "user_uuid"),
        Index("idx_tracking_source", "acquisition_source"),
        Index("idx_tracking_joined_at", "joined_at"),
    )

    def __repr__(self):
        return f"<TrackingUser(id={self.id}, telegram_id={self.telegram_id}, uuid={self.user_uuid}, source={self.acquisition_source})>"


class TrackingClick(Base):
    __tablename__ = "tracking_clicks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    user_uuid = Column(
        String(36),
        ForeignKey("tracking_users.user_uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User uuid",
    )

    source = Column(String(255), nullable=False, index=True, comment="Source")
    page = Column(String(50), nullable=False, index=True, comment="Page")
    exchange = Column(String(100), nullable=False, index=True, comment="Exchange")

    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        index=True,
        comment="Timestamp",
    )

    ip_address = Column(String(45), nullable=True, comment="Ip address")
    user_agent = Column(Text, nullable=True, comment="User agent")
    ref_code = Column(String(100), nullable=True, comment="Ref code")

    __table_args__ = (
        Index("idx_tracking_click_uuid", "user_uuid"),
        Index("idx_tracking_click_source", "source"),
        Index("idx_tracking_click_page", "page"),
        Index("idx_tracking_click_exchange", "exchange"),
        Index("idx_tracking_click_timestamp", "timestamp"),
        Index("idx_tracking_click_source_exchange", "source", "exchange"),
        Index("idx_tracking_click_page_exchange", "page", "exchange"),
    )

    def __repr__(self):
        return f"<TrackingClick(id={self.id}, uuid={self.user_uuid}, exchange={self.exchange}, page={self.page})>"


class SimpleClick(Base):
    __tablename__ = "simple_clicks"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    telegram_id = Column(BigInteger, nullable=False, index=True, comment="Telegram id")

    source = Column(String(255), nullable=False, default="organic", index=True, comment="Source")
    page = Column(String(50), nullable=False, index=True, comment="Page")
    exchange = Column(String(100), nullable=False, index=True, comment="Exchange")

    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        index=True,
        comment="Timestamp",
    )

    ip_address = Column(String(45), nullable=True, comment="Ip address")
    user_agent = Column(Text, nullable=True, comment="User agent")
    ref_code = Column(String(100), nullable=True, comment="Ref code")

    __table_args__ = (
        Index("idx_simple_click_telegram_id", "telegram_id"),
        Index("idx_simple_click_source", "source"),
        Index("idx_simple_click_page", "page"),
        Index("idx_simple_click_exchange", "exchange"),
        Index("idx_simple_click_timestamp", "timestamp"),
        Index("idx_simple_click_source_exchange", "source", "exchange"),
        Index("idx_simple_click_page_exchange", "page", "exchange"),
        Index("idx_simple_click_telegram_exchange", "telegram_id", "exchange"),
    )

    def __repr__(self):
        return f"<SimpleClick(id={self.id}, telegram_id={self.telegram_id}, exchange={self.exchange}, page={self.page})>"


class TrackingCampaign(Base):
    __tablename__ = "tracking_campaigns"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    campaign_id = Column(
        String(100), unique=True, nullable=False, index=True, comment="Campaign id"
    )
    platform = Column(String(50), nullable=False, index=True, comment="Platform")

    start_date = Column(DateTime, nullable=False, comment="Start date")
    end_date = Column(DateTime, nullable=True, comment="End date")

    description = Column(Text, nullable=True, comment="Description")

    total_users = Column(Integer, default=0, comment="Total users")
    total_clicks = Column(Integer, default=0, comment="Total clicks")

    created_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        comment="Created at",
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        comment="Updated at",
    )

    __table_args__ = (
        Index("idx_tracking_campaign_id", "campaign_id"),
        Index("idx_tracking_campaign_platform", "platform"),
        Index("idx_tracking_campaign_dates", "start_date", "end_date"),
    )

    def __repr__(self):
        return f"<TrackingCampaign(id={self.id}, campaign_id={self.campaign_id}, platform={self.platform})>"


class TrackingSession(Base):
    __tablename__ = "tracking_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    user_uuid = Column(
        String(36),
        ForeignKey("tracking_users.user_uuid", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User uuid",
    )

    session_id = Column(String(36), unique=True, nullable=False, index=True, comment="Session id")

    source = Column(String(255), nullable=False, comment="Source")

    session_start = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        comment="Session start",
    )
    session_end = Column(DateTime, nullable=True, comment="Session end")

    total_clicks = Column(Integer, default=0, comment="Total clicks")
    total_time = Column(Integer, default=0, comment="Total time")

    __table_args__ = (
        Index("idx_tracking_session_uuid", "user_uuid"),
        Index("idx_tracking_session_id", "session_id"),
        Index("idx_tracking_session_start", "session_start"),
    )

    def __repr__(self):
        return f"<TrackingSession(id={self.id}, session_id={self.session_id}, clicks={self.total_clicks})>"


class TrackingLog(Base):
    __tablename__ = "tracking_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Id")

    event_type = Column(String(50), nullable=False, index=True, comment="Event type")

    message = Column(Text, nullable=False, comment="Message")

    user_uuid = Column(String(36), nullable=True, index=True, comment="User uuid")
    context = Column(JSON, nullable=True, comment="Context")

    timestamp = Column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
        index=True,
        comment="Timestamp",
    )

    __table_args__ = (
        Index("idx_tracking_log_type", "event_type"),
        Index("idx_tracking_log_uuid", "user_uuid"),
        Index("idx_tracking_log_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<TrackingLog(id={self.id}, type={self.event_type}, timestamp={self.timestamp})>"
