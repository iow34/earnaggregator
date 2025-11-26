"""
Unit тести для DeepLinkValidator.

Тестує:
- Валідацію payload
- Edge cases (пустий, занадто довгий, невалідні символи)
- Whitelist платформ
- Витягування campaign_id
"""

import pytest
from app.services.tracking.deep_link_validator import DeepLinkValidator


class TestDeepLinkValidator:
    """Тести для валідатора deep link."""
    
    def test_valid_payload(self):
        """Тест валідного payload."""
        payload = "ad_xcom_nov2025_123"
        is_valid, source, parsed = DeepLinkValidator.validate(payload)
        
        assert is_valid is True
        assert source == "ad_xcom_nov2025_123"
        assert parsed is not None
        assert parsed['platform'] == 'xcom'
        assert parsed['campaign_id'] == 'nov2025_123'
        assert parsed['prefix'] == 'ad'
    
    def test_valid_payload_with_extra(self):
        """Тест payload з extra параметром."""
        payload = "ad_telegram_ads_001_variant_a"
        is_valid, source, parsed = DeepLinkValidator.validate(payload)
        
        assert is_valid is True
        assert source == "ad_telegram_ads_001_variant_a"
        assert parsed['extra'] == 'variant_a'
    
    def test_empty_payload(self):
        """Тест пустого payload (organic)."""
        is_valid, source, parsed = DeepLinkValidator.validate(None)
        assert is_valid is True
        assert source == "organic"
        assert parsed is None
        
        is_valid, source, parsed = DeepLinkValidator.validate("")
        assert is_valid is True
        assert source == "organic"
        assert parsed is None
    
    def test_start_payload(self):
        """Тест payload='start' (organic)."""
        is_valid, source, parsed = DeepLinkValidator.validate("start")
        assert is_valid is True
        assert source == "organic"
        assert parsed is None
    
    def test_too_short_payload(self):
        """Тест занадто короткого payload."""
        is_valid, source, parsed = DeepLinkValidator.validate("ad_x")
        assert is_valid is False
        assert source == "malformed_deeplink"
    
    def test_too_long_payload(self):
        """Тест занадто довгого payload."""
        long_payload = "a" * 65
        is_valid, source, parsed = DeepLinkValidator.validate(long_payload)
        assert is_valid is False
        assert source == "malformed_deeplink"
    
    def test_invalid_characters(self):
        """Тест payload з недозволеними символами."""
        is_valid, source, parsed = DeepLinkValidator.validate("ad_xcom_123&ref=hack")
        assert is_valid is False
        assert source == "malformed_deeplink"
    
    def test_invalid_format(self):
        """Тест невалідного формату."""
        is_valid, source, parsed = DeepLinkValidator.validate("ad_xcom")
        assert is_valid is False
        assert source == "malformed_deeplink"
    
    def test_unknown_platform(self):
        """Тест невідомої платформи (не в whitelist)."""
        is_valid, source, parsed = DeepLinkValidator.validate("ad_unknown_platform_123")
        assert is_valid is True  # Все одно валідний, але з warning
        assert source == "ad_unknown_unknown_platform_123"
        assert parsed is not None
        assert parsed.get('warning') == 'unknown_platform'
    
    def test_test_prefix(self):
        """Тест payload з префіксом test_."""
        payload = "test_xcom_001"
        is_valid, source, parsed = DeepLinkValidator.validate(payload)
        assert is_valid is True
        assert source == "test_xcom_001"
        assert parsed['prefix'] == 'test'
    
    def test_extract_campaign_id(self):
        """Тест витягування campaign_id."""
        campaign_id = DeepLinkValidator.extract_campaign_id("ad_xcom_nov2025_123")
        assert campaign_id == "nov2025_123"
        
        campaign_id = DeepLinkValidator.extract_campaign_id("organic")
        assert campaign_id is None
    
    def test_is_test_payload(self):
        """Тест перевірки тестового payload."""
        assert DeepLinkValidator.is_test_payload("test_xcom_001") is True
        assert DeepLinkValidator.is_test_payload("ad_xcom_001") is False
        assert DeepLinkValidator.is_test_payload(None) is False
    
    def test_sanitize_payload(self):
        """Тест очищення payload."""
        assert DeepLinkValidator.sanitize_payload("  AD_XCOM_123  ") == "ad_xcom_123"
        assert DeepLinkValidator.sanitize_payload(None) == "organic"
        assert DeepLinkValidator.sanitize_payload("") == "organic"
    
    def test_case_insensitive(self):
        """Тест регістронезалежності."""
        payload_upper = "AD_XCOM_NOV2025_123"
        is_valid, source, parsed = DeepLinkValidator.validate(payload_upper)
        assert is_valid is True
        # Платформа і campaign_id приводяться до lowercase
        assert parsed['platform'] == 'xcom'
        assert parsed['campaign_id'] == 'nov2025_123'

