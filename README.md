# LLM Performance Benchmarking Tool

A comprehensive Django-based application for benchmarking and monitoring the performance of local Language Learning Models (LLMs) using Ollama. This tool measures execution time, memory usage, CPU utilization, and energy consumption while interacting with various LLM models.

## Features

- **Multi-Model Support**: Automatically detects and benchmarks all locally available Ollama models
- **Resource Monitoring**: Real-time tracking of memory usage, CPU utilization, and energy consumption (macOS)
- **Batch Simulation**: Run automated benchmarks across multiple models and questions
- **Web Interface**: User-friendly Django web interface for interactive model testing
- **Data Persistence**: Redis-based storage for metrics and question sets
- **Visualization**: Automatic generation of performance charts with statistical analysis

## Architecture

### Core Components

- **Django Web Application**: Interactive interface for model testing
- **Simulation Engine**: Automated benchmarking system
- **Resource Monitor**: Multi-threaded performance tracking
- **Redis Backend**: Data storage for metrics and questions
- **Visualization Engine**: Statistical analysis and chart generation

## Prerequisites

- Python 3.8+
- Django 5.0+
- Redis server
- Ollama with installed models
- macOS (for power monitoring features)

## Dependencies

```
django
redis
ollama
matplotlib
numpy
memory-profiler
psutil
django-redis
django-debug-toolbar
```

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd llm-performance-tool
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Redis server**
   ```bash
   redis-server
   ```

4. **Ensure Ollama is running**
   ```bash
   ollama serve
   ```

## Usage

### Web Interface

Start the Django development server:
```bash
python manage.py runserver
```

Navigate to `http://localhost:8000` to access the interactive interface where you can:
- Select from available Ollama models
- Submit questions for real-time performance analysis
- View detailed resource usage metrics

### Batch Simulation

Run automated benchmarks across all models and questions:
```bash
python run_simulations.py
```

This will:
1. Clear previous metrics
2. Test each model with every question in the dataset
3. Generate performance charts for each model
4. Save statistical summaries and visualizations

### Question Management

Seed the system with custom questions:
```bash
python seed_questions.py questions.txt
```

**Format for questions.txt:**
```
# Comments start with #
What is the capital of France?
Explain quantum computing in simple terms.
Write a Python function to calculate fibonacci numbers.
```

## Performance Metrics

The tool tracks the following metrics for each model interaction:

- **Execution Time**: Total time to generate response (seconds)
- **Memory Usage**: Peak memory consumption (MiB)
- **CPU Utilization**: Peak CPU usage percentage
- **Energy Consumption**: Total energy used (Joules, macOS only)

## Output

### Console Output
Real-time metrics displayed during each interaction:
```
Execution time: 15.23 seconds
Memory used: 245.67 MiB
CPU used: 85.4%
Peak Memory: 512.34 MiB
Peak CPU: 92.1%
Energy Used: 23.45 J
```

### Statistical Analysis
Aggregate statistics for each model:
- Average and standard deviation for all metrics
- Performance comparisons across models
- Visual charts saved as PNG files

### Generated Charts
Automatic creation of bar charts showing:
- Average performance metrics with error bars
- Individual model performance profiles
- Statistical distributions

## Technical Implementation

### Multi-threaded Architecture
- **Main Thread**: Coordinates simulation workflow
- **Ollama Thread**: Handles LLM API communication
- **Monitor Thread**: Continuously tracks resource usage

### Energy Monitoring (macOS)
Uses `powermetrics` system command to measure real-time power consumption and calculate energy usage in Joules.

### Data Storage
Redis-based storage with efficient key-value structure:
- Questions stored in lists
- Metrics stored with model-question hash keys
- Batch operations for performance optimization


## Configuration

### Redis Connection
Default configuration connects to `redis://127.0.0.1:6379/1`. Modify in:
- `llm/redis_client.py` for direct Redis operations
- `llm/settings.py` for Django cache configuration

