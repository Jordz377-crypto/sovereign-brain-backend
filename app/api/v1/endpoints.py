import json
import logging
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.models.schemas import ChatRequest, LeadCapture, HandoffRequest, TradingUpdate, HealthResponse
from app.security.aigos_shield import shield
from app.services.supabase import insert_lead, insert_record, check_health as check_supabase_health
from app.services.n8n_webhook import trigger_lead_alert, trigger_human_handoff
from app.engine.groq_rag import stream_chat, check_groq_health
from app.config import settings

logger = logging.getLogger("v1_endpoints")
router = APIRouter(prefix="/v1")


@router.post("/chat")
async def chat_endpoint(body: ChatRequest, request: Request):
    raw_messages = [m.model_dump() for m in body.messages]

    last_user_msg = next((m["content"] for m in reversed(raw_messages) if m["role"] == "user"), "")
    print(f"[AIGOS] Incoming message: {last_user_msg[:200]}")

    sanitized_messages, findings = shield.sanitize_messages(raw_messages)

    shield.log_security_event("chat_request", {
        "message_count": len(raw_messages),
        "jailbreak_score": findings["jailbreak_score"],
        "pii_redacted_count": len(findings["pii_redacted"]),
        "ip": request.client.host if request.client else "unknown",
    })

    for msg in sanitized_messages:
        guard = shield.check_founders_guard(msg.get("content", ""))
        if guard:
            logger.info(f"Founders guard triggered: {guard}")

    if not settings.groq_api_key:
        async def error_stream():
            yield f"data: {json.dumps({'content': 'Sovereign Brain Error: Groq Key Missing.'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    async def event_stream():
        async for chunk in stream_chat(sanitized_messages):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/leads/capture")
async def leads_capture(body: LeadCapture, request: Request):
    payload = body.model_dump(exclude_none=True)
    payload.setdefault("payload", {})

    sanitized_payload, findings = shield.sanitize_text(json.dumps(payload))
    sanitized_dict = json.loads(sanitized_payload)

    shield.log_security_event("lead_capture", {
        "source": body.source,
        "jailbreak_score": findings["jailbreak_score"],
        "pii_redacted": findings["pii_redacted"],
        "ip": request.client.host if request.client else "unknown",
    })

    try:
        lead = await insert_lead(sanitized_dict)
        if lead:
            await trigger_lead_alert(lead)
            return {"status": "success", "lead_id": lead.get("id")}
        return {"status": "error", "detail": "Failed to insert lead"}
    except Exception as e:
        logger.error(f"Lead capture failed: {e}")
        raise HTTPException(status_code=500, detail="Lead capture failed")


@router.post("/handoff")
async def human_handoff(body: HandoffRequest, request: Request):
    transcript_dicts = [m.model_dump() for m in body.transcript]
    sanitized, findings = shield.sanitize_messages(transcript_dicts)
    contact = body.contact_info or {}

    shield.log_security_event("human_handoff", {
        "transcript_length": len(transcript_dicts),
        "jailbreak_score": findings["jailbreak_score"],
        "ip": request.client.host if request.client else "unknown",
    })

    try:
        await trigger_human_handoff(sanitized, contact)

        lead_payload = {
            "source": "chat_handoff",
            "payload": {"transcript": sanitized[-12:]},
        }
        if contact.get("name"):
            lead_payload["name"] = contact["name"]
        if contact.get("email"):
            lead_payload["email"] = contact["email"]
        if contact.get("phone"):
            lead_payload["phone"] = contact["phone"]

        await insert_lead(lead_payload)
    except Exception as e:
        logger.error(f"Handoff failed: {e}")

    return {
        "status": "success",
        "message": "AIGOS has dispatched a priority alert. A human specialist will connect shortly.",
    }


@router.post("/trading/bridge")
async def trading_bridge(body: TradingUpdate, request: Request):
    shield.log_security_event("trading_update", {
        "symbol": body.symbol,
        "ip": request.client.host if request.client else "unknown",
    })

    try:
        record = await insert_record("trading_performance", body.model_dump(exclude_none=True))
        if record:
            logger.info(f"Trading update stored: {body.symbol} P/L={body.profit_loss}")
            return {"status": "success", "id": record.get("id")}
        return {"status": "error", "detail": "Failed to store trading update"}
    except Exception as e:
        logger.error(f"Trading bridge failed: {e}")
        raise HTTPException(status_code=500, detail="Trading bridge error")


@router.get("/system/health", response_model=HealthResponse)
async def system_health():
    groq_ok = await check_groq_health()
    supabase_ok = await check_supabase_health()
    return HealthResponse(
        status="healthy" if (groq_ok and supabase_ok) else "degraded",
        version=settings.app_version,
        groq_available=groq_ok,
        supabase_connected=supabase_ok,
    )
