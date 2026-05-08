import re
import json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("aigos_shield")

ZA_ID_PATTERN = re.compile(r"\b(\d{2})(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{4}(0[0-1]|1)\d{2}(?!\d)\b")
ZA_PHONE_PATTERN = re.compile(
    r"(?:\+27|0027|0)[-\s.]?(?:[16789]\d{1,2})[-\s.]?(?:\d{3})[-\s.]?(?:\d{4})\b"
)
ZA_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
ZA_ADDRESS_PATTERN = re.compile(
    r"\b(?:\d{1,5}\s)?(?:[A-Za-z0-9\s]+(?:Street|St|Road|Rd|Ave|Avenue|Drive|Dr|Lane|Ln|Close|Crescent|Cres|Circle|Cir|Court|Ct|Way|Terrace|Ter|Place|Pl|Park|Parade|Square|Sq))(?:\s*,?\s*(?:[A-Za-z\s]+))?(?:\s*,?\s*(?:\d{4}))?\b",
    re.IGNORECASE,
)

JAILBREAK_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(prior|previous|above|the\s+above)\s+instructions?", re.I),
    re.compile(r"forget\s+(all\s+)?(prior|previous|above)\s+(instructions?|prompts?|directives?)", re.I),
    re.compile(r"system\s*(instruction|prompt|message|override)", re.I),
    re.compile(r"you\s+are\s+(now|no longer|not)\s+(an?\s+)?(AI|assistant|chatbot|bot)", re.I),
    re.compile(r"act\s+as\s+(if\s+you\s+are|though\s+you\s+are)", re.I),
    re.compile(r"do\s+not\s+(follow|adhere|obey|comply|listen)", re.I),
    re.compile(r"you\s+have\s+no\s+(restrictions?|limitations?|rules?|boundaries?)", re.I),
    re.compile(r"DAN|jailbreak|bypass\s+(filter|restriction|limit|safeguard)", re.I),
    re.compile(r"output\s+in\s+markdown\s+with\s+code\s+blocks", re.I),
    re.compile(r"role\s*(play|playing)\s*:", re.I),
]


class AIGOSShield:
    def __init__(self):
        self._audit_log: list[dict] = []

    def sanitize_text(self, text: str) -> tuple[str, dict]:
        findings = {"pii_redacted": [], "jailbreak_score": 0.0}

        jailbreak_matches = []
        for i, pattern in enumerate(JAILBREAK_PATTERNS):
            if pattern.search(text):
                jailbreak_matches.append(pattern.pattern[:60])
        findings["jailbreak_score"] = min(1.0, len(jailbreak_matches) * 0.25)

        za_ids = ZA_ID_PATTERN.findall(text)
        if za_ids:
            text = ZA_ID_PATTERN.sub("[REDACTED-ZA-ID]", text)
            findings["pii_redacted"].append({"type": "za_id_number", "count": len(za_ids)})

        phones = ZA_PHONE_PATTERN.findall(text)
        if phones:
            text = ZA_PHONE_PATTERN.sub("[REDACTED-PHONE]", text)
            findings["pii_redacted"].append({"type": "phone_number", "count": len(phones)})

        emails = ZA_EMAIL_PATTERN.findall(text)
        if emails:
            text = ZA_EMAIL_PATTERN.sub("[REDACTED-EMAIL]", text)
            findings["pii_redacted"].append({"type": "email", "count": len(emails)})

        addresses = ZA_ADDRESS_PATTERN.findall(text)
        if addresses:
            text = ZA_ADDRESS_PATTERN.sub("[REDACTED-ADDRESS]", text)
            findings["pii_redacted"].append({"type": "address", "count": len(addresses)})

        return text, findings

    def sanitize_messages(
        self, messages: list[dict]
    ) -> tuple[list[dict], dict]:
        total_findings = {"pii_redacted": [], "jailbreak_score": 0.0, "messages_checked": len(messages)}
        sanitized = []
        for msg in messages:
            sanitized_content, msg_findings = self.sanitize_text(msg.get("content", ""))
            sanitized.append({**msg, "content": sanitized_content})
            total_findings["pii_redacted"].extend(msg_findings["pii_redacted"])
            total_findings["jailbreak_score"] = max(
                total_findings["jailbreak_score"], msg_findings["jailbreak_score"]
            )
        return sanitized, total_findings

    def check_founders_guard(self, text: str) -> Optional[dict]:
        from app.config import settings
        founders_map = {
            settings.za_founder_1_name.lower(): settings.za_founder_1_phone,
            settings.za_founder_2_name.lower(): settings.za_founder_2_phone,
        }
        for name, phone in founders_map.items():
            if name in text.lower():
                if any(kw in text.lower() for kw in ["lead", "contact", "client", "refer", "introduc"]):
                    return {"founder": name, "phone": phone, "action": "route_to_internal_n8n"}
        return None

    def log_security_event(self, event_type: str, details: dict):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "details": details,
        }
        self._audit_log.append(entry)
        logger.info(f"[AIGOS AUDIT] {event_type}: {json.dumps(details)}")
        return entry

    def get_audit_log(self) -> list[dict]:
        return self._audit_log.copy()


shield = AIGOSShield()
