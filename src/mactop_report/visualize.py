import polars as pl
from pathlib import Path
from datetime import date, datetime
from typing import Dict, List, Tuple, Any, Optional, Union
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich import box

# Day of week mapping (1=Monday, 7=Sunday to readable names)
DAY_NAMES = {
    1: "Mon",
    2: "Tue",
    3: "Wed",
    4: "Thu",
    5: "Fri",
    6: "Sat",
    7: "Sun"
}

# Color scale for heatmaps from low (cool) to high (hot)
HEAT_COLORS = [
    "#0A2F51",  # Very low - dark blue
    "#0E4D64",  # Low - blue
    "#137177",  # Below average - teal
    "#188977",  # Average - green
    "#1D9A6C",  # Above average - light green
    "#39A96B",  # Moderately high - yellow-green
    "#56B870",  # High - yellow
    "#74C67A",  # Very high - light orange
    "#99D492",  # Extremely high - orange
    "#BFE1B0",  # Critical - red
]

def format_percentage(value: Union[float, None], precision: int = 1) -> str:
    """Format a value as a percentage string.
    
    Args:
        value: The value to format.
        precision: Number of decimal places to show.
        
    Returns:
        Formatted string with percentage sign.
    """
    if value is None:
        return "N/A"
    return f"{value:.{precision}f}%"

def format_statistic(value: Union[float, int, None], precision: int = 2, is_percentage: bool = False) -> str:
    """Format a statistic with appropriate precision.
    
    Args:
        value: The value to format.
        precision: Number of decimal places for float values.
        is_percentage: Whether to add a percentage sign.
        
    Returns:
        Formatted string.
    """
    if value is None:
        return "N/A"
    
    if isinstance(value, int):
        formatted = str(value)
    else:
        formatted = f"{value:.{precision}f}"
    
    if is_percentage:
        formatted += "%"
    
    return formatted

def create_statistics_table(stats: Dict[str, Dict[str, float]], metrics: List[str]) -> Table:
    """Create a rich table showing statistics for each metric.
    
    Args:
        stats: Dictionary mapping metric names to dictionaries of statistics.
        metrics: List of metrics to include in the table.
        
    Returns:
        Rich Table object.
    """
    table = Table(title="Key Performance Metrics", box=box.ROUNDED)
    
    # Add columns
    table.add_column("Metric", style="bold cyan")
    table.add_column("Min", justify="right")
    table.add_column("Max", justify="right")
    table.add_column("Mean", justify="right")
    table.add_column("Median", justify="right")
    table.add_column("75th", justify="right")
    table.add_column("95th", justify="right")
    table.add_column("Std Dev", justify="right")
    
    # Add rows for each metric
    for metric in metrics:
        if metric not in stats:
            continue
        
        # Get statistics for this metric
        metric_stats = stats[metric]
        is_percentage = metric.endswith("percent")
        
        # Format each value
        table.add_row(
            metric.replace("_", " ").title(),
            format_statistic(metric_stats.get("min"), is_percentage=is_percentage),
            format_statistic(metric_stats.get("max"), is_percentage=is_percentage),
            format_statistic(metric_stats.get("mean"), is_percentage=is_percentage),
            format_statistic(metric_stats.get("median"), is_percentage=is_percentage),
            format_statistic(metric_stats.get("p75"), is_percentage=is_percentage),
            format_statistic(metric_stats.get("p95"), is_percentage=is_percentage),
            format_statistic(metric_stats.get("std"), is_percentage=is_percentage)
        )
    
    return table

def get_color_for_value(value: float, min_val: float, max_val: float) -> str:
    """Get a color from the HEAT_COLORS scale based on a value's position in a range.
    
    Args:
        value: The value to get a color for.
        min_val: The minimum value in the range.
        max_val: The maximum value in the range.
        
    Returns:
        A color hex string.
    """
    # Prevent division by zero
    if min_val == max_val:
        return HEAT_COLORS[0]
    
    # Calculate the position in the range (0 to 1)
    position = (value - min_val) / (max_val - min_val)
    
    # Convert to an index in the color array
    index = min(int(position * len(HEAT_COLORS)), len(HEAT_COLORS) - 1)
    
    return HEAT_COLORS[index]

