import pytest
from app.services.tracking.deep_link_validator import DeepLinkValidator


class TestDeepLinkValidator:
    def test_valid_payload(self):
        payload = "ad_xcom_nov2025_123"
        is_valid, source, parsed = DeepLinkValidator.validate(payload)

        assert is_valid is True
        assert source == "ad_xcom_nov2025_123"
        assert parsed is not None
        assert parsed["platform"] == "xcom"
        assert parsed["campaign_id"] == "nov2025_123"
        assert parsed["prefix"] == "ad"

    def test_valid_payload_with_extra(self):
        payload = "ad_telegram_ads_001_variant_a"
        is_valid, source, parsed = DeepLinkValidator.validate(payload)

        assert is_valid is True
        assert source == "ad_telegram_ads_001_variant_a"
        assert parsed["extra"] == "variant_a"

    def test_empty_payload(self):
        is_valid, source, parsed = DeepLinkValidator.validate(None)
        assert is_valid is True
        assert source == "organic"
        assert parsed is None

        is_valid, source, parsed = DeepLinkValidator.validate("")
        assert is_valid is True
        assert source == "organic"
        assert parsed is None

    def test_start_payload(self):
        is_valid, source, parsed = DeepLinkValidator.validate("start")
        assert is_valid is True
        assert source == "organic"
        assert parsed is None

    def test_too_short_payload(self):
        is_valid, source, parsed = DeepLinkValidator.validate("ad_x")
        assert is_valid is False
        assert source == "malformed_deeplink"

    def test_too_long_payload(self):
        long_payload = "a" * 65
        is_valid, source, parsed = DeepLinkValidator.validate(long_payload)
        assert is_valid is False
        assert source == "malformed_deeplink"

    def test_invalid_characters(self):
        is_valid, source, parsed = DeepLinkValidator.validate("ad_xcom_123&ref=hack")
        assert is_valid is False
        assert source == "malformed_deeplink"

    def test_invalid_format(self):
        is_valid, source, parsed = DeepLinkValidator.validate("ad_xcom")
        assert is_valid is False
        assert source == "malformed_deeplink"

    def test_unknown_platform(self):
        is_valid, source, parsed = DeepLinkValidator.validate("ad_unknown_platform_123")
        assert is_valid is True
        assert source == "ad_unknown_unknown_platform_123"
        assert parsed is not None
        assert parsed.get("warning") == "unknown_platform"

    def test_test_prefix(self):
        payload = "test_xcom_001"
        is_valid, source, parsed = DeepLinkValidator.validate(payload)
        assert is_valid is True
        assert source == "test_xcom_001"
        assert parsed["prefix"] == "test"

    def test_extract_campaign_id(self):
        campaign_id = DeepLinkValidator.extract_campaign_id("ad_xcom_nov2025_123")
        assert campaign_id == "nov2025_123"

        campaign_id = DeepLinkValidator.extract_campaign_id("organic")
        assert campaign_id is None

    def test_is_test_payload(self):
        assert DeepLinkValidator.is_test_payload("test_xcom_001") is True
        assert DeepLinkValidator.is_test_payload("ad_xcom_001") is False
        assert DeepLinkValidator.is_test_payload(None) is False

    def test_sanitize_payload(self):
        assert DeepLinkValidator.sanitize_payload("  AD_XCOM_123  ") == "ad_xcom_123"
        assert DeepLinkValidator.sanitize_payload(None) == "organic"
        assert DeepLinkValidator.sanitize_payload("") == "organic"

    def test_case_insensitive(self):
        payload_upper = "AD_XCOM_NOV2025_123"
        is_valid, source, parsed = DeepLinkValidator.validate(payload_upper)
        assert is_valid is True

        assert parsed["platform"] == "xcom"
        assert parsed["campaign_id"] == "nov2025_123"

    def test_valid_utm_payload(self):
        payload = "utm_tgads_geo_ua_creative_a"
        is_valid, source, parsed = DeepLinkValidator.validate(payload)

        assert is_valid is True
        assert source == "utm_tgads_geo_ua_creative_a"
        assert parsed is not None
        assert parsed["format"] == "utm"
        assert parsed["source"] == "tgads"
        assert parsed["geo"] == "geo"
        assert parsed["creative"] == "ua_creative_a"
        assert parsed["campaign_id"] == "tgads_geo"

    def test_valid_utm_payload_simple(self):
        payload = "utm_blogpost_partners_jan"
        is_valid, source, parsed = DeepLinkValidator.validate(payload)

        assert is_valid is True
        assert source == "utm_blogpost_partners_jan"
        assert parsed["format"] == "utm"
        assert parsed["source"] == "blogpost"
        assert parsed["geo"] == "partners"
        assert parsed["creative"] == "jan"
        assert parsed["campaign_id"] == "blogpost_partners"

    def test_invalid_utm_payload_wrong_parts(self):
        payload = "utm_source_only"
        is_valid, source, parsed = DeepLinkValidator.validate(payload)
        assert is_valid is False
        assert source == "malformed_deeplink"

    def test_invalid_utm_payload_empty_parts(self):
        payload = "utm__geo_creative"
        is_valid, source, parsed = DeepLinkValidator.validate(payload)
        assert is_valid is False
        assert source == "malformed_deeplink"

    def test_utm_case_insensitive(self):
        payload_upper = "UTM_TGADS_UA_CREATIVE_A"
        is_valid, source, parsed = DeepLinkValidator.validate(payload_upper)
        assert is_valid is True
        assert parsed["format"] == "utm"
        assert parsed["source"] == "tgads"
        assert parsed["geo"] == "ua"
        assert parsed["creative"] == "creative_a"

    def test_extract_campaign_id_utm(self):
        campaign_id = DeepLinkValidator.extract_campaign_id("utm_tgads_geo_ua_creative_a")
        assert campaign_id == "tgads_geo"

        campaign_id = DeepLinkValidator.extract_campaign_id("utm_blogpost_partners_jan")
        assert campaign_id == "blogpost_partners"
