import hashlib
import redis

_pool = redis.ConnectionPool.from_url("redis://127.0.0.1:6379/1", decode_responses=True)
_redis_client = redis.Redis(connection_pool=_pool)


def qhash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


# --- Questions ---
def add_question(q: str):
    if not q or not q.strip():
        return
    _redis_client.rpush("llm:questions", q.strip())


def clear_questions():
    _redis_client.delete("llm:questions")


def list_questions():
    return _redis_client.lrange("llm:questions", 0, -1)


# --- Metrics per (model, question) ---
def save_response_metrics(
    model_value: str,
    question: str,
    execution_time: float,
    energy_usage: float,
    memory_usage: float,
):
    key = f"llm:resp:{model_value}|{qhash(question)}"
    _redis_client.hset(
        key,
        mapping={
            "execution_time": execution_time,
            "energy_usage": energy_usage,
            "memory_usage": memory_usage,
            "question": question,
        },
    )


def get_model_metrics(model_value: str):
    prefix = f"llm:resp:{model_value}|"
    keys = [k for k in _redis_client.scan_iter(match=prefix + "*")]
    return [_redis_client.hgetall(k) for k in keys]


def clear_all_metrics():
    """Delete ALL stored metrics keys (llm:resp:*) without touching questions."""
    pattern = "llm:resp:*"
    pipe = _redis_client.pipeline(transaction=False)
    count = 0
    for k in _redis_client.scan_iter(match=pattern, count=1000):
        pipe.delete(k)
        count += 1
        if count % 1000 == 0:
            pipe.execute()
    if count:
        pipe.execute()


def clear_model_metrics(model_value: str):
    """Delete metrics for a specific model only."""
    prefix = f"llm:resp:{model_value}|*"
    pipe = _redis_client.pipeline(transaction=False)
    count = 0
    for k in _redis_client.scan_iter(match=prefix, count=1000):
        pipe.delete(k)
        count += 1
        if count % 1000 == 0:
            pipe.execute()
    if count:
        pipe.execute()
