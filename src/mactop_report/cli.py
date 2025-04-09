import click
from pathlib import Path
from datetime import date, datetime
from typing import Optional

# Import specific functions rather than modules
from mactop_report.record import recording_session
from mactop_report.analyze import run_analysis
from mactop_report.visualize import display_dashboard
from mactop_report.utils import get_data_dir, DEFAULT_PORT


@click.group()
def cli():
    """MacTop Report - Monitor and analyze system resource usage.
    
    This tool helps you collect and analyze performance metrics from your Mac.
    """
    pass


@cli.command()
@click.option('--port', type=int, default=None, 
              help=f'Port mactop is running on (default: {DEFAULT_PORT}).')
@click.option('--interval', type=float, default=1.0, 
              help='Recording interval in seconds.')
@click.option('--data-dir', type=click.Path(file_okay=False, dir_okay=True, writable=True, resolve_path=True), 
              default=None, 
              help='Directory to store CSV data.')
def record(port: Optional[int], interval: float, data_dir: Optional[str]):
    """Record metrics from mactop.
    
    Starts a recording session to collect metrics from mactop at regular intervals.
    The data is saved to daily CSV files.
    """
    # Resolve the data directory
    resolved_data_dir = get_data_dir(data_dir)
    
    # Use the default port if not provided
    effective_port = port if port is not None else DEFAULT_PORT
    
    # Start the recording session
    click.echo(f"Starting recording session with interval {interval}s")
    recording_session(effective_port, interval, resolved_data_dir)


@cli.command()
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), 
              default=None, 
              help='Start date for analysis (YYYY-MM-DD). Defaults to today.')
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), 
              default=None, 
              help='End date for analysis (YYYY-MM-DD). Defaults to start date.')
@click.option('--data-dir', type=click.Path(file_okay=False, dir_okay=True, readable=True, resolve_path=True), 
              default=None, 
              help='Directory containing CSV data.')
def analyze(start_date: Optional[datetime], end_date: Optional[datetime], data_dir: Optional[str]):
    """Analyze recorded metrics.
    
    Analyzes the recorded metrics data within the specified date range
    and displays a dashboard with statistics and visualizations.
    """
    # Resolve the data directory
    resolved_data_dir = get_data_dir(data_dir)
    
    try:
        # Run the analysis
        analysis_results = run_analysis(
            resolved_data_dir,
            start_date.date() if start_date else None,
            end_date.date() if end_date else None
        )
        
        if "error" in analysis_results:
            click.echo(f"Error: {analysis_results['error']}")
            return
        
        # Display the dashboard
        display_dashboard(analysis_results)
        
    except FileNotFoundError as e:
        click.echo(f"Error: {e}")
    except Exception as e:
        click.echo(f"Error analyzing data: {e}")


if __name__ == '__main__':
    cli() 