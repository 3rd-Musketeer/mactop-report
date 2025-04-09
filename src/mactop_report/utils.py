from pathlib import Path
from datetime import date, datetime
from typing import List, Optional, Final

# Constants
DEFAULT_PORT: Final[int] = 8888
DEFAULT_DATA_DIR_NAME: Final[str] = ".mactop-report-data"
CSV_FILENAME_TEMPLATE: Final[str] = "mactop_data_{date:%Y-%m-%d}.csv"

# Core metrics for primary analysis and visualization.
# Note: ram_percent and swap_pressure_percent are derived in analyze.py
PRIMARY_ANALYSIS_METRICS: Final[List[str]] = [
    'cpu_usage_percent',
    'gpu_usage_percent',
    'ram_percent',
    'swap_pressure_percent'
]

# Full list of expected column headers in the CSV, including 'timestamp'.
# This needs to be verified against the actual mactop /metrics output.
EXPECTED_METRIC_FIELDS: Final[List[str]] = [
    'timestamp',
    'cpu_usage_percent',
    'gpu_usage_percent',
    'memory_used',
    'memory_total',
    'memory_swap_used',
    # Add other raw metrics from mactop here as discovered
]

def get_data_dir(user_path: Optional[str] = None) -> Path:
    """Resolves the absolute path for the data directory.

    Ensures the directory exists, creating it if necessary.

    Args:
        user_path: Optional user-provided path string.

    Returns:
        The resolved absolute Path object for the data directory.
    """
    if user_path:
        # Resolve relative paths based on CWD, absolute paths as is
        data_dir = Path(user_path).resolve()
    else:
        # Default to ~/.mactop-report-data
        data_dir = Path.home() / DEFAULT_DATA_DIR_NAME

    # Ensure the directory exists
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

def get_daily_csv_path(data_dir: Path, file_date: Optional[date] = None) -> Path:
    """Constructs the full path for a specific day's CSV file.

    Args:
        data_dir: The resolved data directory Path.
        file_date: The date for the CSV file. Defaults to today.

    Returns:
        The Path object for the specific day's CSV file.
    """
    if file_date is None:
        file_date = date.today()

    filename = CSV_FILENAME_TEMPLATE.format(date=file_date)
    return data_dir / filename 