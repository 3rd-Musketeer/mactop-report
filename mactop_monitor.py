#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import requests
import csv
import time
import datetime
import sys
import subprocess
import signal
import os
import json
import statistics
from typing import Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box
from rich.prompt import Prompt

# Initialize Typer app
app = typer.Typer(help="MacTop Monitor - Track and visualize system performance metrics")
console = Console()

# Default configuration
DEFAULT_CSV_FILENAME = "mactop_data.csv"
DEFAULT_PORT = 8888
DEFAULT_INTERVAL = 1.0
MACTOP_CMD = ["mactop", "-p", f"{DEFAULT_PORT}", "-i", "250"]  # 250ms update interval for mactop
METRICS_URL_TEMPLATE = "http://localhost:{}/metrics"

# CSV fields
CSV_FIELDS = [
    "timestamp",
    "cpu_usage_percent",
    "gpu_freq_mhz",
    "gpu_usage_percent",
    "memory_total",
    "memory_used",
    "memory_swap_total",
    "memory_swap_used",
    "power_cpu",
    "power_gpu",
    "power_total",
]

# Metric pattern for parsing Prometheus format
METRIC_PATTERN = re.compile(
    r'^(?P<metric_name>\w+)(?:\{(?P<labels>[^}]+)\})?\s+(?P<value>[-+]?[\d\.eE]+)$'
)

def start_mactop(port: int = DEFAULT_PORT) -> subprocess.Popen:
    """
    Start mactop in Prometheus mode on specified port
    """
    cmd = MACTOP_CMD.copy()
    cmd[2] = str(port)
    
    try:
        # First check if we can access the metrics - mactop might already be running
        if fetch_metrics(port) is not None:
            console.print(f"[green]mactop is already running on port {port}[/green]")
            return None
            
        # We need sudo to run mactop
        sudo_cmd = ["sudo"] + cmd
        
        console.print(f"[yellow]mactop requires sudo privileges to run.[/yellow]")
        console.print(f"[yellow]Attempting to start mactop with sudo...[/yellow]")
        
        proc = subprocess.Popen(sudo_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)  # Wait for mactop to initialize
        
        # Check if it started successfully
        if fetch_metrics(port) is not None:
            console.print(f"[green]mactop started on port {port} (PID: {proc.pid})[/green]")
            return proc
        else:
            # Process started but metrics aren't available
            proc.terminate()
            raise Exception("mactop started but metrics endpoint is not available")
            
    except Exception as e:
        console.print(f"[red]Error starting mactop: {e}[/red]")
        console.print(f"[yellow]Please start mactop manually with:[/yellow]")
        console.print(f"[bold]sudo mactop -p {port} -i 250[/bold]")
        console.print(f"[yellow]Then run this script again.[/yellow]")
        sys.exit(1)

def fetch_metrics(port: int = DEFAULT_PORT) -> Optional[str]:
    """
    Fetch metrics from mactop's Prometheus endpoint
    """
    metrics_url = METRICS_URL_TEMPLATE.format(port)
    try:
        response = requests.get(metrics_url, timeout=5)
        response.raise_for_status()
        return response.text
    except Exception as e:
        console.print(f"[yellow]Error fetching metrics: {e}[/yellow]")
        return None

def parse_metrics(text: str) -> Dict[str, float]:
    """
    Parse Prometheus format metrics into a dictionary
    """
    results = {}
    if not text:
        return results
        
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
            
        match = METRIC_PATTERN.match(line)
        if match:
            metric_name = match.group("metric_name")
            labels_str = match.group("labels")
            try:
                value = float(match.group("value"))
            except ValueError:
                continue

            # Without labels
            if not labels_str:
                if metric_name == "mactop_cpu_usage_percent":
                    results["cpu_usage_percent"] = value
                elif metric_name == "mactop_gpu_freq_mhz":
                    results["gpu_freq_mhz"] = value
                elif metric_name == "mactop_gpu_usage_percent":
                    results["gpu_usage_percent"] = value
                else:
                    results[metric_name] = value
            else:
                # Parse labels
                label_parts = labels_str.split(',')
                for part in label_parts:
                    if '=' in part:
                        label_key, label_value = part.split('=', 1)
                        label_key = label_key.strip()
                        label_value = label_value.strip().strip('"')
                        
                        if metric_name == "mactop_memory_gb" and label_key == "type":
                            if label_value == "swap_total":
                                results["memory_swap_total"] = value
                            elif label_value == "swap_used":
                                results["memory_swap_used"] = value
                            elif label_value == "total":
                                results["memory_total"] = value
                            elif label_value == "used":
                                results["memory_used"] = value
                        elif metric_name == "mactop_power_watts" and label_key == "component":
                            if label_value == "cpu":
                                results["power_cpu"] = value
                            elif label_value == "gpu":
                                results["power_gpu"] = value
                            elif label_value == "total":
                                results["power_total"] = value
    
    return results

