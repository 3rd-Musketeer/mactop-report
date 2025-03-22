# MacTop Monitor

A lightweight command-line tool for recording and visualizing macOS system performance metrics from mactop.

## Features

- Record system metrics to CSV files
- Customizable sampling interval
- Statistical analysis of CPU, GPU, RAM, and SWAP usage
- Interactive terminal-based visualization dashboard
- Percentile analysis (95th, 75th, 50th)
- Peak usage detection with 15-minute time windows
- Minimal dependencies (rich for visualization)

## Requirements

- Python 3.7+
- mactop command-line utility
- Dependencies listed in requirements.txt

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mactop_monitor.git
cd mactop_monitor

# Install requirements
pip install -r requirements.txt
```

## Usage

### Important Note About Sudo

The `mactop` utility requires root privileges to access system performance metrics. You have two options:

1. **Let MacTop Monitor handle it (recommended)**:
   - The script will attempt to run `mactop` with `sudo` automatically
   - You'll be prompted for your password
   - All collected data will be saved under your regular user account

2. **Start mactop manually**:
   ```bash
   # Start mactop in Prometheus mode with sudo privileges
   sudo mactop -p 8888 -i 250
   
   # In another terminal, run MacTop Monitor with the no-mactop flag
   python mactop_monitor.py record --no-mactop
   ```

### Record Metrics

```bash
# Basic recording to default file (mactop_data.csv)
python mactop_monitor.py record

# Custom file with 2-second interval
python mactop_monitor.py record --file coding_session.csv --interval 2

# Append to existing file
python mactop_monitor.py record --file coding_session.csv --append

# If you already started mactop manually:
python mactop_monitor.py record --no-mactop
```

### Analyze Metrics

```bash
# Basic analysis of recorded data
python mactop_monitor.py analyze --file coding_session.csv

# Focus on specific metrics
python mactop_monitor.py analyze --file coding_session.csv --metrics cpu,ram
```

### Interactive Dashboard

```bash
# Launch dashboard with recorded data
python mactop_monitor.py view --file coding_session.csv

# Update dashboard every 5 seconds
python mactop_monitor.py view --file coding_session.csv --interval 5
```

## Dashboard Controls

- `q`: Quit the dashboard
- `r`: Reload data from file
- `1`: View CPU details
- `2`: View GPU details
- `3`: View RAM details
- `4`: View SWAP details
- `b`: Return to main dashboard

## File Format

The CSV file has the following columns:

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