def render_compact_heatmap(heatmap_data: Dict[Tuple[int, int], float], metric_name: str) -> Panel:
    """Create a compact day-of-week by hour-of-day heatmap panel.
    
    Args:
        heatmap_data: Dictionary mapping (day_of_week, hour) tuples to values.
        metric_name: Name of the metric being displayed.
        
    Returns:
        Rich Panel containing the heatmap.
    """
    if not heatmap_data:
        return Panel(Text("No data available", style="italic"), 
                     title=f"{metric_name.replace('_', ' ').title()} Heatmap")
    
    # Find min and max values for color scaling
    values = list(heatmap_data.values())
    min_val = min(values)
    max_val = max(values)
    
    # Create the heatmap table
    table = Table(show_header=True, show_lines=False, box=None, pad_edge=False, padding=0)
    
    # Add header row with hour labels
    table.add_column("", style="bold")
    for hour in range(0, 24):
        if hour % 3 == 0:  # Show every 3 hours to save space
            table.add_column(f"{hour}", justify="center", width=3)
    
    # For each day of the week
    for day in range(1, 8):  # 1=Monday, 7=Sunday
        row = [DAY_NAMES[day]]
        
        # For each hour (0-23)
        for hour in range(0, 24):
            if hour % 3 == 0:  # Match the header columns
                # Get the value for this day and hour, or None if not present
                value = heatmap_data.get((day, hour))
                
                if value is not None:
                    # Get a color based on the value
                    color = get_color_for_value(value, min_val, max_val)
                    # Create a colored cell with the value
                    cell = Text("■", style=f"bold {color}")
                else:
                    # No data for this cell
                    cell = Text(" ")
                
                row.append(cell)
        
        table.add_row(*row)
    
    # Create a panel with the table
    panel = Panel(
        table,
        title=f"{metric_name.replace('_', ' ').title()} Activity Heatmap",
        border_style="blue"
    )
    
    return panel

def create_sufficiency_panel(sufficiency_metrics: Dict[str, float]) -> Panel:
    """Create a panel showing resource sufficiency metrics.
    
    Args:
        sufficiency_metrics: Dictionary mapping metric names to sufficiency scores.
        
    Returns:
        Rich Panel containing the sufficiency information.
    """
    if not sufficiency_metrics:
        return Panel(Text("No sufficiency data available", style="italic"), 
                     title="Resource Sufficiency Analysis")
    
    table = Table(box=None)
    table.add_column("Metric", style="bold cyan")
    table.add_column("Headroom Score", justify="right")
    table.add_column("Assessment", justify="left")
    
    for metric, score in sufficiency_metrics.items():
        # Create an assessment based on the score
        if score < 0.05:
            assessment = "Very tight [red](!)[/red]"
        elif score < 0.1:
            assessment = "Tight [yellow](!)[/yellow]"
        elif score < 0.2:
            assessment = "Adequate [green]✓[/green]"
        else:
            assessment = "Generous [green]✓✓[/green]"
        
        table.add_row(
            metric.replace("_", " ").title(),
            format_percentage(score * 100, precision=1),
            assessment
        )
    
    panel = Panel(
        table,
        title="Resource Sufficiency Analysis",
        border_style="green"
    )
    
    return panel

def display_dashboard(analysis_results: Dict[str, Any], console: Optional[Console] = None) -> None:
    """Display a complete dashboard with statistics and visualizations.
    
    Args:
        analysis_results: Dictionary containing analysis results from analyze.run_analysis().
        console: Optional Rich Console object. Creates a new one if not provided.
    """
    if console is None:
        console = Console()
    
    # Extract components from the analysis results
    statistics = analysis_results.get("statistics", {})
    heatmaps = analysis_results.get("heatmaps", {})
    sufficiency = analysis_results.get("sufficiency", {})
    metrics = analysis_results.get("metrics", [])
    summary = analysis_results.get("summary", {})
    
    # Create the statistics table
    stats_table = create_statistics_table(statistics, metrics)
    
    # Create sufficiency panel
    sufficiency_panel = create_sufficiency_panel(sufficiency)
    
    # Create date range and record count text
    date_range = summary.get("date_range", [None, None])
    if date_range and len(date_range) == 2 and date_range[0] and date_range[1]:
        start_date, end_date = date_range
        date_range_text = f"Data Range: {start_date} to {end_date}"
    else:
        date_range_text = "Data Range: Unknown"
    
    total_records = summary.get("total_records", 0)
    records_text = f"Total Records: {total_records:,}"
    
    # Display the dashboard components
    console.print("")
    console.print(f"[bold]MacTop Report Dashboard[/bold]", justify="center")
    console.print(f"{date_range_text} | {records_text}", justify="center")
    console.print("")
    
    # Main statistics table
    console.print(stats_table)
    console.print("")
    
    # Resource sufficiency
    console.print(sufficiency_panel)
    console.print("")
    
    # Show a heatmap for each metric (if data is available)
    for metric in metrics:
        if metric in heatmaps:
            metric_heatmap = render_compact_heatmap(heatmaps[metric], metric)
            console.print(metric_heatmap)
            console.print("") 