import pytest
from unittest.mock import patch, MagicMock, ANY
from click.testing import CliRunner
from datetime import datetime, date
from pathlib import Path

# Import the cli module
from mactop_report.cli import cli


def test_cli_group_exists():
    """Test that the main CLI group exists."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    # Check that both commands are listed in the help output
    assert "record" in result.stdout
    assert "analyze" in result.stdout


# --- Tests for 'record' command ---

def test_record_command_exists():
    """Test that the record command exists and responds to --help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["record", "--help"])
    assert result.exit_code == 0
    assert "Recording interval" in result.stdout
    assert "--port" in result.stdout
    assert "--interval" in result.stdout
    assert "--data-dir" in result.stdout


def test_record_with_default_params(mocker):
    """Test record command with default parameters."""
    # Mock the recording_session function directly
    mock_recording_session = mocker.patch("mactop_report.cli.recording_session")
    mock_get_data_dir = mocker.patch("mactop_report.cli.get_data_dir")
    mock_get_data_dir.return_value = Path("/mock/data/dir")
    
    runner = CliRunner()
    result = runner.invoke(cli, ["record"])
    
    assert result.exit_code == 0
    # Verify recording_session was called with the correct default parameters
    mock_recording_session.assert_called_once()
    # The first positional arg should be the default port (8888 from DEFAULT_PORT)
    # The second arg should be the default interval (1.0)
    # The third arg should be the resolved data dir path
    assert mock_recording_session.call_args[0][0] == 8888  # port 
    assert mock_recording_session.call_args[0][1] == 1.0  # interval
    assert mock_recording_session.call_args[0][2] == Path("/mock/data/dir")  # data_dir


def test_record_with_custom_params(mocker):
    """Test record command with custom parameters."""
    # Mock the recording_session function directly
    mock_recording_session = mocker.patch("mactop_report.cli.recording_session")
    mock_get_data_dir = mocker.patch("mactop_report.cli.get_data_dir")
    mock_get_data_dir.return_value = Path("/custom/data/path")
    
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["record", "--port", "9999", "--interval", "2.5", "--data-dir", "custom_data"])
    
        assert result.exit_code == 0
        # Verify recording_session was called with the correct custom parameters
        mock_recording_session.assert_called_once()
        assert mock_recording_session.call_args[0][0] == 9999  # port
        assert mock_recording_session.call_args[0][1] == 2.5  # interval
        assert mock_recording_session.call_args[0][2] == Path("/custom/data/path")  # data_dir
        # Verify get_data_dir was called with any path (due to Click's path resolution)
        mock_get_data_dir.assert_called_once()


# --- Tests for 'analyze' command ---

def test_analyze_command_exists():
    """Test that the analyze command exists and responds to --help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "--start-date" in result.stdout
    assert "--end-date" in result.stdout
    assert "--data-dir" in result.stdout


def test_analyze_with_default_params(mocker):
    """Test analyze command with default parameters."""
    # Mock dependencies
    mock_get_data_dir = mocker.patch("mactop_report.cli.get_data_dir")
    mock_get_data_dir.return_value = Path("/mock/data/dir")
    mock_run_analysis = mocker.patch("mactop_report.cli.run_analysis")
    mock_run_analysis.return_value = {"stats": {}, "heatmaps": {}}  # Mock successful analysis result
    mock_display_dashboard = mocker.patch("mactop_report.cli.display_dashboard")
    
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["analyze"])
    
        assert result.exit_code == 0
        # Verify run_analysis was called with default params (None for both dates)
        mock_run_analysis.assert_called_once()
        # The first arg should be the data_dir path
        assert mock_run_analysis.call_args[0][0] == Path("/mock/data/dir")
        # Start_date and end_date should both be None by default
        assert mock_run_analysis.call_args[0][1] is None
        assert mock_run_analysis.call_args[0][2] is None
    
        # Verify display_dashboard was called with the analysis results
        mock_display_dashboard.assert_called_once_with({"stats": {}, "heatmaps": {}})


def test_analyze_with_custom_dates(mocker):
    """Test analyze command with custom date parameters."""
    # Mock dependencies
    mock_get_data_dir = mocker.patch("mactop_report.cli.get_data_dir")
    mock_get_data_dir.return_value = Path("/mock/data/dir")
    mock_run_analysis = mocker.patch("mactop_report.cli.run_analysis")
    mock_run_analysis.return_value = {"stats": {}, "heatmaps": {}}
    mock_display_dashboard = mocker.patch("mactop_report.cli.display_dashboard")
    
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, [
            "analyze", 
            "--start-date", "2023-10-01",
            "--end-date", "2023-10-05"
        ])
    
        assert result.exit_code == 0
        # Verify run_analysis was called with the specified date parameters
        mock_run_analysis.assert_called_once()
        # First param is data_dir
        assert mock_run_analysis.call_args[0][0] == Path("/mock/data/dir")
        # Start_date should be 2023-10-01 as date object 
        assert mock_run_analysis.call_args[0][1] == date(2023, 10, 1)
        # End_date should be 2023-10-05 as date object
        assert mock_run_analysis.call_args[0][2] == date(2023, 10, 5)


def test_analyze_with_custom_data_dir(mocker):
    """Test analyze command with a custom data directory."""
    # Mock dependencies
    mock_get_data_dir = mocker.patch("mactop_report.cli.get_data_dir")
    mock_get_data_dir.return_value = Path("/custom/data/path")
    mock_run_analysis = mocker.patch("mactop_report.cli.run_analysis")
    mock_run_analysis.return_value = {"stats": {}, "heatmaps": {}}
    mock_display_dashboard = mocker.patch("mactop_report.cli.display_dashboard")
    
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["analyze", "--data-dir", "custom_data"])
    
        assert result.exit_code == 0
        # Verify get_data_dir was called once (with any path due to Click's resolution)
        mock_get_data_dir.assert_called_once()
        # Verify run_analysis was called with the resolved path
        mock_run_analysis.assert_called_once()
        assert mock_run_analysis.call_args[0][0] == Path("/custom/data/path")


def test_analyze_error_handling(mocker):
    """Test error handling when analysis fails."""
    # Mock dependencies
    mock_get_data_dir = mocker.patch("mactop_report.cli.get_data_dir")
    mock_get_data_dir.return_value = Path("/mock/data/dir")
    mock_run_analysis = mocker.patch("mactop_report.cli.run_analysis")
    # Simulate an error during analysis
    mock_run_analysis.side_effect = FileNotFoundError("No data found")
    
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(cli, ["analyze"])
    
        # Verify analyze was called
        mock_run_analysis.assert_called_once()
        # Error message should be displayed
        assert "Error" in result.stdout
        assert "No data found" in result.stdout 