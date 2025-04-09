import requests
import csv
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union
from datetime import datetime

from mactop_report.utils import DEFAULT_PORT, EXPECTED_METRIC_FIELDS, get_daily_csv_path

def check_mactop_running(port: int) -> bool:
    """
    Check if mactop is running by attempting to access its metrics endpoint.
    
    Args:
        port: The port mactop is expected to be running on.
        
    Returns:
        True if mactop is accessible, False otherwise.
    """
    try:
        response = requests.get(f"http://localhost:{port}/metrics", timeout=1)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def start_mactop_subprocess(port: int) -> Optional[subprocess.Popen]:
    """
    Attempt to start mactop as a subprocess.
    
    Args:
        port: The port to run mactop on.
        
    Returns:
        The subprocess.Popen object if successful, None otherwise.
    """
    try:
        print(f"Attempting to start mactop on port {port}...")
        print("Note: sudo permission may be required. You might be prompted for your password.")
        
        # Start mactop with sudo
        process = subprocess.Popen(
            ["sudo", "mactop", "-p", str(port), "-i", "250"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait briefly to give mactop time to start
        time.sleep(2)
        
        # Check if mactop is now running
        if check_mactop_running(port):
            print(f"mactop started successfully on port {port}")
            return process
        else:
            print("Failed to start mactop. Is it installed correctly?")
            return None
    except Exception as e:
        print(f"Error starting mactop: {e}")
        return None

def fetch_and_parse_metrics(port: int) -> Optional[Dict[str, float]]:
    """
    Fetch metrics from mactop and parse them into a dictionary.
    
    Args:
        port: The port mactop is running on.
        
    Returns:
        Dictionary of metrics or None if fetching fails.
    """
    try:
        response = requests.get(f"http://localhost:{port}/metrics", timeout=1)
        if response.status_code != 200:
            return None
        
        # Parse Prometheus text format
        metrics = {}
        for line in response.text.split('\n'):
            # Skip comment lines and empty lines
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse metric lines in the format "name value"
            parts = line.split()
            if len(parts) == 2:
                name, value = parts
                # Convert numeric values to float
                try:
                    metrics[name] = float(value)
                except ValueError:
                    # Skip non-numeric values
                    pass
        
        return metrics
    except requests.exceptions.RequestException:
        return None

def ensure_csv_header(file_path: Path, fields: List[str]) -> None:
    """
    Ensure the CSV file has the correct header. If the file doesn't exist or is empty,
    write the header row.
    
    Args:
        file_path: Path to the CSV file.
        fields: List of field names for the header.
    """
    # If file doesn't exist, create it and write header
    if not file_path.exists() or file_path.stat().st_size == 0:
        with open(file_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(fields)

def append_metrics_batch_to_csv(file_path: Path, metrics_batch: List[Dict[str, Union[str, float]]], fields: List[str]) -> None:
    """
    Append a batch of metrics to the CSV file.
    
    Args:
        file_path: Path to the CSV file.
        metrics_batch: List of dictionaries containing the metrics data.
        fields: List of field names in the expected order.
    """
    with open(file_path, 'a', newline='') as f:
        writer = csv.writer(f)
        
        # Write each row of metrics in the correct field order
        for metrics in metrics_batch:
            row = [metrics.get(field, '') for field in fields]
            writer.writerow(row)

def recording_session(port: int, interval: float, data_dir: Path, batch_size: int = 60) -> None:
    """
    Start a recording session to collect metrics from mactop.
    
    Args:
        port: The port mactop is running on.
        interval: Interval between metric collections in seconds.
        data_dir: Directory to store the CSV files.
        batch_size: Number of metrics to collect before writing to the CSV file.
    """
    # Check if mactop is running, attempt to start it if not
    mactop_process = None
    if not check_mactop_running(port):
        mactop_process = start_mactop_subprocess(port)
        if not mactop_process:
            print("Could not start mactop. Please ensure it is installed correctly.")
            return
    
    # Set up the CSV file
    csv_path = get_daily_csv_path(data_dir)
    ensure_csv_header(csv_path, EXPECTED_METRIC_FIELDS)
    
    # Initialize the buffer
    metrics_buffer = []
    
    try:
        print(f"Recording metrics every {interval} seconds. Press Ctrl+C to stop.")
        
        while True:
            # Fetch metrics
            metrics = fetch_and_parse_metrics(port)
            
            if metrics:
                # Add timestamp
                metrics_with_timestamp = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    **metrics
                }
                
                # Add to buffer
                metrics_buffer.append(metrics_with_timestamp)
                
                # Write to CSV if buffer reaches batch size
                if len(metrics_buffer) >= batch_size:
                    append_metrics_batch_to_csv(csv_path, metrics_buffer, EXPECTED_METRIC_FIELDS)
                    metrics_buffer = []
                    # Check for a new day, create a new file if needed
                    new_csv_path = get_daily_csv_path(data_dir)
                    if new_csv_path != csv_path:
                        csv_path = new_csv_path
                        ensure_csv_header(csv_path, EXPECTED_METRIC_FIELDS)
            
            # Sleep until the next interval
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print("\nStopping recording session...")
    finally:
        # Write any remaining metrics to the CSV
        if metrics_buffer:
            append_metrics_batch_to_csv(csv_path, metrics_buffer, EXPECTED_METRIC_FIELDS)
        
        # Terminate mactop if we started it
        if mactop_process:
            print("Terminating mactop process...")
            mactop_process.terminate() 