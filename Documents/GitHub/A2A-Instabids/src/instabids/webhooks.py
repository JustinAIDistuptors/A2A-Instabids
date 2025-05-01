import hmac, hashlib, os, time, asyncio

SECRET = os.environ.get("WEBHOOK_SECRET", "changeme")
MAX_AGE = 300  # seconds


def verify_signature(token: str):
    # dummy Depends stub for FastAPI
    return token


class _PushBus:
    def __init__(self):
        self._subs: dict[str, set[asyncio.Queue]] = {}

    def subscribe(self, task_id: str):
        q = asyncio.Queue()
        self._subs.setdefault(task_id, set()).add(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subs[task_id].discard(q)

    async def publish(self, task_id: str, event: dict):
        for q in self._subs.get(task_id, []):
            await q.put(event)


push_to_ui = _PushBus()
