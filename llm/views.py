import random
import re
import subprocess
import threading
import time

import matplotlib.pyplot as plt
import numpy as np
import psutil
from django.shortcuts import render
from llama_index.llms import Ollama
from memory_profiler import memory_usage

from llm.models import Model, Question, Response


# Get the response from the LLM model
def get_response_from_ollama(response_data, peak_metrics):
    question = response_data["question"]
    model = response_data["model"]
    print("Received Question:", question)
    if not question:
        response_data["response"] = "Please ask a question"
    else:
        print("Running Model:", model)
        llm = Ollama(model=model)
        response = llm.complete(question)
        print("Received Response:", response)
        response_data["response"] = response
    peak_metrics["monitor"] = False


# Continuously monitor resource usage (memory, CPU, power) and update peak metrics accordingly
def monitor_resources(peak_metrics):
    while peak_metrics["monitor"]:
        start_time = time.time()
        current_mem, current_cpu, current_power = get_current_resource_usage()
        update_peak_metrics(peak_metrics, current_mem, current_cpu)

        instantaneous_energy = get_energy_usage(current_power, time.time() - start_time)
        peak_metrics["energy"] += instantaneous_energy

        time.sleep(0.1)


# Get current memory usage, CPU usage, and power consumption
def get_current_resource_usage():
    current_mem = memory_usage(-1, interval=0.1, timeout=1)[0]
    current_cpu = psutil.cpu_percent(interval=0.1)
    current_power = get_power()
    return current_mem, current_cpu, current_power


def update_peak_metrics(peak_metrics, current_mem, current_cpu):
    peak_metrics["memory"] = max(peak_metrics["memory"], current_mem)
    peak_metrics["cpu"] = max(peak_metrics["cpu"], current_cpu)


# Get power usage using mac shell command
def get_power():
    # Define the command to run with sudo
    sudo_command = "sudo powermetrics -n 1 | grep 'Combined Power'"

    # Run the sudo command and capture the output
    output = subprocess.check_output(sudo_command, shell=True, universal_newlines=True)
    # Regular expression pattern to find a number followed by ' mW'
    pattern = r"(\d+)\s*mW"

    # Search for the pattern in the string
    match = re.search(pattern, output)
    power_value = None
    # Extract the number if a match is found
    if match:
        power_value = int(match.group(1))

    return power_value


#  The function calculates the energy usage in joules based on the difference in power consumption over a given time period.
def get_energy_usage(current_power, time=10):
    # Convert power to watts (1 watt = 1000 milliwatts)
    power_W = current_power / 1000
    energy_joules = power_W * time
    return energy_joules


def index(request):
    model_choices = {x.model_value: x.model_name for x in Model.objects.all()}
    selected_model = Model.objects.all().first().model_value
    print("MODEL_CHOICES", model_choices)
    response_data = {
        "response": "",
        "question": "",
        "responses": False,
        "model_choices": model_choices,
        "selected_model": selected_model,
    }

    if request.method == "POST":
        model = request.POST.get("model")
        response_data["selected_model"] = model
        question = request.POST.get("question")
        response_data["model"] = model
        response_data["question"] = question
        start_threads(response_data)
    return render(request, "index.html", response_data)


# Initalize required parameters
def initialize_peak_metrics(start_power):
    return {
        "memory": 0,
        "cpu": 0,
        "monitor": True,
        "start_time": time.time(),
        "start_mem": memory_usage(-1, interval=0.1, timeout=1)[0],
        "start_cpu": psutil.cpu_percent(interval=None),
        "end_power": start_power,
        "energy": 0,
    }


# Calculate, show and conditionally update resource usage values in database
def report_resource_usage(peak_metrics, response_data, is_simulation=False):
    end_cpu = psutil.cpu_percent(interval=None)
    end_time = time.time()
    end_mem = round(memory_usage(-1, interval=0.1, timeout=1)[0], 2)
    execution_time = round(end_time - peak_metrics["start_time"], 2)
    peak_metrics["energy"] = abs(round(peak_metrics["energy"], 2))
    memory_used = abs(round(end_mem - peak_metrics["start_mem"], 2))
    cpu_used = abs(round(end_cpu - peak_metrics["start_cpu"], 2))
    peak_metrics["memory"] = abs(round(peak_metrics["memory"], 2))

    print(f"Execution time: {execution_time} seconds")
    print(f"Memory used: {memory_used} MiB")
    print(f"CPU used: {cpu_used}%")
    print(f"Peak Memory: {peak_metrics['memory']} MiB")
    print(f"Peak CPU: {peak_metrics['cpu']} %")
    print(f"Energy Used: {peak_metrics['energy']} J")

    response_data["execution_time"] = f"{execution_time} seconds"
    response_data["memory_used"] = f"{memory_used} MiB"
    response_data["energy_used"] = f"{peak_metrics['energy']} J"
    response_data["cpu_used"] = f"{cpu_used} %"
    response_data["peak_memory"] = f"{peak_metrics['memory']} MiB"
    response_data["peak_cpu"] = f"{peak_metrics['cpu']} %"
    response_data["responses"] = True
    if is_simulation:
        question_obj = Question.objects.get(question=response_data["question"])
        model_obj = Model.objects.get(model_value=response_data["model"])
        response_obj, _ = Response.objects.get_or_create(
            question=question_obj, model=model_obj
        )
        response_obj.execution_time = execution_time
        response_obj.energy_usage = peak_metrics["energy"]
        response_obj.memory_usage = memory_used
        response_obj.save()


