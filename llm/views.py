from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

from llm.utils import get_all_models
from llm.redis_client import (
    save_chat_conversation,
    get_all_conversations,
    get_chat_conversation,
    delete_conversation,
    get_conversation_stats,
    get_model_conversations,
)
from run_simulations import start_threads


def index(request):
    # Always fetch live models from Ollama
    model_choices = get_all_models()
    selected_model = model_choices[0] if model_choices else ""

    response_data = {
        "response": "",
        "question": "",
        "responses": False,
        "model_choices": model_choices,
        "selected_model": selected_model,
    }

    if request.method == "POST":
        model = request.POST.get("model") or ""
        question = request.POST.get("question") or ""
        response_data["selected_model"] = model
        response_data["model"] = model
        response_data["question"] = question
        start_threads(response_data, is_simulation=False)

        # Save the conversation to Redis if we have a response
        if response_data.get("response") and response_data.get("responses"):
            metrics = {
                "execution_time": response_data.get("execution_time", ""),
                "memory_used": response_data.get("memory_used", ""),
                "energy_used": response_data.get("energy_used", ""),
                "cpu_used": response_data.get("cpu_used", ""),
                "peak_memory": response_data.get("peak_memory", ""),
                "peak_cpu": response_data.get("peak_cpu", ""),
            }
            save_chat_conversation(
                model=model,
                question=question,
                response=response_data["response"],
                metrics=metrics,
            )

    return render(request, "index.html", response_data)


def dashboard(request):
    """Dashboard view showing chat history and statistics"""
    # Get filter parameters
    model_filter = request.GET.get("model", "")
    page = int(request.GET.get("page", 1))
    limit = 20
    offset = (page - 1) * limit

    # Get conversations
    if model_filter:
        conversations = get_model_conversations(
            model_filter, limit=limit, offset=offset
        )
    else:
        conversations = get_all_conversations(limit=limit, offset=offset)

    # Get statistics
    stats = get_conversation_stats()

    # Get available models for filter
    model_choices = get_all_models()

    # Format conversations for display
    for conv in conversations:
        # Convert timestamp to readable format
        import datetime

        conv["formatted_time"] = datetime.datetime.fromtimestamp(
            conv["timestamp"]
        ).strftime("%Y-%m-%d %H:%M:%S")

        # Truncate long responses for display
        if len(conv.get("response", "")) > 200:
            conv["response_preview"] = conv["response"][:200] + "..."
        else:
            conv["response_preview"] = conv.get("response", "")

    context = {
        "conversations": conversations,
        "stats": stats,
        "model_choices": model_choices,
        "current_model_filter": model_filter,
        "current_page": page,
        "has_previous": page > 1,
        "has_next": len(conversations) == limit,
        "next_page": page + 1,
        "previous_page": page - 1,
    }

    return render(request, "dashboard.html", context)


def conversation_detail(request, conversation_id):
    """Show detailed view of a specific conversation"""
    conversation = get_chat_conversation(conversation_id)

    if not conversation:
        return redirect("dashboard")

    # Format timestamp
    import datetime

    conversation["formatted_time"] = datetime.datetime.fromtimestamp(
        float(conversation["timestamp"])
    ).strftime("%Y-%m-%d %H:%M:%S")

    return render(request, "conversation_detail.html", {"conversation": conversation})


@csrf_exempt
def delete_conversation_ajax(request):
    """AJAX endpoint to delete a conversation"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            conversation_id = data.get("conversation_id")

            if conversation_id:
                success = delete_conversation(conversation_id)
                return JsonResponse({"success": success})
            return JsonResponse(
                {"success": False, "error": "No conversation ID provided"}
            )
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"})

    return JsonResponse({"success": False, "error": "Invalid request method"})


def api_conversations(request):
    """API endpoint to get conversations as JSON"""
    model_filter = request.GET.get("model", "")
    limit = int(request.GET.get("limit", 50))
    offset = int(request.GET.get("offset", 0))

    if model_filter:
        conversations = get_model_conversations(
            model_filter, limit=limit, offset=offset
        )
    else:
        conversations = get_all_conversations(limit=limit, offset=offset)

    # Format timestamps
    import datetime

    for conv in conversations:
        conv["formatted_time"] = datetime.datetime.fromtimestamp(
            conv["timestamp"]
        ).strftime("%Y-%m-%d %H:%M:%S")

    return JsonResponse({"conversations": conversations})
