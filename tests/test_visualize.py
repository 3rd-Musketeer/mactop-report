import pytest
import polars as pl
from pathlib import Path
from datetime import datetime, date
from typing import Dict, List, Tuple, Any
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

from mactop_report.visualize import (
    format_percentage,
    format_statistic,
    create_statistics_table,
    render_compact_heatmap,
    create_sufficiency_panel,
    display_dashboard,
    get_color_for_value
)


class TestFormatters:
    def test_format_percentage(self):
        """Test the percentage formatter with various inputs."""
        assert format_percentage(75.5) == "75.5%"
        assert format_percentage(100.0) == "100.0%"
        assert format_percentage(0.0) == "0.0%"
        assert format_percentage(None) == "N/A"
        # Test with precision
        assert format_percentage(75.5678, precision=1) == "75.6%"
        assert format_percentage(75.5678, precision=0) == "76%"
    
    def test_format_statistic(self):
        """Test the statistic formatter with various inputs."""
        # Test integer formatting
        assert format_statistic(75, is_percentage=False) == "75"
        # Test float formatting
        assert format_statistic(75.5678) == "75.57"
        assert format_statistic(75.5678, precision=1) == "75.6"
        # Test percentage formatting
        assert format_statistic(75.5678, is_percentage=True) == "75.57%"
        # Test None handling
        assert format_statistic(None) == "N/A"


class TestVisualizationComponents:
    @pytest.fixture
    def sample_statistics(self):
        """Create sample statistics for testing."""
        return {
            "cpu_usage_percent": {
                "min": 5.2,
                "max": 95.7,
                "mean": 45.3,
                "median": 42.1,
                "p50": 42.1,
                "p75": 65.8,
                "p95": 85.2,
                "std": 25.4
            },
            "ram_percent": {
                "min": 50.0,
                "max": 85.0,
                "mean": 65.0,
                "median": 67.0,
                "p50": 67.0,
                "p75": 75.0,
                "p95": 82.0,
                "std": 10.0
            }
        }
    
    @pytest.fixture
    def sample_heatmap_data(self):
        """Create sample heatmap data for testing."""
        # Day of week (1=Monday to 7=Sunday), hour => average value
        return {
            (1, 9): 45.6,   # Monday, 9 AM
            (1, 12): 65.2,  # Monday, 12 PM
            (1, 15): 72.4,  # Monday, 3 PM
            (3, 10): 55.3,  # Wednesday, 10 AM
            (5, 16): 85.1,  # Friday, 4 PM
        }
    
    @pytest.fixture
    def sample_sufficiency_metrics(self):
        """Create sample sufficiency metrics for testing."""
        return {
            "cpu_usage_percent": 0.23,
            "ram_percent": 0.12
        }
        
    def test_create_statistics_table(self, sample_statistics):
        """Test that statistics table is created correctly."""
        metrics = ["cpu_usage_percent", "ram_percent"]
        table = create_statistics_table(sample_statistics, metrics)
        
        # Verify we get a Table object back
        assert isinstance(table, Table)
        
        # We can't easily check the content of the table,
        # but we can check that it has the right structure
        assert table.columns is not None
        assert len(table.columns) > 0
        
    def test_get_color_for_value(self):
        """Test the color scale function."""
        # Test normal value
        color = get_color_for_value(75.0, 0.0, 100.0)
        assert color.startswith("#")  # Should return a hex color
        
        # Test edge case: value at the minimum
        color_min = get_color_for_value(10.0, 10.0, 100.0)
        assert color_min.startswith("#")
        
        # Test edge case: value at the maximum
        color_max = get_color_for_value(100.0, 0.0, 100.0)
        assert color_max.startswith("#")
        
        # Test edge case: min and max are the same (avoid division by zero)
        color_same = get_color_for_value(50.0, 50.0, 50.0)
        assert color_same.startswith("#")
    
    def test_render_compact_heatmap(self, sample_heatmap_data):
        """Test that heatmap panel is created correctly."""
        metric_name = "cpu_usage_percent"
        panel = render_compact_heatmap(sample_heatmap_data, metric_name)
        
        # Verify we get a Panel object back
        assert isinstance(panel, Panel)
        
        # Test empty heatmap data
        empty_panel = render_compact_heatmap({}, metric_name)
        assert isinstance(empty_panel, Panel)
    
    def test_create_sufficiency_panel(self, sample_sufficiency_metrics):
        """Test that sufficiency panel is created correctly."""
        panel = create_sufficiency_panel(sample_sufficiency_metrics)
        
        # Verify we get a Panel object back
        assert isinstance(panel, Panel)
        
        # Test empty sufficiency metrics
        empty_panel = create_sufficiency_panel({})
        assert isinstance(empty_panel, Panel)

    def test_display_dashboard(self, sample_statistics, sample_heatmap_data, sample_sufficiency_metrics, monkeypatch):
        """Test that dashboard display doesn't error."""
        # Create a mock console that records output
        mock_console = Console(file=None)
        
        # Mock the print function to prevent actual printing
        prints = []
        monkeypatch.setattr(mock_console, "print", lambda *args, **kwargs: prints.append((args, kwargs)))
        
        # Sample analysis results
        analysis_results = {
            "statistics": sample_statistics,
            "heatmap_data": {
                "cpu_usage_percent": sample_heatmap_data
            },
            "sufficiency_metrics": sample_sufficiency_metrics,
            "metrics": ["cpu_usage_percent", "ram_percent"],
            "summary": {
                "total_records": 1000,
                "date_range": (date(2023, 4, 1), date(2023, 4, 5))
            }
        }
        
        # This should run without raising an exception
        display_dashboard(analysis_results, console=mock_console)
        
        # Verify that print was called at least once
        assert len(prints) > 0 