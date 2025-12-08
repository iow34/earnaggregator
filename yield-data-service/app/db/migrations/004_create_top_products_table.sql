-- Створення таблиці top_products для зберігання TOP 10 трендових монет
-- Дані оновлюються з CoinGecko, доповнені найкращим flexible APY з yield_products

CREATE TABLE IF NOT EXISTS top_products (
    id SERIAL PRIMARY KEY,
    rank INTEGER NOT NULL CHECK (rank >= 1 AND rank <= 10),
    symbol VARCHAR(20) NOT NULL,
    coin_name VARCHAR(100),
    market_cap_rank INTEGER,
    best_apy DECIMAL(10,4) DEFAULT 0.0,
    best_exchange VARCHAR(50),
    product_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Унікальний запис на кожну позицію
ALTER TABLE top_products
    ADD CONSTRAINT unique_top_products_rank UNIQUE (rank);

-- Індекси
CREATE INDEX IF NOT EXISTS idx_top_products_rank ON top_products(rank);
CREATE INDEX IF NOT EXISTS idx_top_products_symbol ON top_products(symbol);
CREATE INDEX IF NOT EXISTS idx_top_products_updated_at ON top_products(updated_at);

-- Тригер для автооновлення updated_at
CREATE OR REPLACE FUNCTION update_top_products_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_top_products_updated_at
    BEFORE UPDATE ON top_products
    FOR EACH ROW
    EXECUTE FUNCTION update_top_products_updated_at();

