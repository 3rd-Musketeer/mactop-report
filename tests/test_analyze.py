import pytest
from pathlib import Path
from datetime import date, datetime
import polars as pl
from unittest.mock import patch, mock_open

from mactop_report.analyze import (
    find_csv_files,
    load_data,
    calculate_derived_metrics,
    calculate_statistics,
    prepare_heatmap_data,
    calculate_sufficiency_metrics,
    run_analysis
)

# Test find_csv_files
def test_find_csv_files_no_date_range(tmp_path):
    """Test finding CSV files with no date range (defaults to today)."""
    # Create mock CSV files
    today = date.today()
    today_file = tmp_path / f"mactop_data_{today.strftime('%Y-%m-%d')}.csv"
    today_file.touch()
    
    # Call the function
    with patch('mactop_report.analyze.date') as mock_date:
        mock_date.today.return_value = today
        result = find_csv_files(tmp_path)
    
    # Verify that only today's file is returned
    assert len(result) == 1
    assert result[0] == today_file

def test_find_csv_files_with_date_range(tmp_path):
    """Test finding CSV files within a specified date range."""
    # Create mock CSV files with different dates
    file1 = tmp_path / "mactop_data_2023-04-01.csv"
    file2 = tmp_path / "mactop_data_2023-04-02.csv"
    file3 = tmp_path / "mactop_data_2023-04-03.csv"
    file4 = tmp_path / "mactop_data_2023-04-04.csv"
    
    file1.touch()
    file2.touch()
    file3.touch()
    file4.touch()
    
    # Also create a non-matching file
    (tmp_path / "other_file.csv").touch()
    
    # Call the function with a date range
    start_date = date(2023, 4, 2)
    end_date = date(2023, 4, 3)
    result = find_csv_files(tmp_path, start_date=start_date, end_date=end_date)
    
    # Verify that only files within the date range are returned
    assert len(result) == 2
    assert file2 in result
    assert file3 in result
    assert file1 not in result  # Before start_date
    assert file4 not in result  # After end_date

# Test load_data
def test_load_data_single_file(tmp_path):
    """Test loading data from a single CSV file."""
    # Create a test CSV file
    csv_content = """timestamp,cpu_usage_percent,memory_used,memory_total
2023-04-01 12:00:00,25.5,8589934592,17179869184
2023-04-01 12:01:00,30.2,9663676416,17179869184
"""
    csv_file = tmp_path / "test.csv"
    with open(csv_file, 'w') as f:
        f.write(csv_content)
    
    # Call the function
    result = load_data([csv_file])
    
    # Verify the result
    assert isinstance(result, pl.DataFrame)
    assert result.shape == (2, 4)  # 2 rows, 4 columns
    assert result.columns == ['timestamp', 'cpu_usage_percent', 'memory_used', 'memory_total']
    assert result['cpu_usage_percent'].to_list() == [25.5, 30.2]
    # Check that timestamp column is parsed as datetime
    assert isinstance(result['timestamp'][0], datetime)

def test_load_data_multiple_files(tmp_path):
    """Test loading data from multiple CSV files."""
    # Create test CSV files
    csv1_content = """timestamp,cpu_usage_percent,memory_used,memory_total
2023-04-01 12:00:00,25.5,8589934592,17179869184
"""
    csv2_content = """timestamp,cpu_usage_percent,memory_used,memory_total
2023-04-02 12:00:00,30.2,9663676416,17179869184
"""
    csv1_file = tmp_path / "test1.csv"
    csv2_file = tmp_path / "test2.csv"
    
    with open(csv1_file, 'w') as f:
        f.write(csv1_content)
    with open(csv2_file, 'w') as f:
        f.write(csv2_content)
    
    # Call the function
    result = load_data([csv1_file, csv2_file])
    
    # Verify the result
    assert isinstance(result, pl.DataFrame)
    assert result.shape == (2, 4)  # 2 rows, 4 columns
    # Data should be combined from both files
    assert result['cpu_usage_percent'].to_list() == [25.5, 30.2]

