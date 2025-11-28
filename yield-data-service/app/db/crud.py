
    @staticmethod
    async def get_products_by_symbol_and_provider(
        db: AsyncSession, 
        symbol: str, 
        provider: str
    ) -> List[YieldProductDB]:
        """
        Отримує продукти по символу та провайдеру.
        
        Args:
            db: Сесія бази даних
            symbol: Символ монети (BTC, ETH)
            provider: Провайдер (Binance, Bybit) - точна назва з БД
            
        Returns:
            List[YieldProductDB]: Список продуктів
        """
        try:
            # Використовуємо точне порівняння (без ilike) для кращої продуктивності
            # Provider в БД зберігається з великої літери (Binance, Bybit)
            result = await db.execute(
                select(YieldProductDB)
                .where(YieldProductDB.symbol == symbol.upper())
                .where(YieldProductDB.provider == provider)  # Точне порівняння
                .order_by(desc(YieldProductDB.apy))
            )
            products = result.scalars().all()
            logger.debug(
                f"🔍 get_products_by_symbol_and_provider({symbol}, {provider}): "
                f"знайдено {len(products)} продуктів"
            )
            return products
        except Exception as e:
            logger.error(f"Помилка отримання продуктів {symbol}/{provider}: {e}", exc_info=True)
            return []
