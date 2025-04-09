# Mactop Report Development Plan

This document outlines the development plan and key discussion points for refactoring the `mactop` monitoring and analysis tool.

## Project Structure

The project will follow the standard `src`-layout:

```
mactop-report/
├── src/
│   └── mactop-report/
│       ├── __init__.py
│       ├── record.py       # Handles mactop interaction and CSV writing
│       ├── analyze.py      # Core analysis logic (using polars)
│       ├── visualize.py    # Rich-based CLI visualization utils
│       ├── cli.py          # Click-based CLI interface
│       └── utils.py        # (Optional: Shared helpers, constants)
├── tests/
│   └── ...
├── pyproject.toml        # Project metadata and dependencies
└── README.md
```

## Refined Development Plan Outline

1.  **Project Setup:** Initialize the structure above, set up `pyproject.toml` with dependencies (`click`, `polars`, `rich`, `requests`).
2.  **Core `mactop` Interaction & Recording (`record.py`):** Implement robust `mactop` detection, startup (with `sudo` notice), data fetching, parsing, and writing to daily indexed CSV files. (Ref: `mactop_monitor.py`)
3.  **Data Handling & Analysis (`analyze.py`):** Implement functions using `polars` to read CSV data, calculate statistics (percentiles, avg, median, max), prepare data for heatmap, and calculate P75/P95 gap.
4.  **Visualization (`visualize.py`):** Create functions using `rich` to display statistical tables and the 24-hour heatmap.
5.  **CLI Implementation (`cli.py`):**
    *   Use `click` to create `record` and `analyze` commands.
    *   `record` command orchestrates `record.py`.
    *   `analyze` command orchestrates `analyze.py` and `visualize.py`.
6.  **Testing:** Add basic unit tests for analysis (`analyze.py`) and data handling logic.
7.  **Documentation:** Update `README.md`.

## Key Design Discussion Points (Decisions Made)

1.  **`mactop` Dependency & Robustness:**
    *   How to handle `mactop` unavailability (not installed, failed start)? Fallback options?
    - show an error message in CLI, refer the user to the mactop repo site
    - no fallback, mactop should be installed and launched

    *   How to handle `sudo` permissions gracefully?
    - display a notice to ask the user type in the password


2.  **Data Storage:**
    *   Is CSV sufficient long-term? Benefits of SQLite or other formats?
    - csv is enough

    *   Need for data rotation or archiving?
    - no need

3.  **Analysis Logic Details:**
    *   **Bottleneck Definition:** How to precisely define a bottleneck (highest %, saturation, combined metrics)?
    - percentiles, highest, average, mid value

    *   **Period Division:** How to define "different periods" (fixed blocks, activity-based)?
    - divide a day into 24 blocks, calculate the heatmap of blocks

    *   **"Sufficiency" Definition:** How to quantify sufficiency? Role of user-defined workload types (development, design, etc.)?
    - sufficiency: might be measured by the gap between 75 percentile and 95 percentile, if there is a large drop between 95p and 75p, it means the workload is low most of the time. Think of other possible metrics.
    - forget about the pattern for now

4.  **User Experience (UX):**
    *   Primary interaction: CLI only, or also TUI/Web?
    - CLI only, lightweight

    *   Report detail level: Raw stats vs. high-level summaries and actionable advice?
    - visual CLI statistics: percentiles, mean + var, mid value, heatmap
    - optional LLM summary for usage statistics

5.  **Real-time vs. Offline Analysis:**
    *   Focus: Live monitoring, historical analysis, or both? Impact on architecture?
    both, support record and analyze.


6.  **Configurability:**
    *   Which parameters need user customization (thresholds, window sizes, workload types)? How to configure them (args, config file, interactive)? 
    - simplify the tool, let `mactop-report record` and `mactop-report analyze` do the stuff, without extra configuration.


Bullet points:
- keep data day-by-day, auto index csv file using date.

## Module Design Details

### `src/mactop-report/record.py`

**Overview:**

