import polars as pl
import re
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Any, Union

from mactop_report.utils import CSV_FILENAME_TEMPLATE, PRIMARY_ANALYSIS_METRICS

def find_csv_files(data_dir: Path, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Path]:
    """
    Find CSV files in the data directory matching the expected pattern.
    
    Args:
        data_dir: Directory to scan for CSV files.
        start_date: Optional start date to filter files.
        end_date: Optional end date to filter files.
        
    Returns:
        List of Path objects for matching CSV files.
    """
    # If no date range is provided, default to today
    if start_date is None and end_date is None:
        today = date.today()
        # Extract the filename pattern from the template, replacing the date format placeholder
        pattern = CSV_FILENAME_TEMPLATE.replace("{date:%Y-%m-%d}", f"{today:%Y-%m-%d}")
        matching_files = list(data_dir.glob(pattern))
        return matching_files
    
    # Get all CSV files
    all_csv_files = list(data_dir.glob("*.csv"))
    matching_files = []
    
    # Extract date pattern from the CSV filename template
    date_pattern = re.compile(r"mactop_data_(\d{4}-\d{2}-\d{2})\.csv")
    
    for file_path in all_csv_files:
        match = date_pattern.match(file_path.name)
        if match:
            file_date_str = match.group(1)
            try:
                file_date = date.fromisoformat(file_date_str)
                # Check if the file date is within the requested range
                if (start_date is None or file_date >= start_date) and \
                   (end_date is None or file_date <= end_date):
                    matching_files.append(file_path)
            except ValueError:
                # Skip files that don't have a valid date format
                continue
    
    return matching_files

def load_data(file_paths: List[Path]) -> pl.DataFrame:
    """
    Load data from CSV files into a Polars DataFrame.
    
    Args:
        file_paths: List of CSV file paths to load.
        
    Returns:
        Polars DataFrame containing the combined data.
        
    Raises:
        ValueError: If the file_paths list is empty or if no data could be loaded.
    """
    if not file_paths:
        raise ValueError("No CSV files provided to load data from.")
    
    # Read all CSV files and combine into a single DataFrame
    dfs = []
    
    for file_path in file_paths:
        try:
            # Use scan_csv for lazy loading, then collect
            df = pl.scan_csv(file_path).collect()
            dfs.append(df)
        except Exception as e:
            print(f"Error loading data from {file_path}: {e}")
    
    if not dfs:
        raise ValueError("Could not load data from any of the provided CSV files.")
    
    # Combine all dataframes
    combined_df = pl.concat(dfs)
    
    # Parse timestamp column to datetime, handling different formats
    try:
        # First try the standard format from recording_session
        combined_df = combined_df.with_columns(
            pl.col("timestamp").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S")
        )
    except Exception:
        try:
            # Try ISO format with T separator and microseconds
            combined_df = combined_df.with_columns(
                pl.col("timestamp").str.strptime(pl.Datetime, "%Y-%m-%dT%H:%M:%S.%f")
            )
        except Exception as e:
            # Fallback: Convert to string format that we know works
            print(f"Warning: Could not parse timestamps directly. Converting to standard format: {e}")
            combined_df = combined_df.with_columns(
                pl.col("timestamp").str.replace("T", " ").str.split(".", n=1).list.first().alias("timestamp_clean")
            )
            combined_df = combined_df.drop("timestamp")
            combined_df = combined_df.rename({"timestamp_clean": "timestamp"})
            combined_df = combined_df.with_columns(
                pl.col("timestamp").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S")
            )
    
    return combined_df