# Query each LLM model with all questions and save the responses in database for plotting
def simulate():
    questions = Question.objects.all().values_list("question", flat=True)
    models = Model.objects.all().values_list("model_value", flat=True)
    model_question_pairs = []
    for model in models:
        for question in questions:
            pair = (model, question)
            model_question_pairs.append(pair)
    # Randomizing the list so that smaller and larger models aren't clustered together
    random.shuffle(model_question_pairs)
    for model, question in model_question_pairs:
        response_data = {
            "response": "",
            "question": "",
            "responses": False,
            "model": model,
            "question": question,
        }
        start_threads(response_data, True)


# Start two threads: get LLM response and log resource usage
def start_threads(response_data, is_simulation=False):
    start_power = get_power()
    peak_metrics = initialize_peak_metrics(start_power)

    ollama_thread = threading.Thread(
        target=get_response_from_ollama,
        args=(response_data, peak_metrics),
    )
    monitor_thread = threading.Thread(target=monitor_resources, args=(peak_metrics,))

    ollama_thread.start()
    monitor_thread.start()

    ollama_thread.join()
    monitor_thread.join()
    report_resource_usage(peak_metrics, response_data, is_simulation)


# Plot graphs based on database values
def plot():
    model_objs = Model.objects.all()
    model_names = [model_obj.model_name for model_obj in model_objs]
    model_parameters = [model_obj.parameters for model_obj in model_objs]
    questions = Question.objects.all()
    execution_times_all = []
    energy_uses_all = []
    memory_uses_all = []
    for model in model_objs:
        execution_times = []
        energy_uses = []
        memory_uses = []
        for question in questions:
            resp = Response.objects.filter(model=model, question=question).first()
            if resp is None:
                continue
            execution_times.append(resp.execution_time)
            energy_uses.append(resp.energy_usage)
            memory_uses.append(resp.memory_usage)
        execution_times_all.append(execution_times)
        energy_uses_all.append(energy_uses)
        memory_uses_all.append(memory_uses)

    for i, model_name in enumerate(model_names):
        # Calculating averages and standard deviations for each model
        avg_execution_time = round(np.mean(execution_times_all[i]), 2)
        std_execution_time = round(np.std(execution_times_all[i]), 2)
        avg_energy_use = round(np.mean(energy_uses_all[i]), 2)
        std_energy_use = round(np.std(energy_uses_all[i]), 2)
        avg_memory_use = round(np.mean(memory_uses_all[i]), 2)
        std_memory_use = round(np.std(memory_uses_all[i]), 2)
        print("Model =>", model_name)
        print(f"Average Execution Time: {avg_execution_time} seconds")
        print(f"Standard Deviation Execution Time: {std_execution_time} seconds")
        print(f"Average Energy Use: {avg_energy_use} J")
        print(f"Standard Deviation Energy Use: {std_energy_use} J")
        print(f"Average Memory Use: {avg_memory_use} MiB")
        print(f"Standard Deviation Memory Use: {std_memory_use} MiB")
        print("-" * 60)

        # Data for plotting
        categories = ["Execution Time", "Energy Use", "Memory Use"]
        averages = [avg_execution_time, avg_energy_use, avg_memory_use]
        std_devs = [std_execution_time, std_energy_use, std_memory_use]

        # Creating the bar plot with error bars for each model
        plt.figure(figsize=(10, 6))
        plt.bar(
            categories,
            averages,
            yerr=std_devs,
            capsize=10,
            color=["blue", "green", "red"],
        )
        plt.xlabel("Metric")
        plt.ylabel("Values")
        plt.title(f"Model Performance - {model_name} ({model_parameters[i]})")

        # Save the plot as a PNG file
        filename = f"{model_name.replace(' ', '_')}.png"
        plt.savefig(filename)
        plt.close()  # Close the plot to free memory
