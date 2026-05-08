import json
import logging
from app.config import settings

logger = logging.getLogger("n8n_webhook")

PLACEHOLDER = "your_n8n_link"


def _is_disabled(url: str | None) -> bool:
    return not url or PLACEHOLDER in url


async def trigger_lead_alert(lead_data: dict):
    webhook_url = settings.n8n_webhook_url
    if _is_disabled(webhook_url):
        logger.info("[n8n BYPASS] Lead alert payload (would POST to n8n):\n%s", json.dumps(lead_data, indent=2))
        return

    import httpx
    payload = {
        "event": "new_lead",
        "source": lead_data.get("source", "unknown"),
        "name": lead_data.get("name"),
        "email": lead_data.get("email"),
        "company": lead_data.get("company"),
        "phone": lead_data.get("phone"),
        "hours_manual": lead_data.get("hours_manual"),
        "pain_points": lead_data.get("pain_points"),
        "created_at": lead_data.get("created_at"),
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(webhook_url, json=payload)
        resp.raise_for_status()
        logger.info(f"Lead alert sent to n8n (status={resp.status_code})")


async def trigger_human_handoff(transcript: list[dict], contact_info: dict | None = None):
    webhook_url = settings.n8n_handoff_webhook_url or settings.n8n_webhook_url
    if _is_disabled(webhook_url):
        payload = {
            "event": "human_handoff",
            "transcript": transcript[-12:],
            "contact_info": contact_info or {},
        }
        logger.info("[n8n BYPASS] Human handoff payload (would POST to n8n):\n%s", json.dumps(payload, indent=2))
        return

    import httpx
    handoff_webhook = webhook_url.rstrip("/") + "/handoff"
    payload = {
        "event": "human_handoff",
        "transcript": transcript[-12:],
        "contact_info": contact_info or {},
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(handoff_webhook, json=payload)
        resp.raise_for_status()
        logger.info(f"Human handoff sent to n8n (status={resp.status_code})")