def test_load_data_empty_list():
    """Test loading data with an empty list of files."""
    # Call the function with an empty list
    with pytest.raises(ValueError):
        load_data([])

# Test calculate_derived_metrics
def test_calculate_derived_metrics():
    """Test calculating derived metrics from raw data."""
    # Create a test DataFrame
    df = pl.DataFrame({
        'timestamp': ['2023-04-01 12:00:00', '2023-04-01 12:01:00'],
        'memory_used': [8589934592, 12884901888],
        'memory_total': [17179869184, 17179869184],
        'memory_swap_used': [1073741824, 2147483648]
    })
    
    # Call the function
    result = calculate_derived_metrics(df)
    
    # Verify the derived metrics
    assert 'ram_percent' in result.columns
    assert 'swap_pressure_percent' in result.columns
    
    # Check calculations (memory_used / memory_total * 100)
    expected_ram_percent = [50.0, 75.0]
    expected_swap_pressure = [6.25, 12.5]  # memory_swap_used / memory_total * 100
    
    # Allow small floating point differences
    assert result['ram_percent'].to_list() == pytest.approx(expected_ram_percent)
    assert result['swap_pressure_percent'].to_list() == pytest.approx(expected_swap_pressure)

def test_calculate_derived_metrics_handles_zero_division():
    """Test that calculate_derived_metrics handles division by zero gracefully."""
    # Create a test DataFrame with zero memory_total
    df = pl.DataFrame({
        'timestamp': ['2023-04-01 12:00:00'],
        'memory_used': [8589934592],
        'memory_total': [0],  # Zero memory_total to test division by zero
        'memory_swap_used': [1073741824]
    })
    
    # Call the function
    result = calculate_derived_metrics(df)
    
    # Verify that derived metrics are null or a reasonable value for division by zero
    assert result['ram_percent'][0] is None or result['ram_percent'][0] == 0
    assert result['swap_pressure_percent'][0] is None or result['swap_pressure_percent'][0] == 0

# Test calculate_statistics
def test_calculate_statistics():
    """Test calculating statistics for metrics."""
    # Create a test DataFrame with known values
    df = pl.DataFrame({
        'metric1': [10, 20, 30, 40, 50],
        'metric2': [5, 15, 25, 35, 45]
    })
    
    # Define metrics to analyze
    metrics = ['metric1', 'metric2']
    
    # Call the function
    result = calculate_statistics(df, metrics)
    
    # Verify the structure of the result
    assert isinstance(result, dict)
    assert sorted(result.keys()) == sorted(metrics)
    
    # Verify statistics for metric1
    m1_stats = result['metric1']
    assert m1_stats['min'] == 10
    assert m1_stats['max'] == 50
    assert m1_stats['mean'] == 30
    assert m1_stats['median'] == 30
    assert m1_stats['p75'] == 40
    assert m1_stats['p95'] == 50
    
    # Verify statistics for metric2
    m2_stats = result['metric2']
    assert m2_stats['min'] == 5
    assert m2_stats['max'] == 45
    assert m2_stats['mean'] == 25
    assert m2_stats['median'] == 25
    assert m2_stats['p75'] == 35
    assert m2_stats['p95'] == 45

