import hashlib
import redis
import json
import time
import uuid
import os
from dotenv import load_dotenv

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/1")
_pool = redis.ConnectionPool.from_url(REDIS_URL, decode_responses=True)
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


# --- Chat History ---
def save_chat_conversation(model: str, question: str, response: str, metrics: dict):
    conversation_id = str(uuid.uuid4())
    timestamp = time.time()

    # Convert metrics dict to JSON string for storage
    metrics_json = json.dumps(metrics)

    conversation_data = {
        "id": conversation_id,
        "timestamp": str(timestamp),
        "model": model,
        "question": question,
        "response": response,
        "metrics": metrics_json,
    }

    # Store the conversation
    _redis_client.hset(f"llm:chat:{conversation_id}", mapping=conversation_data)

    # Add to conversation list (sorted by timestamp)
    _redis_client.zadd("llm:conversations", {conversation_id: timestamp})

    # Add to model-specific conversation list
    _redis_client.zadd(f"llm:model_conversations:{model}", {conversation_id: timestamp})

    return conversation_id


def get_chat_conversation(conversation_id: str):
    conversation = _redis_client.hgetall(f"llm:chat:{conversation_id}")
    if conversation:
        # Convert timestamp back to float
        conversation["timestamp"] = float(conversation["timestamp"])
        # Parse metrics if it's a string
        if isinstance(conversation.get("metrics"), str):
            try:
                conversation["metrics"] = json.loads(conversation["metrics"])
            except json.JSONDecodeError:
                conversation["metrics"] = {}
    return conversation


def get_all_conversations(limit: int = 50, offset: int = 0):
    """Get all conversations sorted by timestamp (newest first)"""
    conversation_ids = _redis_client.zrevrange(
        "llm:conversations", offset, offset + limit - 1
    )
    conversations = []

    for conv_id in conversation_ids:
        conversation = get_chat_conversation(conv_id)
        if conversation:
            conversations.append(conversation)

    return conversations


def get_model_conversations(model: str, limit: int = 50, offset: int = 0):
    """Get conversations for a specific model"""
    conversation_ids = _redis_client.zrevrange(
        f"llm:model_conversations:{model}", offset, offset + limit - 1
    )
    conversations = []

    for conv_id in conversation_ids:
        conversation = get_chat_conversation(conv_id)
        if conversation:
            conversations.append(conversation)

    return conversations


def delete_conversation(conversation_id: str):
    """Delete a specific conversation"""
    conversation = get_chat_conversation(conversation_id)
    if conversation:
        model = conversation.get("model", "")

        # Remove from main conversation list
        _redis_client.zrem("llm:conversations", conversation_id)

        # Remove from model-specific list
        if model:
            _redis_client.zrem(f"llm:model_conversations:{model}", conversation_id)

        # Delete the conversation data
        _redis_client.delete(f"llm:chat:{conversation_id}")

        return True
    return False


def clear_all_conversations():
    """Delete all chat conversations"""
    # Get all conversation IDs
    conversation_ids = _redis_client.zrange("llm:conversations", 0, -1)

    # Delete each conversation
    for conv_id in conversation_ids:
        delete_conversation(conv_id)


def get_conversation_stats():
    """Get statistics about stored conversations"""
    total_conversations = _redis_client.zcard("llm:conversations")

    # Get unique models
    models = set()
    conversation_ids = _redis_client.zrange("llm:conversations", 0, -1)
    for conv_id in conversation_ids:
        conversation = get_chat_conversation(conv_id)
        if conversation and conversation.get("model"):
            models.add(conversation["model"])

    # Get conversations per model
    model_stats = {}
    for model in models:
        count = _redis_client.zcard(f"llm:model_conversations:{model}")
        model_stats[model] = count

    return {
        "total_conversations": total_conversations,
        "unique_models": len(models),
        "models": list(models),
        "conversations_per_model": model_stats,
    }


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
    keys = list(_redis_client.scan_iter(match=prefix + "*"))
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
