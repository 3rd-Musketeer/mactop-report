import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import csv
import requests
from datetime import datetime

from mactop_report.record import (
    check_mactop_running,
    fetch_and_parse_metrics,
    ensure_csv_header,
    append_metrics_batch_to_csv,
    recording_session
)

# Test check_mactop_running function
def test_check_mactop_running_success():
    """Test that check_mactop_running returns True when mactop is running."""
    with patch('requests.get') as mock_get:
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        result = check_mactop_running(8888)
        
        # Verify the function returns True for a successful request
        assert result is True
        # Verify requests.get was called with the expected URL
        mock_get.assert_called_once_with('http://localhost:8888/metrics', timeout=1)

def test_check_mactop_running_failure_status_code():
    """Test that check_mactop_running returns False when mactop returns non-200 status."""
    with patch('requests.get') as mock_get:
        # Mock failed response with non-200 status code
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = check_mactop_running(8888)
        
        # Verify the function returns False for a non-200 status code
        assert result is False

def test_check_mactop_running_request_exception():
    """Test that check_mactop_running returns False when request raises an exception."""
    with patch('requests.get') as mock_get:
        # Mock request raising an exception
        mock_get.side_effect = requests.exceptions.RequestException()

        result = check_mactop_running(8888)
        
        # Verify the function returns False when an exception occurs
        assert result is False

# Test fetch_and_parse_metrics function
def test_fetch_and_parse_metrics_success():
    """Test that fetch_and_parse_metrics correctly parses Prometheus metrics."""
    with patch('requests.get') as mock_get:
        # Mock successful response with sample Prometheus metrics
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
# HELP cpu_usage_percent Current CPU usage in percent
# TYPE cpu_usage_percent gauge
cpu_usage_percent 25.5
# HELP memory_used Memory used in bytes
# TYPE memory_used gauge
memory_used 8589934592
# HELP memory_total Total memory in bytes
# TYPE memory_total gauge
memory_total 17179869184
"""
        mock_get.return_value = mock_response

        result = fetch_and_parse_metrics(8888)
        
        # Verify the function returns a dictionary with parsed metrics
        assert result == {
            'cpu_usage_percent': 25.5,
            'memory_used': 8589934592,
            'memory_total': 17179869184
        }

def test_fetch_and_parse_metrics_request_failure():
    """Test that fetch_and_parse_metrics returns None when request fails."""
    with patch('requests.get') as mock_get:
        # Mock request raising an exception
        mock_get.side_effect = requests.exceptions.RequestException()

        result = fetch_and_parse_metrics(8888)
        
        # Verify the function returns None when the request fails
        assert result is None

# Test ensure_csv_header function
def test_ensure_csv_header_new_file(tmp_path):
    """Test that ensure_csv_header writes header to a new file."""
    # Create a test CSV file path
    test_csv = tmp_path / "test.csv"
    test_fields = ["timestamp", "cpu_usage_percent", "memory_used"]
    
    # Call the function to write the header
    ensure_csv_header(test_csv, test_fields)
    
    # Verify the file was created with the correct header
    assert test_csv.exists()
    with open(test_csv, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == test_fields

def test_ensure_csv_header_existing_file_with_content(tmp_path):
    """Test that ensure_csv_header doesn't modify an existing file with content."""
    # Create a test CSV file with existing content
    test_csv = tmp_path / "test.csv"
    test_fields = ["timestamp", "cpu_usage_percent", "memory_used"]
    
    # Write some initial content
    with open(test_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(test_fields)
        writer.writerow(["2023-10-27 12:00:00", "10.5", "4294967296"])
    
    # Get file modification time before calling the function
    mtime_before = test_csv.stat().st_mtime
    
    # Call the function
    ensure_csv_header(test_csv, test_fields)
    
    # Get file modification time after calling the function
    mtime_after = test_csv.stat().st_mtime
    
    # Verify the file wasn't modified (same modification time)
    assert mtime_before == mtime_after

# Test append_metrics_batch_to_csv function
def test_append_metrics_batch_to_csv(tmp_path):
    """Test that append_metrics_batch_to_csv correctly appends metrics to a CSV file."""
    # Create a test CSV file with a header
    test_csv = tmp_path / "test.csv"
    test_fields = ["timestamp", "cpu_usage_percent", "memory_used"]
    
    with open(test_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(test_fields)
    
    # Create a batch of metrics
    metrics_batch = [
        {"timestamp": "2023-10-27 12:00:00", "cpu_usage_percent": 10.5, "memory_used": 4294967296},
        {"timestamp": "2023-10-27 12:01:00", "cpu_usage_percent": 15.2, "memory_used": 5368709120}
    ]
    
    # Call the function to append the metrics
    append_metrics_batch_to_csv(test_csv, metrics_batch, test_fields)
    
    # Verify the metrics were appended correctly
    with open(test_csv, 'r', newline='') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        # Check there are 3 rows (header + 2 data rows)
        assert len(rows) == 3
        
        # Check header row
        assert rows[0] == test_fields
        
        # Check data rows
        assert rows[1] == ["2023-10-27 12:00:00", "10.5", "4294967296"]
        assert rows[2] == ["2023-10-27 12:01:00", "15.2", "5368709120"]

# Test recording_session function
def test_recording_session_basic_flow(tmp_path):
    """Test the basic flow of the recording_session function."""
    with patch('mactop_report.record.check_mactop_running') as mock_check, \
         patch('mactop_report.record.fetch_and_parse_metrics') as mock_fetch, \
         patch('mactop_report.record.time.sleep', side_effect=KeyboardInterrupt) as mock_sleep, \
         patch('mactop_report.record.get_daily_csv_path') as mock_get_path, \
         patch('mactop_report.record.ensure_csv_header') as mock_ensure, \
         patch('mactop_report.record.append_metrics_batch_to_csv') as mock_append:
        
        # Mock check_mactop_running to return True (mactop is running)
        mock_check.return_value = True
        
        # Mock fetch_and_parse_metrics to return sample metrics
        mock_fetch.return_value = {
            'cpu_usage_percent': 10.5,
            'memory_used': 4294967296,
            'memory_total': 8589934592
        }
        
        # Mock get_daily_csv_path to return a test path
        test_csv_path = tmp_path / "test.csv"
        mock_get_path.return_value = test_csv_path
        
        # Call recording_session, which will be interrupted due to mocked KeyboardInterrupt
        recording_session(8888, 1.0, tmp_path)
        
        # Verify mactop was checked but not started (since it's already running)
        mock_check.assert_called_once_with(8888)
        
        # Verify fetch_and_parse_metrics was called
        mock_fetch.assert_called_once()
        
        # Verify ensure_csv_header was called
        mock_ensure.assert_called_once()
        
        # Verify append_metrics_batch_to_csv was called to flush buffer on exit
        mock_append.assert_called_once()
        
        # Verify sleep was called to wait for the next interval
        mock_sleep.assert_called_once_with(1.0) 