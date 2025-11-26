"""
Валідатор для deep link payload.

Валідує payload з deep link посилань згідно з ТЗ:
- Формат: ad_platform_campaignID_extra
- Regex перевірка
- Whitelist платформ
- Обробка edge cases
"""

import re
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, UTC

from app.utils.logger import logger


class DeepLinkValidator:
    """
    Валідатор для deep link payload.
    
    Перевіряє формат, платформу, довжину та обробляє edge cases.
    """
    
    # Whitelist дозволених платформ
    ALLOWED_PLATFORMS = [
        'xcom',
        'telegram',
        'telegram_ads',
        'facebook',
        'reddit',
        'website',
        'website_banner',
        'email',
        'email_campaign',
        'influencer',
        'youtube',
        'instagram',
        'tiktok',
        'discord',
        'linkedin',
        'twitter',
        'medium',
        'blog'
    ]
    
    # Regex для валідації payload
    # Формат: (ad|test)_platform_campaignID_extra (extra опціонально)
    PAYLOAD_PATTERN = re.compile(
        r'^(ad|test)_([a-z0-9_-]+)_([a-z0-9_-]+)(_[a-z0-9_-]+)?$',
        re.IGNORECASE
    )
    
    # Мінімальна та максимальна довжина
    MIN_LENGTH = 5  # "ad_x_1"
    MAX_LENGTH = 64  # Обмеження Telegram
    
    @classmethod
    def validate(
        cls,
        payload: Optional[str]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Валідує deep link payload.
        
        Args:
            payload: Payload з deep link
            
        Returns:
            Tuple: (is_valid, source, parsed_data)
            - is_valid: True якщо payload валідний
            - source: Джерело для збереження (або organic/malformed_deeplink)
            - parsed_data: Розпарсені дані (prefix, platform, campaign_id, extra)
        """
        # Edge Case 1: Пустий payload або "start"
        if not payload or payload.strip() == "" or payload.strip().lower() == "start":
            logger.info("📊 Органічний вхід (пустий payload або 'start')")
            return True, "organic", None
        
        payload = payload.strip()
        
        # Edge Case 2: Перевірка довжини
        if len(payload) < cls.MIN_LENGTH:
            logger.warning(f"⚠️ Payload занадто короткий: {len(payload)} < {cls.MIN_LENGTH}")
            return False, "malformed_deeplink", None
        
        if len(payload) > cls.MAX_LENGTH:
            logger.warning(f"⚠️ Payload занадто довгий: {len(payload)} > {cls.MAX_LENGTH}")
            # Можливо відрізано Telegram - логуємо warning
            return False, "malformed_deeplink", {"reason": "payload_at_limit"}
        
        # Edge Case 3: Перевірка на дозволені символи
        if not re.match(r'^[a-zA-Z0-9_-]+$', payload):
            logger.warning(f"⚠️ Payload містить недозволені символи: {payload}")
            return False, "malformed_deeplink", {"reason": "invalid_characters"}
        
        # Простіший парсинг: розділити по підкреслення
        parts = payload.split('_')
        
        if len(parts) < 3:
            logger.warning(f"⚠️ Payload не відповідає формату (замало частин): {payload}")
            return False, "malformed_deeplink", {"reason": "invalid_format"}
        
        # Формат: prefix_platform_campaign_parts...
        prefix = parts[0].lower()  # ad або test
        platform = parts[1].lower()
        
        # Campaign ID - все після platform (parts[2:])
        campaign_id = '_'.join(parts[2:])
        
        # Валідація префіксу
        if prefix not in ['ad', 'test']:
            logger.warning(f"⚠️ Невалідний префікс: {prefix}")
            return False, "malformed_deeplink", {"reason": "invalid_prefix"}
        
        # Семантична валідація: перевірка платформи
        if platform not in cls.ALLOWED_PLATFORMS:
            logger.warning(f"⚠️ Невідома платформа: {platform} (не в whitelist)")
            # Все одно зберігаємо, але позначаємо
            source = payload.lower()
            parsed_data = {
                "prefix": prefix,
                "platform": platform,
                "campaign_id": campaign_id,
                "warning": "unknown_platform"
            }
            return True, source, parsed_data
        
        # Успішна валідація
        source = payload.lower()
        
        parsed_data = {
            "prefix": prefix,
            "platform": platform,
            "campaign_id": campaign_id
        }
        
        logger.info(f"✅ Payload валідний: {source}, campaign_id={campaign_id}")
        return True, source, parsed_data
    
    @classmethod
    def extract_campaign_id(
        cls,
        payload: Optional[str]
    ) -> Optional[str]:
        """
        Витягує campaign_id з payload.
        
        Формат: ad_platform_campaignID_extra
        Campaign ID - все після platform
        
        Args:
            payload: Payload з deep link
            
        Returns:
            campaign_id або None
        """
        is_valid, source, parsed_data = cls.validate(payload)
        
        if not is_valid or not parsed_data:
            return None
        
        return parsed_data.get('campaign_id')
    
    @classmethod
    def is_test_payload(
        cls,
        payload: Optional[str]
    ) -> bool:
        """
        Перевіряє чи payload тестовий.
        
        Args:
            payload: Payload з deep link
            
        Returns:
            True якщо payload починається з "test_"
        """
        if not payload:
            return False
        
        return payload.strip().lower().startswith('test_')
    
    @classmethod
    def validate_campaign_active(
        cls,
        end_date: Optional[datetime]
    ) -> Tuple[bool, Optional[str]]:
        """
        Перевіряє чи кампанія активна.
        
        Args:
            end_date: Дата закінчення кампанії (None = активна)
            
        Returns:
            Tuple: (is_active, warning_message)
        """
        if end_date is None:
            return True, None
        
        now = datetime.now(UTC).replace(tzinfo=None)
        
        if end_date < now:
            return False, f"Campaign expired on {end_date.isoformat()}"
        
        return True, None
    
    @classmethod
    def sanitize_payload(
        cls,
        payload: Optional[str]
    ) -> str:
        """
        Очищує payload від зайвих символів.
        
        Args:
            payload: Вхідний payload
            
        Returns:
            Очищений payload
        """
        if not payload:
            return "organic"
        
        # URL decode якщо потрібно
        import urllib.parse
        payload = urllib.parse.unquote(payload)
        
        # Видалити пробіли
        payload = payload.strip()
        
        # Привести до lowercase
        payload = payload.lower()
        
        return payload


# Глобальний екземпляр
deep_link_validator = DeepLinkValidator()

