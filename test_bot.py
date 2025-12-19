#!/usr/bin/env python3
"""
Тест скрипт для перевірки функціонування Telegram бота EarnAggregator.
"""

import json
import requests
from typing import Optional, Dict, Any


class BotTester:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"

    def get_me(self) -> Dict[str, Any]:
        """Отримати інформацію про бота."""
        response = requests.get(f"{self.base_url}/getMe")
        return response.json()

    def get_updates(self, offset: Optional[int] = None, limit: int = 100) -> Dict[str, Any]:
        """Отримати оновлення від бота."""
        params = {"limit": limit}
        if offset:
            params["offset"] = offset
        response = requests.get(f"{self.base_url}/getUpdates", params=params)
        return response.json()

    def send_message(self, chat_id: int, text: str) -> Dict[str, Any]:
        """Відправити повідомлення боту."""
        data = {"chat_id": chat_id, "text": text}
        response = requests.post(f"{self.base_url}/sendMessage", json=data)
        return response.json()

    def test_commands(self, chat_id: int):
        """Протестувати основні команди бота."""
        commands = [
            "/start",
            "/main",
            "/help",
            "/recommendations",
            "/exchanges"
        ]

        print(f"🚀 Початок тестування бота для chat_id: {chat_id}")
        print("=" * 50)

        for command in commands:
            print(f"\n📤 Відправка команди: {command}")
            try:
                response = self.send_message(chat_id, command)
                if response.get("ok"):
                    print(f"✅ Команда {command} відправлена успішно")
                    # Чекаємо трохи щоб бот обробив
                    import time
                    time.sleep(3)
                else:
                    print(f"❌ Помилка відправки команди {command}: {response.get('description', 'Unknown error')}")
            except Exception as e:
                print(f"❌ Виняток при відправці команди {command}: {e}")

            import time
            time.sleep(1)  # Затримка між командами

        print("\n" + "=" * 50)
        print("🏁 Тестування завершено")


def main():
    # Токен бота з Railway
    BOT_TOKEN = "REMOVED_TELEGRAM_BOT_TOKEN"

    tester = BotTester(BOT_TOKEN)

    # Перевіряємо чи бот працює
    print("🤖 Перевірка статусу бота...")
    bot_info = tester.get_me()
    if bot_info.get("ok"):
        print(f"✅ Бот працює: {bot_info['result']['first_name']} (@{bot_info['result']['username']})")
    else:
        print("❌ Бот не працює або токен неправильний")
        return

    # Отримуємо останні оновлення щоб знайти chat_id
    print("\n📨 Отримання останніх оновлень...")
    updates = tester.get_updates(limit=10)

    if updates.get("ok") and updates.get("result"):
        print(f"✅ Отримано {len(updates['result'])} оновлень")

        # Знаходимо останній chat_id
        latest_update = updates["result"][-1] if updates["result"] else None
        if latest_update:
            chat_id = latest_update["message"]["chat"]["id"]
            print(f"🎯 Використовуємо chat_id: {chat_id}")

            # Запускаємо тестування
            tester.test_commands(chat_id)

            # Отримуємо offset для наступних оновлень
            offset = latest_update["update_id"] + 1
            tester.get_updates(offset=offset)
        else:
            print("❌ Немає доступних оновлень для отримання chat_id")
            print("💡 Спробуйте відправити повідомлення боту @ChainAdvisorBot у Telegram")
    else:
        print("❌ Не вдалося отримати оновлення")
        print("💡 Можливо бот не має нових повідомлень")


if __name__ == "__main__":
    main()