"""
Тестовий файл для перевірки реальних даних з API бірж.

Цей скрипт отримує дані про Earn продукти для топ-5 криптовалют
з Binance та Bybit і виводить їх у читабельному форматі.

Використання:
    python -m yield-data-service.tests.test_exchanges_real_data
    
    або з кореневої директорії:
    cd /Users/user777/Documents/EarnAggregator
    python -m yield-data-service.tests.test_exchanges_real_data
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Додати шлях до проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.exchanges import BinanceAPI, BybitAPI
from app.config import settings
from app.utils.logger import logger


# Топ-5 криптовалют для тестування
TEST_ASSETS = ["BTC", "ETH", "USDT", "BNB", "SOL"]


def print_separator(title: str = ""):
    """Друкує красивий роздільник."""
    if title:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    else:
        print(f"{'='*80}\n")


def print_product_summary(products: list, exchange: str):
    """
    Друкує короткий звіт про отримані продукти.
    
    Args:
        products: Список продуктів
        exchange: Назва біржі
    """
    if not products:
        print(f"❌ {exchange}: Не отримано жодного продукту")
        return
    
    print(f"✅ {exchange}: Отримано {len(products)} продуктів")
    
    # Групуємо по активу
    by_asset = {}
    for product in products:
        symbol = product.get("symbol", "Unknown")
        if symbol not in by_asset:
            by_asset[symbol] = []
        by_asset[symbol].append(product)
    
    print(f"\nРозподіл по активам:")
    for symbol, prods in sorted(by_asset.items()):
        max_apy = max(p.get("apy", 0) for p in prods)
        print(f"  • {symbol}: {len(prods)} продуктів (макс APY: {max_apy:.2f}%)")


def format_product_details(products: list, asset: str) -> str:
    """
    Форматує детальну інформацію про продукти для одного активу.
    
    Args:
        products: Список продуктів
        asset: Символ активу
        
    Returns:
        str: Відформатований текст
    """
    if not products:
        return f"Немає продуктів для {asset}"
    
    result = []
    result.append(f"\n{'─'*60}")
    result.append(f"  {asset} - знайдено {len(products)} продуктів")
    result.append(f"{'─'*60}")
    
    # Сортуємо за APY (найбільший -> найменший)
    sorted_products = sorted(products, key=lambda x: x.get("apy", 0), reverse=True)
    
    for i, product in enumerate(sorted_products[:5], 1):  # Показуємо топ-5
        apy = product.get("apy", 0)
        provider = product.get("provider", "Unknown")
        name = product.get("name", "Unknown")
        min_amount = product.get("min_amount", 0)
        lock_days = product.get("lock_period_days", 0)
        is_active = product.get("is_active", False)
        
        status = "🟢 Активний" if is_active else "🔴 Неактивний"
        lock_text = f"{lock_days} днів" if lock_days > 0 else "Flexible"
        
        result.append(f"\n{i}. {name}")
        result.append(f"   APY: {apy:.2f}%")
        result.append(f"   Провайдер: {provider}")
        result.append(f"   Мін. сума: {min_amount}")
        result.append(f"   Блокування: {lock_text}")
        result.append(f"   Статус: {status}")
    
    if len(sorted_products) > 5:
        result.append(f"\n   ... та ще {len(sorted_products) - 5} продуктів")
    
    return "\n".join(result)


async def test_binance_api():
    """
    Тестує Binance API для отримання даних по топ-5 криптовалютах.
    """
    print_separator("🟡 BINANCE API - Тестування")
    
    # Перевірка налаштувань
    if (settings.binance_api_key == "your_binance_api_key_here" or 
        not settings.binance_api_key):
        print("⚠️ УВАГА: Binance API ключі не налаштовані!")
        print("Встановіть змінні BINANCE_API_KEY та BINANCE_API_SECRET у .env файлі")
        return None
    
    logger.info("Ініціалізація Binance API клієнта...")
    binance = BinanceAPI(
        api_key=settings.binance_api_key,
        api_secret=settings.binance_api_secret
    )
    
    all_results = {}
    
    # Тестуємо кожен актив
    for asset in TEST_ASSETS:
        print(f"\n📊 Отримання даних для {asset}...")
        try:
            products = await binance.get_earn_products_by_asset(asset)
            all_results[asset] = products
            
            if products:
                print(f"   ✅ Знайдено {len(products)} продуктів")
            else:
                print(f"   ⚠️ Продуктів не знайдено")
                
        except Exception as e:
            logger.error(f"Помилка при отриманні {asset}: {e}")
            print(f"   ❌ Помилка: {e}")
            all_results[asset] = []
    
    # Загальна статистика
    print("\n" + "="*60)
    total_products = sum(len(prods) for prods in all_results.values())
    print(f"📊 Binance - Всього отримано: {total_products} продуктів")
    
    return all_results


async def test_bybit_api():
    """
    Тестує Bybit API для отримання даних по топ-5 криптовалютах.
    """
    print_separator("🔵 BYBIT API - Тестування")
    
    # Перевірка налаштувань
    if (settings.bybit_api_key == "your_bybit_api_key_here" or 
        not settings.bybit_api_key):
        print("⚠️ УВАГА: Bybit API ключі не налаштовані!")
        print("Встановіть змінні BYBIT_API_KEY та BYBIT_API_SECRET у .env файлі")
        return None
    
    logger.info("Ініціалізація Bybit API клієнта...")
    bybit = BybitAPI(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret
    )
    
    all_results = {}
    
    # Тестуємо кожен актив
    for asset in TEST_ASSETS:
        print(f"\n📊 Отримання даних для {asset}...")
        try:
            products = await bybit.get_earn_products_by_asset(asset)
            all_results[asset] = products
            
            if products:
                print(f"   ✅ Знайдено {len(products)} продуктів")
            else:
                print(f"   ⚠️ Продуктів не знайдено")
                
        except Exception as e:
            logger.error(f"Помилка при отриманні {asset}: {e}")
            print(f"   ❌ Помилка: {e}")
            all_results[asset] = []
    
    # Загальна статистика
    print("\n" + "="*60)
    total_products = sum(len(prods) for prods in all_results.values())
    print(f"📊 Bybit - Всього отримано: {total_products} продуктів")
    
    return all_results


def save_results_to_json(binance_data: dict, bybit_data: dict):
    """
    Зберігає результати в JSON файл у папку data/.
    
    Args:
        binance_data: Дані з Binance
        bybit_data: Дані з Bybit
    """
    # Створюємо папку data/ якщо не існує
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"exchange_data_{timestamp}.json"
    filepath = data_dir / filename
    
    combined_data = {
        "timestamp": datetime.now().isoformat(),
        "test_assets": TEST_ASSETS,
        "exchanges": {
            "binance": binance_data if binance_data else {},
            "bybit": bybit_data if bybit_data else {}
        },
        "summary": {
            "binance_total": sum(len(prods) for prods in (binance_data or {}).values()),
            "bybit_total": sum(len(prods) for prods in (bybit_data or {}).values())
        }
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Результати збережено в: tests/data/{filename}")


def display_detailed_results(binance_data: dict, bybit_data: dict):
    """
    Відображає детальні результати для кожного активу.
    
    Args:
        binance_data: Дані з Binance
        bybit_data: Дані з Bybit
    """
    print_separator("📊 ДЕТАЛЬНІ РЕЗУЛЬТАТИ")
    
    for asset in TEST_ASSETS:
        print(f"\n{'█'*70}")
        print(f"  💰 {asset}")
        print(f"{'█'*70}")
        
        # Binance
        if binance_data and asset in binance_data:
            binance_products = binance_data[asset]
            print(f"\n🟡 Binance:")
            print(format_product_details(binance_products, asset))
        else:
            print(f"\n🟡 Binance: Немає даних")
        
        # Bybit
        if bybit_data and asset in bybit_data:
            bybit_products = bybit_data[asset]
            print(f"\n🔵 Bybit:")
            print(format_product_details(bybit_products, asset))
        else:
            print(f"\n🔵 Bybit: Немає даних")
        
        print()  # Порожній рядок для розділення


async def main():
    """
    Головна функція для запуску тестів.
    """
    print_separator("🚀 ТЕСТУВАННЯ API БІРЖ - EARN ПРОДУКТИ")
    print(f"Час запуску: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Тестові активи: {', '.join(TEST_ASSETS)}")
    
    # Тестуємо Binance
    binance_results = await test_binance_api()
    
    # Затримка між запитами
    print("\n⏳ Затримка 2 секунди перед наступним тестом...")
    await asyncio.sleep(2)
    
    # Тестуємо Bybit
    bybit_results = await test_bybit_api()
    
    # Відображаємо детальні результати
    if binance_results or bybit_results:
        display_detailed_results(binance_results, bybit_results)
        
        # Зберігаємо в JSON
        save_results_to_json(binance_results, bybit_results)
    
    # Підсумок
    print_separator("✅ ТЕСТУВАННЯ ЗАВЕРШЕНО")
    
    if binance_results:
        total_binance = sum(len(prods) for prods in binance_results.values())
        print(f"🟡 Binance: {total_binance} продуктів")
    else:
        print(f"🟡 Binance: API не налаштовано або помилка")
    
    if bybit_results:
        total_bybit = sum(len(prods) for prods in bybit_results.values())
        print(f"🔵 Bybit: {total_bybit} продуктів")
    else:
        print(f"🔵 Bybit: API не налаштовано або помилка")
    
    print()


if __name__ == "__main__":
    # Запускаємо асинхронну функцію
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Тестування перервано користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}", exc_info=True)
        print(f"\n❌ Критична помилка: {e}")
        sys.exit(1)

