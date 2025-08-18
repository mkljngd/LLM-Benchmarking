import random
import threading
import time
import matplotlib.pyplot as plt
import numpy as np
import ollama
from django.shortcuts import render
from llm.redis_client import (
    clear_all_metrics,
    get_model_metrics,
    list_questions,
    save_response_metrics,
)
from llm.utils import (
    get_all_models,
    get_current_resource_usage,
    get_energy_usage,
    get_power,
    initialize_peak_metrics,
    report_resource_usage,
    update_peak_metrics,
)


# Get the response from the LLM model
def get_response_from_ollama(response_data, peak_metrics):
    question = response_data.get("question", "")
    model = response_data.get("model", "")
    if not question:
        response_data["response"] = "Please ask a question"
        peak_metrics["monitor"] = False
        return

    try:
        resp = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": question}],
            options={"temperature": 0.7},
        )
        response = resp["message"]["content"]
    except Exception as e:
        response = f"Error calling model '{model}': {e}"

    response_data["response"] = response
    peak_metrics["monitor"] = False


# Continuously monitor resource usage (memory, CPU, power) and update peak metrics accordingly
def monitor_resources(peak_metrics):
    while peak_metrics.get("monitor", False):
        loop_start = time.time()
        current_mem, current_cpu, current_power = get_current_resource_usage()
        update_peak_metrics(peak_metrics, current_mem, current_cpu)

        # If power available, accumulate instantaneous energy
        if current_power is not None:
            elapsed = time.time() - loop_start
            instantaneous_energy = get_energy_usage(current_power, elapsed)
            peak_metrics["energy"] += instantaneous_energy

        time.sleep(0.1)


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


# Query each live LLM model with all questions stored in Redis and save metrics in Redis for plotting
def simulate():
    clear_all_metrics()
    questions = list_questions()  # from Redis (seeded via text file)
    models = get_all_models()  # live from Ollama
    if not questions or not models:
        print("No questions or models available for simulation.")
        return

    model_question_pairs = [(m, q) for m in models for q in questions]
    random.shuffle(model_question_pairs)

    for model, question in model_question_pairs:
        response_data = {
            "response": "",
            "question": question,
            "responses": False,
            "model": model,
        }
        start_threads(response_data, is_simulation=True)


# Start two threads: get LLM response and log resource usage
def start_threads(response_data, is_simulation=False):
    start_power = get_power()
    peak_metrics = initialize_peak_metrics(start_power)

    ollama_thread = threading.Thread(
        target=get_response_from_ollama,
        args=(response_data, peak_metrics),
        daemon=True,
    )
    monitor_thread = threading.Thread(
        target=monitor_resources,
        args=(peak_metrics,),
        daemon=True,
    )

    ollama_thread.start()
    monitor_thread.start()

    ollama_thread.join()
    monitor_thread.join()

    # Fill response_data with computed stats (strings with units)
    report_resource_usage(peak_metrics, response_data, is_simulation)

    # Persist numeric metrics for simulations
    if is_simulation:

        def _num(s, default=0.0):
            try:
                return float(str(s).split()[0])
            except Exception:
                return default

        save_response_metrics(
            response_data.get("model", ""),
            response_data.get("question", ""),
            execution_time=_num(response_data.get("execution_time")),
            energy_usage=_num(response_data.get("energy_used")),
            memory_usage=_num(response_data.get("memory_used")),
        )


# Plot graphs based on metrics stored in Redis for currently installed models
def plot():
    models = get_all_models()  # live models
    if not models:
        print("No models available for plotting.")
        return

    for model_value in models:
        metrics = get_model_metrics(model_value)
        if not metrics:
            continue

        execs = [float(m["execution_time"]) for m in metrics if m.get("execution_time")]
        energ = [float(m["energy_usage"]) for m in metrics if m.get("energy_usage")]
        mems = [float(m["memory_usage"]) for m in metrics if m.get("memory_usage")]

        if not (execs and energ and mems):
            continue

        avg_execution_time = round(float(np.mean(execs)), 2)
        std_execution_time = round(float(np.std(execs)), 2)
        avg_energy_use = round(float(np.mean(energ)), 2)
        std_energy_use = round(float(np.std(energ)), 2)
        avg_memory_use = round(float(np.mean(mems)), 2)
        std_memory_use = round(float(np.std(mems)), 2)

        print("Model =>", model_value)
        print(f"Average Execution Time: {avg_execution_time} seconds")
        print(f"StdDev Execution Time: {std_execution_time} seconds")
        print(f"Average Energy Use: {avg_energy_use} J")
        print(f"StdDev Energy Use: {std_energy_use} J")
        print(f"Average Memory Use: {avg_memory_use} MiB")
        print(f"StdDev Memory Use: {std_memory_use} MiB")
        print("-" * 60)

        # Data for plotting
        categories = ["Execution Time", "Energy Use", "Memory Use"]
        averages = [avg_execution_time, avg_energy_use, avg_memory_use]
        std_devs = [std_execution_time, std_energy_use, std_memory_use]

        # Creating the bar plot with error bars for each model
        plt.figure(figsize=(10, 6))
        plt.bar(categories, averages, yerr=std_devs, capsize=10)
        plt.xlabel("Metric")
        plt.ylabel("Values")
        plt.title(f"Model Performance - {model_value}")

        # Save the plot as a PNG file
        filename = f"{model_value.replace(':', '_').replace(' ', '_')}.png"
        plt.savefig(filename)
        plt.close()  # Close the plot to free memory
