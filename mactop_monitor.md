# MacTop Monitor Design

## Overview
MacTop Monitor is a lightweight command-line tool for recording and visualizing macOS system performance metrics from mactop. It provides real-time monitoring, data recording, statistical analysis, and interactive visualization through a terminal-based UI.

## Architecture

### Components
1. **Core Module**: Handles data collection from mactop
2. **Storage Module**: Manages CSV data persistence
3. **Analysis Module**: Processes metrics for statistical insights
4. **Visualization Module**: Renders charts using rich
5. **CLI Module**: Processes command-line arguments
6. **TUI Module**: Provides interactive dashboard

### Dependencies
- `rich`: Terminal UI components and visualizations
- `textual`: TUI framework built on rich
- `requests`: HTTP requests for metric collection
- `typer`: Command-line interface
- `pandas`: Data analysis (minimal usage)

## Features

### Command-line Interface
```
mactop_monitor [command] [options]

Commands:
  record    Record performance metrics
  analyze   Analyze recorded metrics
  view      Interactive dashboard

Options:
  --file TEXT                 CSV file path for data [default: mactop_data.csv]
  --interval FLOAT            Sampling interval in seconds [default: 1.0]
  --port INTEGER              Mactop Prometheus port [default: 8888]
  --append / --overwrite      Append to existing file or start fresh
  --metrics TEXT              Metrics to monitor (cpu,gpu,ram,swap,power)
  --help                      Show help message and exit
```

### Data Recording
- Record system metrics to CSV files
- Support for appending to existing files or creating new ones
- Customizable sampling interval
- Signal handling for graceful exit
- Automatic mactop process management

### Data Analysis
For each metric (CPU, GPU, RAM, SWAP):
- Statistical measures (95th, 75th, 50th percentiles)
- Maximum, minimum, average values
- Variance and standard deviation
- Time-based analysis with 15-minute windows
- Identification of peak usage periods

### Visualization
- Real-time metric charts during recording
- Historical trend visualizations
- Bar charts for percentile comparisons
- Heatmaps for time-window analysis
- Progress bars for current utilization

### TUI Dashboard
- Main dashboard with summary of all metrics
- Dedicated pages for detailed metric analysis
- Navigation between views
- Real-time updates during recording
- Historical data exploration
- Time window selection for detailed analysis

## Implementation Details

### Data Format
CSV structure preserved from original script:
- timestamp
- cpu_usage_percent
- gpu_freq_mhz
- gpu_usage_percent
- memory_total
- memory_used
- memory_swap_total
- memory_swap_used
- power_cpu
- power_gpu
- power_total

### Analysis Methods
- Sliding window analysis (15-minute default)
- Peak detection algorithm
- Statistical calculations using pandas

### Visualization Components
- Sparklines for trends
- Progress bars for utilization
- Bar charts for comparing metrics
- Tables for statistical summaries

## Usage Scenarios

### Recording Session
```bash
# Basic recording to default file
mactop_monitor record

# Custom file with 2-second interval
mactop_monitor record --file coding_session.csv --interval 2

# Append to existing file
mactop_monitor record --file coding_session.csv --append
```

### Analysis
```bash
# Basic analysis of recorded data
mactop_monitor analyze --file coding_session.csv

# Focus on specific metrics
mactop_monitor analyze --file coding_session.csv --metrics cpu,ram
```

### Interactive Dashboard
```bash
# Launch dashboard with recorded data
mactop_monitor view --file coding_session.csv
```

## Dashboard Layout

### Main Dashboard
```
┌─────────────────────── MacTop Monitor ───────────────────────┐
│                                                              │
│  CPU: [█████████▏      ] 45.5%    GPU: [██████████████▏] 70.2%│
│  RAM: [███████████     ] 55.0%   SWAP: [▏               ] 0.5%│
│                                                              │
│  ┌─ CPU Usage ───────────┐  ┌─ GPU Usage ───────────┐        │
│  │                       │  │                       │        │
│  │    ╭╮  ╭╮             │  │         ╭─╮          │        │
│  │   ╭╯╰╮╭╯╰╮            │  │        ╭╯ ╰╮         │        │
│  │  ╭╯  ╰╯  ╰─────       │  │    ╭───╯   ╰────     │        │
│  │                       │  │                       │        │
│  └───────────────────────┘  └───────────────────────┘        │
│                                                              │
│  ┌─ RAM Usage ───────────┐  ┌─ Power Usage ─────────┐        │
│  │                       │  │                       │        │
│  │      ╭───╮            │  │   CPU: 12.3W          │        │
│  │     ╭╯   ╰╮           │  │   GPU: 9.8W           │        │
│  │  ╭──╯     ╰───        │  │   Total: 22.1W        │        │
│  │                       │  │                       │        │
│  └───────────────────────┘  └───────────────────────┘        │
│                                                              │
│  Statistics:        CPU      GPU      RAM      SWAP          │
│  95th Percentile:   78.2%    83.5%    68.9%    2.1%          │
│  Average:           45.5%    48.2%    52.3%    0.3%          │
│  Peak Period:       11:30 - 11:45 (74.3% avg CPU)            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
 [q] Quit  [1] CPU Details  [2] GPU Details  [3] RAM Details
```

### Detailed Metric View (Example: CPU)
```
┌─────────────────────── CPU Usage Details ─────────────────────┐
│                                                               │
│  Current: 45.5%   Max: 92.3%   Min: 12.1%   Avg: 48.5%        │
│                                                               │
│  ┌─ Usage History ─────────────────────────────────────────┐  │
│  │                                                         │  │
│  │    ╭╮  ╭╮                                              │  │
│  │   ╭╯╰╮╭╯╰╮                                             │  │
│  │  ╭╯  ╰╯  ╰─────                                        │  │
│  │                                                         │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌─ Statistics ───────────────────────────────────────────┐   │
│  │                                                        │   │
│  │  95th Percentile: 78.2%                               │   │
│  │  75th Percentile: 62.5%                               │   │
│  │  50th Percentile: 45.3%                               │   │
│  │  Standard Deviation: 18.7%                            │   │
│  │  Variance: 349.7                                      │   │
│  │                                                        │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─ Peak Usage Period ──────────────────────────────────┐     │
│  │                                                      │     │
│  │  Time: 11:30 - 11:45                                │     │
│  │  Average: 74.3%                                     │     │
│  │  Max: 92.3%                                         │     │
│  │                                                      │     │
│  │  ┌─ Activity (11:00 - 12:00) ─────────────────────┐ │     │
│  │  │                                                │ │     │
│  │  │  ▁▂▃▄▄▅▆▇█████▇▆▅▄▃▂▁                         │ │     │
│  │  │  11:00           11:30           12:00        │ │     │
│  │  └────────────────────────────────────────────────┘ │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                               │
└───────────────────────────────────────────────────────────────┘
 [b] Back to Dashboard  [←] Previous  [→] Next  [q] Quit
```

## Implementation Plan

1. **Phase 1: Core Functionality**
   - Set up project structure
   - Implement data collection module
   - Build command-line interface
   - Create CSV storage module

2. **Phase 2: Analysis Features**
   - Implement statistical analysis
   - Build time window processing
   - Create peak detection

3. **Phase 3: Visualization**
   - Implement rich-based charts
   - Create dashboard layout
   - Build detailed metric views

4. **Phase 4: TUI Integration**
   - Implement interactive navigation
   - Add real-time updates
   - Create interactive controls

5. **Phase 5: Testing and Optimization**
   - Performance optimization
   - Resource usage reduction
   - Cross-platform testing 