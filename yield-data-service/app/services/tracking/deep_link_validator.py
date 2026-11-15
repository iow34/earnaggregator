import re
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, UTC

from app.utils.logger import logger


class DeepLinkValidator:
    ALLOWED_PLATFORMS = [
        "xcom",
        "telegram",
        "telegram_ads",
        "facebook",
        "reddit",
        "website",
        "website_banner",
        "email",
        "email_campaign",
        "influencer",
        "youtube",
        "instagram",
        "tiktok",
        "discord",
        "linkedin",
        "twitter",
        "medium",
        "blog",
    ]

    LEGACY_PAYLOAD_PATTERN = re.compile(
        r"^(ad|test)_([a-z0-9_-]+)_([a-z0-9_-]+)(_[a-z0-9_-]+)?$", re.IGNORECASE
    )

    UTM_PAYLOAD_PATTERN = re.compile(r"^utm_([a-z0-9_-]+)_([a-z0-9_-]+)_(.+)$", re.IGNORECASE)

    MIN_LENGTH = 5  # "ad_x_1"
    MAX_LENGTH = 64

    @classmethod
    def validate(cls, payload: Optional[str]) -> Tuple[bool, str, Optional[Dict[str, Any]]]:

        if not payload or payload.strip() == "" or payload.strip().lower() == "start":
            logger.info("📊 Органічний вхід (пустий payload або 'start')")
            return True, "organic", None

        payload = payload.strip()

        if len(payload) < cls.MIN_LENGTH:
            logger.warning(f"⚠️ Payload занадто короткий: {len(payload)} < {cls.MIN_LENGTH}")
            return False, "malformed_deeplink", None

        if len(payload) > cls.MAX_LENGTH:
            logger.warning(f"⚠️ Payload занадто довгий: {len(payload)} > {cls.MAX_LENGTH}")

            return False, "malformed_deeplink", {"reason": "payload_at_limit"}

        if not re.match(r"^[a-zA-Z0-9_-]+$", payload):
            logger.warning(f"⚠️ Payload містить недозволені символи: {payload}")
            return False, "malformed_deeplink", {"reason": "invalid_characters"}

        if payload.lower().startswith("utm_"):
            return cls._validate_utm_payload(payload)
        else:
            return cls._validate_legacy_payload(payload)

    @classmethod
    def extract_campaign_id(cls, payload: Optional[str]) -> Optional[str]:
        is_valid, source, parsed_data = cls.validate(payload)

        if not is_valid or not parsed_data:
            return None

        return parsed_data.get("campaign_id")

    @classmethod
    def _validate_utm_payload(cls, payload: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:

        parts = payload.split("_", 3)

        if len(parts) < 4 or parts[0].lower() != "utm":
            logger.warning(f"⚠️ UTM payload не відповідає формату: {payload}")
            return False, "malformed_deeplink", {"reason": "invalid_utm_format"}

        source_part = parts[1]
        geo_part = parts[2]
        creative_part = parts[3] if len(parts) > 3 else ""

        if not all([source_part, geo_part, creative_part]):
            logger.warning(f"⚠️ UTM payload містить пусті частини: {payload}")
            return False, "malformed_deeplink", {"reason": "empty_utm_parts"}

        campaign_id = f"{source_part}_{geo_part}"

        source = payload.lower()

        parsed_data = {
            "format": "utm",
            "source": source_part,
            "geo": geo_part,
            "creative": creative_part,
            "campaign_id": campaign_id,
        }

        logger.info(f"✅ UTM payload валідний: {source}, campaign_id={campaign_id}")
        return True, source, parsed_data

    @classmethod
    def _validate_legacy_payload(cls, payload: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:

        parts = payload.split("_")

        if len(parts) < 3:
            logger.warning(f"⚠️ Legacy payload не відповідає формату (замало частин): {payload}")
            return False, "malformed_deeplink", {"reason": "invalid_format"}

        prefix = parts[0].lower()
        platform = parts[1].lower()

        campaign_id = "_".join(parts[2:])

        if prefix not in ["ad", "test"]:
            logger.warning(f"⚠️ Невалідний префікс: {prefix}")
            return False, "malformed_deeplink", {"reason": "invalid_prefix"}

        if platform not in cls.ALLOWED_PLATFORMS:
            logger.warning(f"⚠️ Невідома платформа: {platform} (не в whitelist)")

            source = payload.lower()
            parsed_data = {
                "format": "legacy",
                "prefix": prefix,
                "platform": platform,
                "campaign_id": campaign_id,
                "warning": "unknown_platform",
            }
            return True, source, parsed_data

        source = payload.lower()

        parsed_data = {
            "format": "legacy",
            "prefix": prefix,
            "platform": platform,
            "campaign_id": campaign_id,
        }

        logger.info(f"✅ Legacy payload валідний: {source}, campaign_id={campaign_id}")
        return True, source, parsed_data

    @classmethod
    def is_test_payload(cls, payload: Optional[str]) -> bool:
        if not payload:
            return False

        return payload.strip().lower().startswith("test_")

    @classmethod
    def validate_campaign_active(cls, end_date: Optional[datetime]) -> Tuple[bool, Optional[str]]:
        if end_date is None:
            return True, None

        now = datetime.now(UTC).replace(tzinfo=None)

        if end_date < now:
            return False, f"Campaign expired on {end_date.isoformat()}"

        return True, None

    @classmethod
    def sanitize_payload(cls, payload: Optional[str]) -> str:
        if not payload:
            return "organic"

        import urllib.parse

        payload = urllib.parse.unquote(payload)

        payload = payload.strip()

        payload = payload.lower()

        return payload


deep_link_validator = DeepLinkValidator()