def ensure_csv_file(filename: str, overwrite: bool = False) -> None:
    """
    Ensure CSV file exists with proper headers
    """
    if overwrite or not os.path.exists(filename):
        with open(filename, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
            writer.writeheader()
            console.print(f"[green]Created new CSV file: {filename}[/green]")

def write_metrics_to_csv(metrics: Dict[str, Union[float, str]], filename: str) -> None:
    """
    Write metrics to CSV file
    """
    # Ensure all fields are present
    for field in CSV_FIELDS:
        if field not in metrics and field != "timestamp":
            metrics[field] = ""
            
    try:
        with open(filename, "a", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDS)
            writer.writerow(metrics)
    except Exception as e:
        console.print(f"[red]Error writing to CSV: {e}[/red]")

def display_recording_status(metrics: Dict[str, Union[float, str]], iteration: int) -> None:
    """
    Display current recording status
    """
    if iteration % 5 == 0:  # Only update display every 5 iterations to reduce flicker
        cpu = metrics.get("cpu_usage_percent", 0)
        gpu = metrics.get("gpu_usage_percent", 0)
        ram_total = metrics.get("memory_total", 0)
        ram_used = metrics.get("memory_used", 0)
        ram_percent = (ram_used / ram_total * 100) if ram_total > 0 else 0
        
        console.print(f"Recording #{iteration}: CPU: {cpu:.1f}%, GPU: {gpu:.1f}%, RAM: {ram_percent:.1f}%")

@app.command("record")
def record_metrics(
    file: str = typer.Option(DEFAULT_CSV_FILENAME, help="CSV file to record data"),
    interval: float = typer.Option(DEFAULT_INTERVAL, help="Sampling interval in seconds"),
    port: int = typer.Option(DEFAULT_PORT, help="mactop Prometheus port"),
    append: bool = typer.Option(True, help="Append to existing file if True, otherwise create new"),
    no_mactop: bool = typer.Option(False, help="Don't try to start mactop, assume it's already running"),
):
    """
    Record performance metrics from mactop to a CSV file
    """
    console.print(Panel(f"[bold]MacTop Monitor - Recording[/bold]", 
                        subtitle=f"File: {file}, Interval: {interval}s"))
    
    # Setup CSV file
    ensure_csv_file(file, not append)
    
    # Check if mactop is already running
    mactop_proc = None
    try:
        # Try to fetch metrics first to see if mactop is already running
        if fetch_metrics(port) is None:
            if no_mactop:
                console.print("[yellow]mactop not detected. Please start it manually with:[/yellow]")
                console.print(f"[bold]sudo mactop -p {port} -i 250[/bold]")
                console.print("[yellow]Then run this script again.[/yellow]")
                return
            else:
                console.print("[yellow]mactop not detected, attempting to start it...[/yellow]")
                mactop_proc = start_mactop(port)
                # Double-check we can get metrics
                if fetch_metrics(port) is None:
                    console.print("[red]Failed to get metrics even after attempting to start mactop.[/red]")
                    console.print("[yellow]Please start mactop manually and try again with --no-mactop flag.[/yellow]")
                    return
        else:
            console.print("[green]mactop is already running, using existing instance[/green]")
    
        # Register signal handlers for graceful exit
        def signal_handler(sig, frame):
            console.print("\n[yellow]Stopping recording...[/yellow]")
            if mactop_proc:
                console.print("[yellow]Terminating mactop...[/yellow]")
                mactop_proc.terminate()
                try:
                    mactop_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    mactop_proc.kill()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Main recording loop
        iteration = 0
        console.print("[green]Recording started. Press Ctrl+C to stop.[/green]")
        
        while True:
            iteration += 1
            timestamp = datetime.now().isoformat()
            
            # Fetch and parse metrics
            content = fetch_metrics(port)
            if content:
                metrics = parse_metrics(content)
                # Add timestamp
                metrics["timestamp"] = timestamp
                # Write to CSV
                write_metrics_to_csv(metrics, file)
                # Display status
                display_recording_status(metrics, iteration)
            else:
                console.print(f"[yellow]No data available at {timestamp}[/yellow]")
                
            time.sleep(interval)
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Recording stopped by user[/yellow]")
    finally:
        if mactop_proc:
            console.print("[yellow]Terminating mactop...[/yellow]")
            mactop_proc.terminate()
            try:
                mactop_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mactop_proc.kill()
        console.print(f"[green]Recording finished. Data saved to {file}[/green]")

def read_csv_data(file: str) -> List[Dict[str, Union[float, str]]]:
    """
    Read and parse CSV data file
    """
    if not os.path.exists(file):
        console.print(f"[red]Error: File {file} not found[/red]")
        sys.exit(1)
        
    data = []
    try:
        with open(file, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Convert numeric values to float
                for key, value in row.items():
                    if key != "timestamp" and value:
                        try:
                            row[key] = float(value)
                        except ValueError:
                            pass
                data.append(row)
    except Exception as e:
        console.print(f"[red]Error reading CSV file: {e}[/red]")
        sys.exit(1)
        
    return data

def calculate_statistics(data: List[Dict[str, Union[float, str]]], metric: str) -> Dict[str, float]:
    """
    Calculate statistics for a given metric
    """
    values = [float(row[metric]) for row in data if metric in row and row[metric] != ""]
    
    if not values:
        return {
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "p75": 0.0,
            "p95": 0.0,
            "std_dev": 0.0,
            "variance": 0.0
        }
        
    values.sort()
    n = len(values)
    
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / n,
        "median": values[n // 2] if n % 2 == 1 else (values[n // 2 - 1] + values[n // 2]) / 2,
        "p75": values[int(n * 0.75)],
        "p95": values[int(n * 0.95)],
        "std_dev": statistics.stdev(values) if len(values) > 1 else 0,
        "variance": statistics.variance(values) if len(values) > 1 else 0
    }

def find_peak_window(data: List[Dict[str, Union[float, str]]], metric: str, window_minutes: int = 15) -> Tuple[int, float]:
    """
    Find the peak window of specified duration based on average metric value
    Returns (start_index, average_value)
    """
    if not data or len(data) < 2:
        return (0, 0.0)
        
    # Parse timestamps
    try:
        for item in data:
            if isinstance(item["timestamp"], str):
                item["timestamp_obj"] = datetime.fromisoformat(item["timestamp"])
    except (ValueError, KeyError):
        console.print("[red]Error parsing timestamps in data[/red]")
        return (0, 0.0)
    
    # Find time span of data
    start_time = min(item["timestamp_obj"] for item in data)
    end_time = max(item["timestamp_obj"] for item in data)
    
    # If data span is less than window, use entire dataset
    if (end_time - start_time).total_seconds() < window_minutes * 60:
        values = [float(row[metric]) for row in data if metric in row and row[metric] != ""]
        return (0, sum(values) / len(values) if values else 0.0)
    
    # Find highest average window
    highest_avg = 0.0
    best_start_idx = 0
    
    for i in range(len(data) - 1):
        window_start = data[i]["timestamp_obj"]
        window_end = window_start + timedelta(minutes=window_minutes)
        
        # Get values in this window
        window_values = []
        for j in range(i, len(data)):
            if data[j]["timestamp_obj"] > window_end:
                break
            if metric in data[j] and data[j][metric] != "":
                window_values.append(float(data[j][metric]))
        
        if window_values:
            window_avg = sum(window_values) / len(window_values)
            if window_avg > highest_avg:
                highest_avg = window_avg
                best_start_idx = i
    
    return (best_start_idx, highest_avg)

@app.command("analyze")
def analyze_data(
    file: str = typer.Option(DEFAULT_CSV_FILENAME, help="CSV file to analyze"),
    metrics: str = typer.Option("cpu,gpu,ram,swap", help="Metrics to analyze (comma-separated)")
):
    """
    Analyze recorded metric data and display statistics
    """
    console.print(Panel(f"[bold]MacTop Monitor - Analysis[/bold]", subtitle=f"File: {file}"))
    
    # Parse metrics list
    metrics_list = [m.strip().lower() for m in metrics.split(",")]
    
    # Read data from CSV
    data = read_csv_data(file)
    if not data:
        console.print("[yellow]No data found in file.[/yellow]")
        return
        
    console.print(f"[green]Loaded {len(data)} data points from {file}[/green]")
    
    # Create results table
    table = Table(title="Performance Metrics Analysis")
    table.add_column("Metric", style="cyan")
    table.add_column("Min", justify="right")
    table.add_column("Max", justify="right")
    table.add_column("Avg", justify="right")
    table.add_column("Median", justify="right")
    table.add_column("75th %", justify="right")
    table.add_column("95th %", justify="right")
    table.add_column("Std Dev", justify="right")
    
    # Analyze each requested metric
    for metric_key in metrics_list:
        if metric_key == "cpu":
            metric_name = "cpu_usage_percent"
            display_name = "CPU Usage"
            unit = "%"
        elif metric_key == "gpu":
            metric_name = "gpu_usage_percent"
            display_name = "GPU Usage"
            unit = "%"
        elif metric_key == "ram":
            # For RAM we need to calculate percentage
            if all(key in data[0] for key in ["memory_total", "memory_used"]):
                for item in data:
                    if "memory_total" in item and "memory_used" in item:
                        # Convert empty strings to 0
                        memory_total = float(item["memory_total"]) if item["memory_total"] != "" else 0
                        memory_used = float(item["memory_used"]) if item["memory_used"] != "" else 0
                        
                        if memory_total > 0:
                            item["ram_percent"] = (memory_used / memory_total) * 100
                        else:
                            item["ram_percent"] = 0
                metric_name = "ram_percent"
                display_name = "RAM Usage"
                unit = "%"
            else:
                console.print("[yellow]RAM data not available in this dataset[/yellow]")
                continue
        elif metric_key == "swap":
            # Similar calculation for swap
            if all(key in data[0] for key in ["memory_swap_total", "memory_swap_used"]):
                for item in data:
                    if "memory_swap_total" in item and "memory_swap_used" in item:
                        # Convert empty strings to 0
                        swap_total = float(item["memory_swap_total"]) if item["memory_swap_total"] != "" else 0
                        swap_used = float(item["memory_swap_used"]) if item["memory_swap_used"] != "" else 0
                        
                        if swap_total > 0:
                            item["swap_percent"] = (swap_used / swap_total) * 100
                        else:
                            item["swap_percent"] = 0
                metric_name = "swap_percent"
                display_name = "SWAP Usage"
                unit = "%"
            else:
                console.print("[yellow]SWAP data not available in this dataset[/yellow]")
                continue
        else:
            # Try to use the metric name directly
            metric_name = metric_key
            display_name = metric_key.replace("_", " ").title()
            unit = ""  # Unknown unit
            
            # Check if metric exists in data
            if not any(metric_name in item for item in data):
                console.print(f"[yellow]Metric '{metric_name}' not found in data[/yellow]")
                continue
                
        # Calculate statistics
        stats = calculate_statistics(data, metric_name)
        
        # Add to table
        table.add_row(
            display_name,
            f"{stats['min']:.1f}{unit}",
            f"{stats['max']:.1f}{unit}",
            f"{stats['mean']:.1f}{unit}",
            f"{stats['median']:.1f}{unit}",
            f"{stats['p75']:.1f}{unit}",
            f"{stats['p95']:.1f}{unit}",
            f"{stats['std_dev']:.1f}{unit}"
        )
        
        # Find peak window for this metric
        peak_idx, peak_avg = find_peak_window(data, metric_name)
        if peak_idx > 0:
            try:
                peak_time = data[peak_idx]["timestamp_obj"]
                console.print(f"[cyan]Peak {display_name} period:[/cyan] "
                              f"{peak_time.strftime('%H:%M:%S')} - "
                              f"{(peak_time + timedelta(minutes=15)).strftime('%H:%M:%S')}, "
                              f"Average: {peak_avg:.1f}{unit}")
            except (KeyError, AttributeError):
                pass
    
    # Display the table
    console.print(table)

@app.command("view")
def view_dashboard(
    file: str = typer.Option(DEFAULT_CSV_FILENAME, help="CSV file to visualize"),
    interval: float = typer.Option(DEFAULT_INTERVAL, help="Update interval in seconds")
):
    """
    Launch an interactive dashboard to visualize performance metrics
    """
    console.print(Panel(f"[bold]MacTop Monitor - Dashboard[/bold]", subtitle=f"File: {file}"))
    
    try:
        from dashboard import run_dashboard
        run_dashboard(file, interval)
    except ImportError:
        console.print("[yellow]Dashboard module not available.[/yellow]")
        console.print("[green]Use the analyze command for now to see statistics.[/green]")

if __name__ == "__main__":
    app() 