This module is responsible for interacting with the `mactop` process (refer to [mactop repo](https://github.com/context-labs/mactop)), fetching performance metrics, parsing them, and writing them to daily CSV files. It handles the lifecycle of checking, potentially starting `mactop`, and continuously recording data.

**Key Functions/APIs:**

*   `check_mactop_running(port: int) -> bool:`
    *   Checks if the `mactop` metrics endpoint (`http://localhost:{port}/metrics`) is accessible.
*   `start_mactop_subprocess(port: int) -> Optional[subprocess.Popen]:`
    *   Attempts to start `mactop` using `sudo mactop -p {port} -i 250`.
    *   Handles informing the user about the `sudo` requirement.
    *   Returns the process handle if successful, `None` otherwise.
    *   Includes a brief wait and re-check after starting.
*   `fetch_and_parse_metrics(port: int) -> Optional[Dict[str, float]]:`
    *   Fetches raw text data from the metrics endpoint.
    *   Parses the Prometheus format into a flat dictionary (e.g., `{'cpu_usage_percent': 10.5, 'gpu_usage_percent': 5.1, ...}`).
    *   Returns `None` if fetching or parsing fails.
*   `get_daily_csv_path(data_dir: Path) -> Path:`
    *   Determines the path for the current day's CSV file (e.g., `{data_dir}/mactop_data_YYYY-MM-DD.csv`).
*   `ensure_csv_header(file_path: Path, fields: List[str]) -> None:`
    *   Checks if the CSV exists and writes the header row if it's new or empty.
*   `append_metrics_batch_to_csv(file_path: Path, metrics_batch: List[Dict[str, Union[str, float]]], fields: List[str]) -> None:`
    *   Appends a batch of metrics data rows to the specified CSV using `writerows`.
*   `recording_session(port: int, interval: float, data_dir: Path, batch_size: int = 60) -> None:`
    *   Main function called by the CLI `record` command.
    *   Orchestrates checking/starting `mactop`.
    *   Initializes an in-memory buffer (`List[Dict]`).
    *   Enters a loop to fetch and parse metrics at the specified `interval`.
    *   Appends parsed metrics to the buffer.
    *   If buffer size reaches `batch_size`, calls `append_metrics_batch_to_csv` to flush the buffer to the daily CSV file and clears the buffer.
    *   Handles `KeyboardInterrupt` for graceful shutdown.
    *   **Crucially:** Ensures any remaining metrics in the buffer are flushed to the CSV upon exiting the loop (e.g., in a `finally` block).
    *   Manages the `mactop` subprocess lifecycle if started by this script.

**Functionality Notes:**

*   **`sudo` Handling:** The `start_mactop_subprocess` will print a message informing the user that `sudo` is required and `mactop` will be launched via `sudo`. It assumes the user running the script has `sudo` privileges and will handle the OS-level password prompt.
*   **Batch Writing:** To minimize disk I/O, metrics are collected in an in-memory buffer and written to the CSV file in batches (`batch_size` determines frequency). The buffer is always flushed upon termination.
*   **CSV Format:** Uses standard CSV format. The exact `fields` list (column headers) will be defined (likely matching the original script's list).
*   **Data Structure:** Metrics parsed from Prometheus will be stored in a simple `Dict[str, float]` before adding the timestamp (`Dict[str, Union[str, float]]`) and collecting in the buffer.
*   **Error Handling:** Functions will use `try...except` blocks for network errors (requests), file I/O errors, and parsing errors. Errors will be logged or printed to the console (using `rich.print` potentially), and functions may return `None` or raise specific exceptions for critical failures (like inability to start `mactop`).
*   **Daily Files:** Data is automatically saved to a new file each day based on the system date.

**Dependencies & Configuration:**

*   Requires `requests`. Uses standard libraries `subprocess`, `csv`, `time`, `datetime`, `os`, `signal`.
*   Configuration parameters (`port`, `interval`, `data_dir`) are expected to be passed into `recording_session` from the `cli.py` module.

### `src/mactop-report/analyze.py`

**Overview:**

This module is responsible for reading the performance data from CSV files, performing analysis using the `polars` library, and preparing the results for visualization. It handles loading data across specified date ranges, calculating various statistics, and structuring the output.

**Key Functions/APIs:**

*   `find_csv_files(data_dir: Path, start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Path]:`
    *   Scans the `data_dir` for CSV files matching the `mactop_data_YYYY-MM-DD.csv` pattern.
    *   Filters files based on the optional `start_date` and `end_date` range.
    *   If `start_date` and `end_date` are both `None`, defaults to finding only the file for the current date.
*   `load_data(file_paths: List[Path]) -> pl.DataFrame:`
    *   Takes a list of CSV file paths.
    *   Uses `polars.scan_csv` followed by `collect()` (or `read_csv` if simpler for fewer files) to load data into a single Polars DataFrame.
    *   Parses the 'timestamp' column into a proper datetime type.
    *   Handles potential errors like file not found or empty files.
*   `calculate_derived_metrics(df: pl.DataFrame) -> pl.DataFrame:`
    *   Calculates RAM Usage % (`memory_used` / `memory_total`) and SWAP Pressure % (`memory_swap_used` / `memory_total`).
    *   Handles potential division by zero or missing input columns gracefully (e.g., resulting in nulls).
    *   Returns the DataFrame with added percentage columns (e.g., `ram_percent`, `swap_pressure_percent`).
*   `calculate_statistics(df: pl.DataFrame, metrics: List[str]) -> Dict[str, Dict[str, float]]:`
    *   Takes the DataFrame and a list of metric column names (e.g., `['cpu_usage_percent', 'gpu_usage_percent', 'ram_percent', 'swap_pressure_percent']`).
    *   For each metric, calculates: min, max, mean, median, p50, p75, p95, std dev.
    *   Returns a nested dictionary, e.g., `{'cpu_usage_percent': {'mean': 25.5, 'p95': 80.1, ...}, ...}`.
*   `prepare_heatmap_data(df: pl.DataFrame, metric: str) -> Dict[Tuple[int, int], float]:`
    *   Takes the DataFrame and the target metric for the heatmap.
    *   Groups data by day of the week and hour of the day.
    *   Calculates the average metric value for each group.
    *   Returns a dictionary mapping `(day_of_week, hour)` tuples to the average value, suitable for rendering a heatmap.
*   `calculate_sufficiency_metrics(stats: Dict[str, Dict[str, float]]) -> Dict[str, float]:`
    *   Takes the statistics dictionary generated by `calculate_statistics`.
    *   Calculates the percentile gap for key metrics.
    *   Potentially calculates other sufficiency indicators in the future.
    *   Returns a dictionary of sufficiency scores per metric.
*   `run_analysis(data_dir: Path, start_date: Optional[date] = None, end_date: Optional[date] = None, target_metrics: List[str] = [...]) -> Dict[str, Any]:`
    *   Main orchestrator function called by the CLI `analyze` command.
    *   If `start_date` and `end_date` are None, sets them to the current date before calling `find_csv_files`.
    *   Calls `find_csv_files`, `load_data`, `calculate_derived_metrics`, `calculate_statistics`, `prepare_heatmap_data` (likely for a primary metric like CPU), `calculate_sufficiency_metrics`.
    *   Bundles the results (statistics table data, heatmap data, sufficiency scores) into a single dictionary to be returned.

**Functionality Notes:**

*   **Polars Usage:** Leverages `polars` for efficient data loading, manipulation (like calculating derived metrics), and aggregation (for stats and heatmap).
*   **Data Loading:** Can load data from a single day (default) or span multiple days based on file discovery controlled by date range parameters.
*   **Metrics:** Core metrics for analysis will likely be CPU Usage %, GPU Usage %, RAM Usage %, SWAP Pressure % (`swap_used / memory_total`). The specific list `target_metrics` will be configurable via the CLI.
*   **Heatmap:** The heatmap data focuses on showing activity patterns across a typical week (day x hour).
*   **Return Structure:** The `run_analysis` function returns a dictionary containing clearly keyed results (e.g., `results['statistics']`, `results['heatmap_cpu']`, `results['sufficiency']`) ready for `visualize.py`.
*   **Error Handling:** Includes checks for empty DataFrames, missing required columns after loading, and errors during calculations.

**Dependencies & Configuration:**

*   Requires `polars`.
*   Uses standard libraries `datetime`, `pathlib`.
*   Configuration (`data_dir`, date range, `target_metrics`) provided by `cli.py`.

### `src/mactop-report/visualize.py`

**Overview:**

This module takes the processed analysis results from `analyze.py` and renders a comprehensive dashboard to the console using the `rich` library and its `Layout` feature. It aims to present statistics, usage patterns (heatmaps for all key metrics), and semantic summaries simultaneously, utilizing the full terminal width.

**TUI Design & Layout:**

The output will be structured using `rich.layout.Layout`:

*   `layout = Layout()`
*   **Top Row (Fixed Height):** `layout.split_column(Layout(name="title", size=3), Layout(name="main"))`
    *   `layout["title"]`: A `rich.panel.Panel` for the report title and date range.
*   **Main Area:** `layout["main"].split_row(Layout(name="left", ratio=2), Layout(name="right", ratio=3))` (Adjust ratios as needed)
    *   **Left Pane (`layout["left"]`):** Contains the main `rich.table.Table` with detailed statistics for all key metrics (CPU%, GPU%, RAM%, SWAP Pressure%). Metric names/rows use distinct base colors. Cells like Avg, P75, P95 may use subtle background colors (green/yellow/red scale) for intensity.
    *   **Right Pane (`layout["right"]`):** `layout["right"].split_column(Layout(name="heatmaps"), Layout(name="summary"))` (Can adjust ratios)
        *   **Heatmaps Area (`layout["heatmaps"]`):** Contains *compact* heatmaps for all key metrics (CPU, GPU, RAM%, SWAP Pressure%), likely arranged vertically or in a 2x2 grid if space allows. Each heatmap panel uses its metric's base color in the title and the green-yellow-red scale for intensity. Axis labels might be minimized for compactness.
        *   **Summary Area (`layout["summary"]`):** Contains the `rich.panel.Panel` for the "Analysis Summary", including semantic load levels per metric (using base colors) and the daily activity pattern summary.

**Key Functions/APIs:**

*   `create_statistics_table(...) -> Table:` (Similar to previous design, ensures it fits well in the left pane).
*   `render_compact_heatmap(heatmap_data: Dict[Tuple[int, int], float], metric: str, metric_color: str) -> Panel:`
    *   Generates a *compact* grid display suitable for the smaller heatmap area.
    *   Minimizes labels/padding.
    *   Uses colored blocks/backgrounds (green-yellow-red scale).
    *   Wraps in a `Panel` with a colored title.
*   `format_summary_report(...) -> Panel:` (Similar to previous design, formats semantic descriptions).
*   `create_dashboard_layout(analysis_results: Dict[str, Any]) -> Layout:`
    *   Takes the analysis results.
    *   Defines the base `metric_colors` mapping.
    *   Calls `create_statistics_table`, `render_compact_heatmap` (for each metric), `format_summary_report`.
    *   Constructs the `rich.layout.Layout` object as described above.
    *   Assigns the generated `Table`, heatmap `Panel`s, and summary `Panel` to the appropriate layout sections (`layout["left"].update(...)`, `layout["heatmaps"].update(...)`, etc.).
    *   Returns the fully populated `Layout` object.
*   `display_dashboard(analysis_results: Dict[str, Any]) -> None:`
    *   Main function called by `cli.py`.
    *   Initializes a `rich.console.Console`.
    *   Calls `create_dashboard_layout` to get the populated layout.
    *   Prints the `Layout` object to the console (potentially within a `Live` context if future updates are desired, though likely not needed for a static report).

**Functionality Notes:**

*   **Rich Components:** Primarily uses `rich.layout.Layout`, `rich.table.Table`, `rich.panel.Panel`, `rich.text.Text`. Heatmap rendering focuses on compactness.
*   **Full Width:** `Layout` automatically adapts to terminal width.
*   **All Metrics View:** Shows stats and heatmaps for all key metrics simultaneously.
*   **Color Usage:** Consistent use of base colors for metric identity and green-yellow-red scale for intensity.
*   **Semantic Summary:** Provides high-level takeaways alongside the data.

**Dependencies & Configuration:**

*   Requires `rich`.
*   Takes the analysis results dictionary as input.

### `src/mactop-report/cli.py`

**Overview:**

This module serves as the main entry point for the application, defining the command-line interface using the `click` library. It parses user commands and options, orchestrates the calls to the `record`, `analyze`, and `visualize` modules, and handles basic configuration like the data directory location.

**Key Functions/APIs (Click Commands & Groups):**

*   `@click.group()`
    `def cli():`
    *   Main entry point group for the commands.
    *   Can potentially handle global options like `--data-dir` here if desired.

*   `@cli.command()`
    `@click.option('--port', type=int, default=8888, help='Port mactop is running on.')`
    `@click.option('--interval', type=float, default=1.0, help='Recording interval in seconds.')`
    `@click.option('--data-dir', type=click.Path(file_okay=False, dir_okay=True, writable=True, resolve_path=True), default=None, help='Directory to store CSV data (defaults to ~/.mactop-report-data).')`
    `def record(port: int, interval: float, data_dir: Optional[str]):`
    *   Implements the `record` command.
    *   Determines the final `data_dir` path (using default if None).
    *   Ensures the `data_dir` exists.
    *   Calls `record.recording_session(port, interval, Path(data_dir))`.
    *   Includes status messages to the console (e.g., "Starting recording...").

*   `@cli.command()`
    `@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), default=None, help='Start date for analysis (YYYY-MM-DD). Defaults to today.')`
    `@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), default=None, help='End date for analysis (YYYY-MM-DD). Defaults to start date.')`
    `@click.option('--data-dir', type=click.Path(file_okay=False, dir_okay=True, readable=True, resolve_path=True), default=None, help='Directory containing CSV data (defaults to ~/.mactop-report-data).')`
    `def analyze(start_date: Optional[datetime], end_date: Optional[datetime], data_dir: Optional[str]):`
    *   Implements the `analyze` command.
    *   Determines the final `data_dir` path.
    *   Validates that `data_dir` exists and is readable.
    *   Sets default dates: if `start_date` is None, use today; if `end_date` is None, use `start_date`.
    *   Calls `analyze.run_analysis(Path(data_dir), start_date.date() if start_date else None, end_date.date() if end_date else None)`.
    *   Handles potential errors during analysis (e.g., no data found) by printing informative messages.
    *   If analysis is successful, calls `visualize.display_dashboard(analysis_results)`.

**Functionality Notes:**

*   **Click Usage:** Uses `click` decorators (`@click.group`, `@click.command`, `@click.option`) to define the interface.
*   **Data Directory:** Defaults to a hidden directory in the user's home (`~/.mactop-report-data`). This can be overridden with the `--data-dir` option, which is available for both commands.
*   **Date Handling:** Uses `click.DateTime` for convenient parsing of date strings. Defaults analysis to today if no dates are provided.
*   **Orchestration:** Acts as the conductor, calling the main functions in the other modules based on the command invoked.
*   **Error Handling:** Performs basic checks (e.g., data directory existence) and handles exceptions from underlying modules gracefully (e.g., printing error messages).
*   **Configuration:** Command-line options are the primary means of configuration, keeping it simple as requested.

**Dependencies & Configuration:**

*   Requires `click`.
*   Imports functions from `record`, `analyze`, `visualize`.
*   Uses standard libraries `pathlib`, `datetime`, `os` (for home directory).