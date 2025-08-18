import random
import threading

import matplotlib.pyplot as plt
import numpy as np

from llm.redis_client import (
    clear_all_metrics,
    get_model_metrics,
    list_questions,
    save_response_metrics,
)
from llm.utils import (
    get_all_models,
    get_power,
    initialize_peak_metrics,
    monitor_resources,
    report_resource_usage,
)
from llm.utils import get_response_from_ollama


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


if __name__ == "__main__":
    simulate()
    plot()