def calculate_derived_metrics(df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculate derived metrics based on raw data.
    
    Args:
        df: Input DataFrame with raw metrics.
        
    Returns:
        DataFrame with added derived metrics.
    """
    # Make a copy of the DataFrame to avoid modifying the original
    result_df = df.clone()
    
    # Handle division by zero by using a conditional expression
    # Calculate RAM usage percentage: memory_used / memory_total * 100
    result_df = result_df.with_columns(
        pl.when(pl.col("memory_total") > 0)
        .then(pl.col("memory_used") / pl.col("memory_total") * 100.0)
        .otherwise(0.0)
        .alias("ram_percent")
    )
    
    # Calculate SWAP pressure percentage: memory_swap_used / memory_total * 100
    result_df = result_df.with_columns(
        pl.when(pl.col("memory_total") > 0)
        .then(pl.col("memory_swap_used") / pl.col("memory_total") * 100.0)
        .otherwise(0.0)
        .alias("swap_pressure_percent")
    )
    
    return result_df

def calculate_statistics(df: pl.DataFrame, metrics: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Calculate various statistics for the specified metrics.
    
    Args:
        df: Input DataFrame with data.
        metrics: List of metric names to calculate statistics for.
        
    Returns:
        Dictionary mapping metric names to dictionaries of statistics.
    """
    stats = {}
    
    for metric in metrics:
        if metric not in df.columns:
            print(f"Warning: Metric '{metric}' not found in the data. Skipping.")
            continue
        
        # Calculate all statistics for this metric
        metric_stats = {
            "min": df[metric].min(),
            "max": df[metric].max(),
            "mean": df[metric].mean(),
            "median": df[metric].median(),
            "p50": df[metric].quantile(0.5),
            "p75": df[metric].quantile(0.75),
            "p95": df[metric].quantile(0.95),
            "std": df[metric].std(),
        }
        
        stats[metric] = metric_stats
    
    return stats

def prepare_heatmap_data(df: pl.DataFrame, metric: str) -> Dict[Tuple[int, int], float]:
    """
    Prepare data for a day-of-week by hour-of-day heatmap for a specific metric.
    
    Args:
        df: Input DataFrame with timestamp column.
        metric: Metric to create heatmap for.
        
    Returns:
        Dictionary mapping (day_of_week, hour) tuples to average metric values.
        day_of_week uses Polars convention: 1=Monday, 2=Tuesday, ..., 7=Sunday
    """
    if "timestamp" not in df.columns or metric not in df.columns:
        print(f"Warning: Required columns not found in the data. Returning empty heatmap.")
        return {}
    
    # Extract day of week and hour from timestamp
    # Note: In Polars, weekday() returns 1 for Monday, 2 for Tuesday, ..., 7 for Sunday
    df_with_time = df.with_columns([
        pl.col("timestamp").dt.weekday().alias("day_of_week"),
        pl.col("timestamp").dt.hour().alias("hour")
    ])
    
    # Group by day of week and hour, calculate average metric value
    grouped = df_with_time.group_by(["day_of_week", "hour"]).agg(
        pl.col(metric).mean().alias("avg_value")
    )
    
    # Convert to dictionary mapping (day_of_week, hour) -> avg_value
    heatmap_data = {
        (row["day_of_week"], row["hour"]): row["avg_value"] 
        for row in grouped.to_dicts()
    }
    
    return heatmap_data

def calculate_sufficiency_metrics(stats: Dict[str, Dict[str, float]]) -> Dict[str, float]:
    """
    Calculate sufficiency metrics based on percentile gaps.
    
    Args:
        stats: Dictionary of statistics per metric.
        
    Returns:
        Dictionary mapping metric names to sufficiency scores.
    """
    sufficiency = {}
    
    for metric, metric_stats in stats.items():
        if 'p75' not in metric_stats or 'p95' not in metric_stats or 'max' not in metric_stats:
            print(f"Warning: Required statistics missing for metric '{metric}'. Skipping.")
            continue
        
        # Calculate the p95-p75 gap as a proportion of the maximum value
        p75 = metric_stats['p75']
        p95 = metric_stats['p95']
        max_val = metric_stats['max']
        
        if max_val == 0:
            sufficiency[metric] = 0.0
        else:
            # Calculate the normalized percentile gap as a measure of sufficiency
            # Higher values indicate more headroom between typical and peak usage
            gap = (p95 - p75) / max_val
            sufficiency[metric] = gap
    
    return sufficiency

def run_analysis(
    data_dir: Path, 
    start_date: Optional[date] = None, 
    end_date: Optional[date] = None, 
    target_metrics: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Run the complete analysis pipeline.
    
    Args:
        data_dir: Directory containing CSV data files.
        start_date: Optional start date for analysis.
        end_date: Optional end date for analysis.
        target_metrics: Optional list of metrics to analyze. Defaults to PRIMARY_ANALYSIS_METRICS.
        
    Returns:
        Dictionary containing analysis results.
    """
    # Set default target metrics if not provided
    if target_metrics is None:
        target_metrics = PRIMARY_ANALYSIS_METRICS
    
    # If start_date and end_date are both None, set them to today
    if start_date is None and end_date is None:
        print(f"No date range provided. Using today: {date.today()}")
        start_date = date.today()
        end_date = start_date
    
    # Find CSV files matching the date range
    csv_files = find_csv_files(data_dir, start_date, end_date)
    print(f"Found {len(csv_files)} CSV files in {data_dir} matching date range: {start_date} to {end_date}")
    for file in csv_files:
        print(f"  - {file}")
    
    if not csv_files:
        return {
            "error": "No data files found for the specified date range.",
            "statistics": {},
            "heatmaps": {},
            "sufficiency": {}
        }
    
    # Load data from CSV files
    df = load_data(csv_files)
    print(f"Loaded data shape: {df.shape}")
    
    # Calculate derived metrics
    df = calculate_derived_metrics(df)
    print(f"Metrics available after derivation: {df.columns}")
    
    # Calculate statistics for all metrics
    all_metrics = target_metrics.copy()
    # Add raw metrics needed for derived metrics if not already included
    if 'ram_percent' in all_metrics and 'memory_used' not in all_metrics:
        all_metrics.append('memory_used')
    if 'ram_percent' in all_metrics and 'memory_total' not in all_metrics:
        all_metrics.append('memory_total')
    if 'swap_pressure_percent' in all_metrics and 'memory_swap_used' not in all_metrics:
        all_metrics.append('memory_swap_used')
    
    statistics = calculate_statistics(df, all_metrics)
    
    # Generate heatmaps for the target metrics
    heatmaps = {}
    for metric in target_metrics:
        if metric in df.columns:
            heatmaps[metric] = prepare_heatmap_data(df, metric)
    
    # Calculate sufficiency metrics
    sufficiency = calculate_sufficiency_metrics(statistics)
    
    # Add summary information
    summary = {
        "total_records": len(df),
        "date_range": [
            df["timestamp"].min().strftime("%Y-%m-%d") if len(df) > 0 else None,
            df["timestamp"].max().strftime("%Y-%m-%d") if len(df) > 0 else None
        ],
        "metrics": target_metrics
    }
    
    # Return the complete analysis results
    return {
        "statistics": statistics,
        "heatmaps": heatmaps,
        "sufficiency": sufficiency,
        "metrics": target_metrics,
        "summary": summary
    } 