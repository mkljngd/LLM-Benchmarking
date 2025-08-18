from django.shortcuts import render

from llm.utils import get_all_models
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

    return render(request, "index.html", response_data)
