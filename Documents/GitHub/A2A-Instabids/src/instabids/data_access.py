from supabase import create_client, Client
import os, json, asyncio
from pgvector.asyncpg import register_vector
import asyncpg
from typing import Any

_supabase: Client | None = None
_pgpool: asyncpg.Pool | None = None


def supabase() -> Client:
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"]
        )
    return _supabase


async def pg() -> asyncpg.Connection:
    global _pgpool
    if _pgpool is None:
        _pgpool = await asyncpg.create_pool(os.environ["SUPABASE_DB_URL"])
        await register_vector(_pgpool)
    return await _pgpool.acquire()


# -- Project helpers --
async def create_project(task_id: str, payload: dict) -> None:
    await supabase().table("projects").insert(
        {"id": task_id, "payload": json.dumps(payload)}
    ).execute()


async def get_project_status(task_id: str) -> dict[str, Any] | None:
    res = (
        await supabase()
        .table("projects")
        .select("status,bids")
        .eq("id", task_id)
        .single()
        .execute()
    )
    return res.data if res.data else None
