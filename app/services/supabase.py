import asyncio
import logging
from functools import partial
from supabase import create_client, Client
from app.config import settings

logger = logging.getLogger("supabase_service")

_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        _supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
        logger.info("Supabase admin client initialised")
    return _supabase


def _run_sync(fn, *args, **kwargs):
    return fn(*args, **kwargs)


async def insert_lead(data: dict) -> dict | None:
    try:
        client = get_supabase()
        fn = partial(client.table("leads").insert(data).execute)
        result = await asyncio.to_thread(fn)
        if result.data:
            logger.info(f"Lead inserted: {result.data[0].get('id', 'unknown')}")
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to insert lead: {e}")
        raise


async def insert_record(table: str, data: dict) -> dict | None:
    try:
        client = get_supabase()
        fn = partial(client.table(table).insert(data).execute)
        result = await asyncio.to_thread(fn)
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to insert into {table}: {e}")
        raise


async def select_records(table: str, column: str, value, order_col: str = "created_at", desc: bool = True, limit: int = 100) -> list:
    try:
        client = get_supabase()
        query = client.table(table).select("*").eq(column, value)
        query = query.order(order_col, desc=desc)
        query = query.limit(limit)
        fn = partial(query.execute)
        result = await asyncio.to_thread(fn)
        return result.data or []
    except Exception as e:
        logger.error(f"Failed to select from {table}: {e}")
        raise


async def check_health() -> bool:
    try:
        client = get_supabase()
        fn = partial(client.table("leads").select("id").limit(1).execute)
        await asyncio.to_thread(fn)
        return True
    except Exception:
        return False
