"""
trading_bridge.py — MetaTrader 5 Webhook Receiver

Receives trade updates from MT5 Expert Advisors via webhook and stores
them in Supabase for the "Venture Lab" Live Performance dashboard.
Designed to run as a standalone FastAPI mount or as a separate service.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.supabase import insert_record, select_records

logger = logging.getLogger("trading_bridge")

mt5_router = APIRouter(prefix="/mt5")


class MT5WebhookPayload(BaseModel):
    symbol: str
    magic_number: int = 0
    order_type: str = Field(pattern=r"^(buy|sell|close|modify)$")
    volume: float
    price: float
    stop_loss: float = 0.0
    take_profit: float = 0.0
    profit: float = 0.0
    balance: float = 0.0
    equity: float = 0.0
    comment: str = ""
    timestamp: str = ""


@mt5_router.post("/webhook")
async def mt5_webhook(body: MT5WebhookPayload, request: Request):
    logger.info(f"MT5 webhook received: {body.symbol} {body.order_type} @ {body.price}")

    try:
        record = body.model_dump()
        if not record.get("timestamp"):
            record["timestamp"] = datetime.now(timezone.utc).isoformat()
        result = await insert_record("mt5_trades", record)
        if result:
            return {"status": "success", "trade_id": result.get("id")}
        return {"status": "error", "detail": "Insert failed"}
    except Exception as e:
        logger.error(f"MT5 webhook error: {e}")
        raise HTTPException(status_code=500, detail="MT5 webhook processing failed")


@mt5_router.get("/performance/{symbol:path}")
async def get_performance(symbol: str):
    try:
        trades = await select_records("mt5_trades", "symbol", symbol.upper(), order_col="timestamp", desc=True, limit=100)
        return {"symbol": symbol.upper(), "trades": trades}
    except Exception as e:
        logger.error(f"Performance retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve performance data")
