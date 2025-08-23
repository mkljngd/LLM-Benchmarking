import re
import subprocess
import time
import ollama
import psutil
from memory_profiler import memory_usage


def get_all_models():
    models_response = ollama.list()
    models = models_response["models"]
    return [m["model"] for m in models]


# Initalize required parameters
def initialize_peak_metrics(start_power):
    return {
        "memory": 0.0,
        "cpu": 0.0,
        "monitor": True,
        "start_time": time.time(),
        "start_mem": memory_usage(-1, interval=0.1, timeout=1)[0],
        "cpu_samples": [],  # <— add
        "end_power": start_power,
        "energy": 0.0,
    }


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


# Get current memory usage, CPU usage, and power consumption
def get_current_resource_usage():
    current_mem = memory_usage(-1, interval=0.1, timeout=1)[0]
    current_cpu = psutil.cpu_percent(interval=0.1)
    current_power = get_power()
    return (current_mem, current_cpu, current_power)


#  calculate energy usage in joules based on the difference in power consumption over a given time period.
def get_energy_usage(current_power, time=10.0):
    # Convert power to watts (1 watt = 1000 milliwatts)
    power_W = current_power / 1000
    energy_joules = power_W * time
    return energy_joules


def update_peak_metrics(peak_metrics, current_mem, current_cpu):
    peak_metrics["memory"] = max(peak_metrics["memory"], current_mem)
    peak_metrics["cpu"] = max(peak_metrics["cpu"], current_cpu)
    peak_metrics["cpu_samples"].append(current_cpu)


# Calculate, show and conditionally update resource usage values in database
def report_resource_usage(peak_metrics, response_data, is_simulation=False):
    end_time = time.time()
    end_mem = round(memory_usage(-1, interval=0.1, timeout=1)[0], 2)
    execution_time = round(end_time - peak_metrics["start_time"], 2)

    avg_cpu = round(
        sum(peak_metrics["cpu_samples"]) / max(1, len(peak_metrics["cpu_samples"])), 2
    )
    peak_cpu = round(peak_metrics["cpu"], 2)
    peak_mem = round(peak_metrics["memory"], 2)
    memory_used = abs(round(end_mem - peak_metrics["start_mem"], 2))
    energy = abs(round(peak_metrics["energy"], 2))

    print(f"Execution time: {execution_time} seconds")
    print(f"Memory used: {memory_used} MiB")
    print(f"Avg CPU: {avg_cpu}%")
    print(f"Peak Memory: {peak_mem} MiB")
    print(f"Peak CPU: {peak_cpu} %")
    print(f"Energy Used: {energy} J")

    response_data["execution_time"] = f"{execution_time} seconds"
    response_data["memory_used"] = f"{memory_used} MiB"
    response_data["energy_used"] = f"{energy} J"
    response_data["cpu_used"] = f"{avg_cpu} %"
    response_data["peak_memory"] = f"{peak_mem} MiB"
    response_data["peak_cpu"] = f"{peak_cpu} %"
    response_data["responses"] = True


# Continuously monitor resource usage (memory, CPU, power) and update peak metrics accordingly
def monitor_resources(peak_metrics, sample_interval=0.8):
    while peak_metrics.get("monitor", False):
        loop_start = time.time()
        current_mem = memory_usage(-1, interval=0.1, timeout=1)[0]
        current_cpu = psutil.cpu_percent(interval=0.1)
        current_power = get_power()  # now cheap-ish, and not every 100ms

        update_peak_metrics(peak_metrics, current_mem, current_cpu)

        if current_power is not None:
            elapsed = time.time() - loop_start
            peak_metrics["energy"] += get_energy_usage(current_power, elapsed)

        time.sleep(sample_interval)


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
