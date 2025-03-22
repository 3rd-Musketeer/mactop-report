#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MacTop Monitor - Dashboard Module
Provides interactive TUI visualization of performance metrics
"""

import time
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, BarColumn, TextColumn
from rich import box
from rich.live import Live
from rich.prompt import Prompt

# Try to import textual for more advanced TUI features
# (this is optional as we can fall back to rich.live)
try:
    from textual.app import App
    from textual.widgets import Header, Footer, Static
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

# Constants
DEFAULT_UPDATE_INTERVAL = 1.0  # seconds
DEFAULT_CHART_WIDTH = 60
DEFAULT_CHART_HEIGHT = 10

class DashboardData:
    """Class to handle data processing for the dashboard"""
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.data = []
        self.cpu_data = []
        self.gpu_data = []
        self.ram_data = []
        self.swap_data = []
        self.power_data = []
        self.timestamps = []
        self._load_data()
        
    def _load_data(self) -> None:
        """Load data from CSV file"""
        if not os.path.exists(self.data_file):
            raise FileNotFoundError(f"Data file {self.data_file} not found")
            
        self.data = []
        with open(self.data_file, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Convert numeric fields to float
                for key, value in row.items():
                    if key != "timestamp" and value:
                        try:
                            row[key] = float(value)
                        except ValueError:
                            pass
                self.data.append(row)
                
        # Process data into specific metric lists
        self._process_data()
    
    def _process_data(self) -> None:
        """Process raw data into specialized metric lists"""
        self.cpu_data = []
        self.gpu_data = []
        self.ram_data = []
        self.swap_data = []
        self.power_data = []
        self.timestamps = []
        
        for item in self.data:
            # Process timestamp
            try:
                if isinstance(item["timestamp"], str):
                    timestamp = datetime.fromisoformat(item["timestamp"])
                    self.timestamps.append(timestamp)
            except (ValueError, KeyError):
                # Use a dummy timestamp if parsing fails
                self.timestamps.append(datetime.now())
            
            # Process CPU
            if "cpu_usage_percent" in item and item["cpu_usage_percent"] != "":
                self.cpu_data.append(float(item["cpu_usage_percent"]))
            else:
                self.cpu_data.append(0.0)
                
            # Process GPU
            if "gpu_usage_percent" in item and item["gpu_usage_percent"] != "":
                self.gpu_data.append(float(item["gpu_usage_percent"]))
            else:
                self.gpu_data.append(0.0)
                
            # Process RAM
            if "memory_total" in item and "memory_used" in item:
                # Convert empty strings to 0
                memory_total = float(item["memory_total"]) if item["memory_total"] != "" else 0
                memory_used = float(item["memory_used"]) if item["memory_used"] != "" else 0
                
                if memory_total > 0:
                    ram_percent = (memory_used / memory_total) * 100
                    self.ram_data.append(ram_percent)
                else:
                    self.ram_data.append(0.0)
            else:
                self.ram_data.append(0.0)
                
            # Process SWAP
            if "memory_swap_total" in item and "memory_swap_used" in item:
                # Convert empty strings to 0
                swap_total = float(item["memory_swap_total"]) if item["memory_swap_total"] != "" else 0
                swap_used = float(item["memory_swap_used"]) if item["memory_swap_used"] != "" else 0
                
                if swap_total > 0:
                    swap_percent = (swap_used / swap_total) * 100
                    self.swap_data.append(swap_percent)
                else:
                    self.swap_data.append(0.0)
            else:
                self.swap_data.append(0.0)
                
            # Process Power
            if "power_total" in item and item["power_total"] != "":
                self.power_data.append(float(item["power_total"]))
            else:
                self.power_data.append(0.0)
    
    def reload_data(self) -> None:
        """Reload data from file (for live updates)"""
        self._load_data()
    
    def get_stats(self, metric_data: List[float]) -> Dict[str, float]:
        """Calculate statistics for a metric dataset"""
        if not metric_data:
            return {
                "min": 0.0,
                "max": 0.0,
                "mean": 0.0,
                "median": 0.0,
                "p75": 0.0,
                "p95": 0.0
            }
            
        # Sort a copy of the data for percentile calculations
        sorted_data = sorted(metric_data)
        n = len(sorted_data)
        
        return {
            "min": min(sorted_data),
            "max": max(sorted_data),
            "mean": sum(sorted_data) / n,
            "median": sorted_data[n // 2] if n % 2 == 1 else (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2,
            "p75": sorted_data[int(n * 0.75)],
            "p95": sorted_data[int(n * 0.95)]
        }
    
    def get_cpu_stats(self) -> Dict[str, float]:
        """Get CPU usage statistics"""
        return self.get_stats(self.cpu_data)
    
    def get_gpu_stats(self) -> Dict[str, float]:
        """Get GPU usage statistics"""
        return self.get_stats(self.gpu_data)
    
    def get_ram_stats(self) -> Dict[str, float]:
        """Get RAM usage statistics"""
        return self.get_stats(self.ram_data)
    
    def get_swap_stats(self) -> Dict[str, float]:
        """Get SWAP usage statistics"""
        return self.get_stats(self.swap_data)
        
    def get_current_values(self) -> Dict[str, float]:
        """Get the most recent values for all metrics"""
        if not self.data:
            return {
                "cpu": 0.0,
                "gpu": 0.0,
                "ram": 0.0,
                "swap": 0.0,
                "power": 0.0
            }
            
        return {
            "cpu": self.cpu_data[-1] if self.cpu_data else 0.0,
            "gpu": self.gpu_data[-1] if self.gpu_data else 0.0,
            "ram": self.ram_data[-1] if self.ram_data else 0.0,
            "swap": self.swap_data[-1] if self.swap_data else 0.0,
            "power": self.power_data[-1] if self.power_data else 0.0
        }
    
    def find_peak_window(self, metric_data: List[float], window_minutes: int = 15) -> Tuple[int, float]:
        """Find peak usage window for given metric data"""
        if not metric_data or len(metric_data) < 2 or len(self.timestamps) != len(metric_data):
            return (0, 0.0)
        
        # If data span is less than window, use entire dataset
        timespan = (self.timestamps[-1] - self.timestamps[0]).total_seconds()
        if timespan < window_minutes * 60:
            return (0, sum(metric_data) / len(metric_data))
        
        # Find highest average window
        highest_avg = 0.0
        best_start_idx = 0
        
        for i in range(len(metric_data) - 1):
            window_start = self.timestamps[i]
            window_end = window_start + timedelta(minutes=window_minutes)
            
            # Get values in this window
            window_values = []
            for j in range(i, min(len(self.timestamps), len(metric_data))):
                if self.timestamps[j] > window_end:
                    break
                window_values.append(metric_data[j])
            
            if window_values:
                window_avg = sum(window_values) / len(window_values)
                if window_avg > highest_avg:
                    highest_avg = window_avg
                    best_start_idx = i
        
        return (best_start_idx, highest_avg)

class SimpleSpark:
    """Simple sparkline renderer for rich"""
    
    @staticmethod
    def generate(values: List[float], width: int = 40, min_value: Optional[float] = None, 
                max_value: Optional[float] = None) -> str:
        """Generate a simple sparkline string"""
        if not values:
            return " " * width
            
        # Determine min and max if not provided
        if min_value is None:
            min_value = min(values)
        if max_value is None:
            max_value = max(values)
            
        # Ensure we have a range to work with
        value_range = max_value - min_value
        if value_range <= 0:
            value_range = 1.0
            
        # Select a subset of values that fit the width
        if len(values) > width:
            # Use recent values if we have too many
            step = len(values) / width
            sampled = []
            for i in range(width):
                idx = min(int(i * step), len(values) - 1)
                sampled.append(values[idx])
            values = sampled
        elif len(values) < width:
            # Pad with empty space if we have too few
            values = values + [values[-1] if values else 0] * (width - len(values))
            
        # Map to spark characters
        spark_chars = "▁▂▃▄▅▆▇█"
        result = ""
        for v in values:
            # Normalize value to 0-1 range
            normalized = (v - min_value) / value_range
            # Map to character index
            char_idx = min(int(normalized * len(spark_chars)), len(spark_chars) - 1)
            result += spark_chars[char_idx]
            
        return result

class SimpleProgressBar:
    """Simple progress bar renderer for rich"""
    
    @staticmethod
    def generate(value: float, width: int = 20, max_value: float = 100.0) -> str:
        """Generate a simple progress bar string"""
        fill_chars = "█"
        empty_chars = "▒"
        
        # Normalize value to 0-1 range
        normalized = min(1.0, max(0.0, value / max_value))
        
        # Calculate filled width
        filled_width = int(normalized * width)
        
        # Create bar
        bar = fill_chars * filled_width + empty_chars * (width - filled_width)
        
        return f"[{bar}] {value:.1f}%"

class RichDashboard:
    """Dashboard implementation using rich.live"""
    
    def __init__(self, data_file: str, update_interval: float = DEFAULT_UPDATE_INTERVAL):
        self.data = DashboardData(data_file)
        self.update_interval = update_interval
        self.console = Console()
        self.layout = Layout()
        self.current_view = "main"  # main, cpu, gpu, ram, swap
    
    def _generate_main_layout(self) -> Layout:
        """Generate the main dashboard layout"""
        layout = Layout()
        
        # Create header layout
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Setup header
        current = self.data.get_current_values()
        header_text = (
            "[bold white]MacTop Monitor[/bold white] | "
            f"CPU: {current['cpu']:.1f}% | "
            f"GPU: {current['gpu']:.1f}% | "
            f"RAM: {current['ram']:.1f}% | "
            f"SWAP: {current['swap']:.1f}%"
        )
        header = Panel(Text(header_text, justify="center"), border_style="cyan")
        layout["header"].update(header)
        
        # Setup body with metrics panels
        layout["body"].split_row(
            Layout(name="left_col"),
            Layout(name="right_col")
        )
        
        # Split columns into rows
        layout["left_col"].split(
            Layout(name="cpu_panel"),
            Layout(name="ram_panel")
        )
        
        layout["right_col"].split(
            Layout(name="gpu_panel"),
            Layout(name="stats_panel")
        )
        
        # Setup CPU panel
        cpu_stats = self.data.get_cpu_stats()
        cpu_spark = SimpleSpark.generate(self.data.cpu_data[-60:] if len(self.data.cpu_data) > 60 else self.data.cpu_data)
        cpu_panel = Panel(
            f"\n{cpu_spark}\n\n"
            f"Current: {current['cpu']:.1f}%  Max: {cpu_stats['max']:.1f}%  Avg: {cpu_stats['mean']:.1f}%\n"
            f"95th: {cpu_stats['p95']:.1f}%  75th: {cpu_stats['p75']:.1f}%  Median: {cpu_stats['median']:.1f}%",
            title="[bold]CPU Usage[/bold]", border_style="green"
        )
        layout["cpu_panel"].update(cpu_panel)
        
        # Setup GPU panel
        gpu_stats = self.data.get_gpu_stats()
        gpu_spark = SimpleSpark.generate(self.data.gpu_data[-60:] if len(self.data.gpu_data) > 60 else self.data.gpu_data)
        gpu_panel = Panel(
            f"\n{gpu_spark}\n\n"
            f"Current: {current['gpu']:.1f}%  Max: {gpu_stats['max']:.1f}%  Avg: {gpu_stats['mean']:.1f}%\n"
            f"95th: {gpu_stats['p95']:.1f}%  75th: {gpu_stats['p75']:.1f}%  Median: {gpu_stats['median']:.1f}%",
            title="[bold]GPU Usage[/bold]", border_style="magenta"
        )
        layout["gpu_panel"].update(gpu_panel)
        
        # Setup RAM panel
        ram_stats = self.data.get_ram_stats()
        ram_spark = SimpleSpark.generate(self.data.ram_data[-60:] if len(self.data.ram_data) > 60 else self.data.ram_data)
        ram_panel = Panel(
            f"\n{ram_spark}\n\n"
            f"Current: {current['ram']:.1f}%  Max: {ram_stats['max']:.1f}%  Avg: {ram_stats['mean']:.1f}%\n"
            f"95th: {ram_stats['p95']:.1f}%  75th: {ram_stats['p75']:.1f}%  Median: {ram_stats['median']:.1f}%",
            title="[bold]RAM Usage[/bold]", border_style="blue"
        )
        layout["ram_panel"].update(ram_panel)
        
        # Setup Stats panel with peak windows
        cpu_peak_idx, cpu_peak_avg = self.data.find_peak_window(self.data.cpu_data)
        gpu_peak_idx, gpu_peak_avg = self.data.find_peak_window(self.data.gpu_data)
        ram_peak_idx, ram_peak_avg = self.data.find_peak_window(self.data.ram_data)
        
        peak_info = ""
        if cpu_peak_idx > 0 and cpu_peak_idx < len(self.data.timestamps):
            peak_time = self.data.timestamps[cpu_peak_idx]
            peak_end = peak_time + timedelta(minutes=15)
            peak_info += f"CPU peak: {peak_time.strftime('%H:%M')} - {peak_end.strftime('%H:%M')} ({cpu_peak_avg:.1f}%)\n"
            
        if gpu_peak_idx > 0 and gpu_peak_idx < len(self.data.timestamps):
            peak_time = self.data.timestamps[gpu_peak_idx]
            peak_end = peak_time + timedelta(minutes=15)
            peak_info += f"GPU peak: {peak_time.strftime('%H:%M')} - {peak_end.strftime('%H:%M')} ({gpu_peak_avg:.1f}%)\n"
            
        if ram_peak_idx > 0 and ram_peak_idx < len(self.data.timestamps):
            peak_time = self.data.timestamps[ram_peak_idx]
            peak_end = peak_time + timedelta(minutes=15)
            peak_info += f"RAM peak: {peak_time.strftime('%H:%M')} - {peak_end.strftime('%H:%M')} ({ram_peak_avg:.1f}%)\n"
            
        # If we have power data, add that too
        power_info = ""
        if self.data.power_data:
            power_current = current['power']
            power_avg = sum(self.data.power_data) / len(self.data.power_data) if self.data.power_data else 0
            power_max = max(self.data.power_data) if self.data.power_data else 0
            power_info = f"\nPower: Current: {power_current:.1f}W  Avg: {power_avg:.1f}W  Max: {power_max:.1f}W"
        
        stats_panel = Panel(
            f"{peak_info}\n"
            f"Total samples: {len(self.data.data)}\n"
            f"Time range: {self.data.timestamps[0].strftime('%Y-%m-%d %H:%M')} - " 
            f"{self.data.timestamps[-1].strftime('%Y-%m-%d %H:%M')}" +
            power_info,
            title="[bold]Statistics[/bold]", border_style="yellow"
        )
        layout["stats_panel"].update(stats_panel)
        
        # Setup footer
        footer_text = "[q]uit | [r]eload | [1]CPU | [2]GPU | [3]RAM | [4]SWAP details"
        footer = Panel(Text(footer_text, justify="center"), border_style="cyan")
        layout["footer"].update(footer)
        
        return layout
    
    def _generate_detail_layout(self, metric: str) -> Layout:
        """Generate detail view layout for a specific metric"""
        layout = Layout()
        
        # Create header layout
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        # Get metric-specific data
        if metric == "cpu":
            title = "CPU Usage Details"
            color = "green"
            data = self.data.cpu_data
            stats = self.data.get_cpu_stats()
            current = self.data.get_current_values()["cpu"]
            peak_idx, peak_avg = self.data.find_peak_window(data)
        elif metric == "gpu":
            title = "GPU Usage Details"
            color = "magenta"
            data = self.data.gpu_data
            stats = self.data.get_gpu_stats()
            current = self.data.get_current_values()["gpu"]
            peak_idx, peak_avg = self.data.find_peak_window(data)
        elif metric == "ram":
            title = "RAM Usage Details"
            color = "blue"
            data = self.data.ram_data
            stats = self.data.get_ram_stats()
            current = self.data.get_current_values()["ram"]
            peak_idx, peak_avg = self.data.find_peak_window(data)
        elif metric == "swap":
            title = "SWAP Usage Details"
            color = "red"
            data = self.data.swap_data
            stats = self.data.get_swap_stats()
            current = self.data.get_current_values()["swap"]
            peak_idx, peak_avg = self.data.find_peak_window(data)
        else:
            return self._generate_main_layout()
        
        # Setup header
        header = Panel(
            Text(f"[bold white]{title}[/bold white]", justify="center"), 
            border_style=color
        )
        layout["header"].update(header)
        
        # Setup body with detailed panels
        layout["body"].split(
            Layout(name="chart_panel", size=10),
            Layout(name="stats_panel", size=8),
            Layout(name="peak_panel")
        )
        
        # Chart panel
        spark_line = SimpleSpark.generate(
            data[-100:] if len(data) > 100 else data, 
            width=80, 
            min_value=0, 
            max_value=max(100, stats["max"])
        )
        chart_panel = Panel(
            f"\n{spark_line}\n\n"
            f"Min: {stats['min']:.1f}%  Max: {stats['max']:.1f}%  Current: {current:.1f}%\n",
            title="[bold]Usage History[/bold]", 
            border_style=color
        )
        layout["chart_panel"].update(chart_panel)
        
        # Statistics panel
        stats_table = Table(box=box.SIMPLE)
        stats_table.add_column("Statistic", style="cyan")
        stats_table.add_column("Value", justify="right")
        
        stats_table.add_row("95th Percentile", f"{stats['p95']:.1f}%")
        stats_table.add_row("75th Percentile", f"{stats['p75']:.1f}%")
        stats_table.add_row("50th Percentile (Median)", f"{stats['median']:.1f}%")
        stats_table.add_row("Average", f"{stats['mean']:.1f}%")
        stats_table.add_row("Minimum", f"{stats['min']:.1f}%")
        stats_table.add_row("Maximum", f"{stats['max']:.1f}%")
        
        stats_panel = Panel(
            stats_table,
            title="[bold]Statistics[/bold]", 
            border_style=color
        )
        layout["stats_panel"].update(stats_panel)
        
        # Peak Usage panel
        peak_content = ""
        if peak_idx > 0 and peak_idx < len(self.data.timestamps):
            peak_time = self.data.timestamps[peak_idx]
            peak_end = peak_time + timedelta(minutes=15)
            
            # Find window surrounding peak (30 min before and after)
            window_start = peak_time - timedelta(minutes=30)
            window_end = peak_end + timedelta(minutes=30)
            
            # Get data for surrounding window
            window_data = []
            window_times = []
            for i, ts in enumerate(self.data.timestamps):
                if window_start <= ts <= window_end and i < len(data):
                    window_data.append(data[i])
                    window_times.append(ts)
            
            # Generate mini sparkline for the window
            window_spark = SimpleSpark.generate(
                window_data, 
                width=60, 
                min_value=0, 
                max_value=max(100, stats["max"])
            )
            
            peak_content = (
                f"Peak period: {peak_time.strftime('%H:%M:%S')} - {peak_end.strftime('%H:%M:%S')}\n"
                f"Average: {peak_avg:.1f}%  Maximum: {max(window_data) if window_data else 0:.1f}%\n\n"
                f"Activity surrounding peak period:\n\n"
                f"{window_spark}\n"
                f"{window_start.strftime('%H:%M')}{'':>30}{peak_time.strftime('%H:%M')}{'':>30}{window_end.strftime('%H:%M')}"
            )
        else:
            peak_content = "Insufficient data to identify peak period"
            
        peak_panel = Panel(
            peak_content,
            title="[bold]Peak Usage Period[/bold]", 
            border_style=color
        )
        layout["peak_panel"].update(peak_panel)
        
        # Setup footer
        footer_text = "[b]ack to main | [q]uit | [r]eload"
        footer = Panel(Text(footer_text, justify="center"), border_style="cyan")
        layout["footer"].update(footer)
        
        return layout
    
    def _update_layout(self) -> None:
        """Update layout based on current view"""
        if self.current_view == "main":
            self.layout = self._generate_main_layout()
        elif self.current_view in ["cpu", "gpu", "ram", "swap"]:
            self.layout = self._generate_detail_layout(self.current_view)
            
    def _handle_input(self, key: str) -> bool:
        """Handle user input, return False to exit"""
        if key.lower() == "q":
            return False
        elif key.lower() == "r":
            self.data.reload_data()
        elif key == "1":
            self.current_view = "cpu"
        elif key == "2":
            self.current_view = "gpu"
        elif key == "3":
            self.current_view = "ram" 
        elif key == "4":
            self.current_view = "swap"
        elif key.lower() == "b" and self.current_view != "main":
            self.current_view = "main"
        return True
            
    def run(self) -> None:
        """Run the dashboard"""
        self._update_layout()
        
        console = Console()
        console.print("[yellow]Starting dashboard... Press Ctrl+C to exit[/yellow]")
        
        try:
            # Use a simpler approach with regular updates without trying to capture keystrokes
            with Live(self.layout, refresh_per_second=1/self.update_interval, screen=True) as live:
                while True:
                    self.data.reload_data()
                    self._update_layout()
                    live.update(self.layout)
                    time.sleep(self.update_interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard stopped by user[/yellow]")
        except Exception as e:
            console.print(f"\n[red]Error in dashboard: {str(e)}[/red]")

# If textual is available, implement a more advanced dashboard
if TEXTUAL_AVAILABLE:
    class MacTopDashboard(App):
        """MacTop Monitor Dashboard using Textual"""
        
        def __init__(self, data_file: str, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.data_file = data_file
            self.data = DashboardData(data_file)
            
        def compose(self):
            """Compose the dashboard layout"""
            yield Header()
            yield Footer()
            # Implementation would go here
            
        def on_mount(self):
            """Ons dashboard mount"""
            self.set_interval(1, self.update_data)
            
        def update_data(self):
            """Update dashboard data"""
            self.data.reload_data()
            # Update UI elements

def run_dashboard(data_file: str, update_interval: float = DEFAULT_UPDATE_INTERVAL) -> None:
    """Run the appropriate dashboard based on available libraries"""
    
    console = Console()
    
    if not os.path.exists(data_file):
        console.print(f"[red]Error: Data file {data_file} not found[/red]")
        return
        
    try:
        # Fall back to rich.live only, as textual implementation might have issues
        dashboard = RichDashboard(data_file, update_interval)
        dashboard.run()
    except Exception as e:
        console.print(f"[red]Dashboard error: {str(e)}[/red]")
        console.print("[yellow]Falling back to simple text analysis...[/yellow]")
        
        # Provide a simple fallback display
        try:
            data = DashboardData(data_file)
            
            console.print("\n[bold cyan]MacTop Monitor - Summary[/bold cyan]")
            console.print(f"Data file: {data_file} ({len(data.data)} samples)")
            
            # CPU stats
            cpu_stats = data.get_cpu_stats()
            console.print("\n[bold green]CPU Usage[/bold green]")
            console.print(f"Avg: {cpu_stats['mean']:.1f}%  Max: {cpu_stats['max']:.1f}%  95th: {cpu_stats['p95']:.1f}%")
            
            # GPU stats
            gpu_stats = data.get_gpu_stats()
            console.print("\n[bold magenta]GPU Usage[/bold magenta]")
            console.print(f"Avg: {gpu_stats['mean']:.1f}%  Max: {gpu_stats['max']:.1f}%  95th: {gpu_stats['p95']:.1f}%")
            
            # RAM stats
            ram_stats = data.get_ram_stats()
            console.print("\n[bold blue]RAM Usage[/bold blue]")
            console.print(f"Avg: {ram_stats['mean']:.1f}%  Max: {ram_stats['max']:.1f}%  95th: {ram_stats['p95']:.1f}%")
            
            # SWAP stats
            swap_stats = data.get_swap_stats()
            console.print("\n[bold red]SWAP Usage[/bold red]")
            console.print(f"Avg: {swap_stats['mean']:.1f}%  Max: {swap_stats['max']:.1f}%  95th: {swap_stats['p95']:.1f}%")
            
        except Exception as inner_e:
            console.print(f"[red]Error displaying summary: {str(inner_e)}[/red]")
            console.print("[yellow]Please use the analyze command instead:[/yellow]")
            console.print("python mactop_monitor.py analyze")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MacTop Monitor Dashboard")
    parser.add_argument("--file", default="mactop_data.csv", help="CSV data file path")
    parser.add_argument("--interval", type=float, default=DEFAULT_UPDATE_INTERVAL, 
                      help="Update interval in seconds")
    
    args = parser.parse_args()
    run_dashboard(args.file, args.interval) 