# Test prepare_heatmap_data
def test_prepare_heatmap_data():
    """Test preparing heatmap data from time series."""
    # Create a test DataFrame with timestamps across different hours and days
    timestamps = [
        '2023-04-03 08:00:00',  # Monday 8 AM
        '2023-04-03 08:30:00',  # Monday 8 AM (same hour)
        '2023-04-03 14:00:00',  # Monday 2 PM
        '2023-04-04 10:00:00',  # Tuesday 10 AM
    ]
    values = [10, 20, 30, 40]
    
    df = pl.DataFrame({
        'timestamp': timestamps,
        'test_metric': values
    })
    
    # Parse timestamps into datetime
    df = df.with_columns(pl.col('timestamp').str.strptime(pl.Datetime, '%Y-%m-%d %H:%M:%S'))
    
    # Call the function
    result = prepare_heatmap_data(df, 'test_metric')
    
    # For debugging: print out the actual keys in the result dictionary
    print(f"Keys in heatmap_data: {list(result.keys())}")
    
    # Verify the structure of the result
    assert isinstance(result, dict)
    
    # Based on the debugging output, polars gives Monday a weekday of 1 and Tuesday a weekday of 2
    
    # Monday (weekday=1) 8 AM should be average of first two values (10 and 20)
    assert result[(1, 8)] == 15.0
    
    # Monday (weekday=1) 2 PM
    assert result[(1, 14)] == 30.0
    
    # Tuesday (weekday=2) 10 AM
    assert result[(2, 10)] == 40.0

# Test calculate_sufficiency_metrics
def test_calculate_sufficiency_metrics():
    """Test calculating sufficiency metrics based on percentile gaps."""
    # Create a mock statistics dictionary
    stats = {
        'metric1': {
            'p75': 75.0,
            'p95': 95.0,
            'max': 100.0
        },
        'metric2': {
            'p75': 50.0,
            'p95': 90.0,
            'max': 100.0
        }
    }
    
    # Call the function
    result = calculate_sufficiency_metrics(stats)
    
    # Verify the structure of the result
    assert isinstance(result, dict)
    assert 'metric1' in result
    assert 'metric2' in result
    
    # For metric1, the p95-p75 gap is 20% of max (95-75=20, max=100)
    assert result['metric1'] == pytest.approx(0.2)
    
    # For metric2, the p95-p75 gap is 40% of max (90-50=40, max=100)
    assert result['metric2'] == pytest.approx(0.4)

# Test run_analysis
def test_run_analysis(tmp_path):
    """Test the main analysis function."""
    # Mock find_csv_files to return a known file
    # Mock load_data to return a known DataFrame
    test_df = pl.DataFrame({
        'timestamp': ['2023-04-01 12:00:00', '2023-04-01 14:00:00'],
        'cpu_usage_percent': [25.0, 35.0],
        'memory_used': [8589934592, 10737418240],
        'memory_total': [17179869184, 17179869184],
        'memory_swap_used': [1073741824, 2147483648]
    })
    test_df = test_df.with_columns(pl.col('timestamp').str.strptime(pl.Datetime, '%Y-%m-%d %H:%M:%S'))
    
    with patch('mactop_report.analyze.find_csv_files') as mock_find, \
         patch('mactop_report.analyze.load_data') as mock_load, \
         patch('mactop_report.analyze.calculate_derived_metrics', return_value=test_df) as mock_derived, \
         patch('mactop_report.analyze.calculate_statistics') as mock_stats, \
         patch('mactop_report.analyze.prepare_heatmap_data') as mock_heatmap, \
         patch('mactop_report.analyze.calculate_sufficiency_metrics') as mock_sufficiency:
        
        # Set up mock return values
        mock_find.return_value = [tmp_path / 'test.csv']
        mock_load.return_value = test_df
        mock_stats.return_value = {'cpu_usage_percent': {'mean': 30.0, 'p75': 35.0, 'p95': 35.0}}
        mock_heatmap.return_value = {(1, 12): 25.0, (1, 14): 35.0}
        mock_sufficiency.return_value = {'cpu_usage_percent': 0.0}
        
        # Call the function
        result = run_analysis(tmp_path)
        
        # Verify the expected calls
        mock_find.assert_called_once()
        mock_load.assert_called_once()
        mock_derived.assert_called_once()
        mock_stats.assert_called_once()
        
        # There should be a call to prepare_heatmap_data for each of the PRIMARY_ANALYSIS_METRICS
        assert mock_heatmap.call_count >= 1
        
        mock_sufficiency.assert_called_once()
        
        # Verify the structure of the result
        assert isinstance(result, dict)
        assert 'statistics' in result
        assert 'heatmaps' in result
        assert 'sufficiency' in result 