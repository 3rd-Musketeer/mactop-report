# Mactop Report - Practical TDD Plan (Solo Developer)

This document outlines a simplified Test-Driven Development (TDD) approach for the `mactop-report` project, tailored for a solo developer. The goal is to leverage the core benefits of TDD (design guidance, regression prevention, documentation) while minimizing overhead.

## Setup Assumption

*   **Editable Install:** It is assumed the project will be installed in editable mode using `pip install -e .` from the project root directory (where `pyproject.toml` is located).
*   **Absolute Imports:** Consequently, both the application code (within `src/mactop_report/`) and the test code (within `tests/`) should use absolute imports relative to the package name, e.g., `from mactop_report.utils import get_data_dir`, `from mactop_report.analyze import run_analysis`.

## Core TDD Workflow: Red-Green-Refactor

We will follow the fundamental TDD cycle for developing new functionality:

1.  **RED:** Write a small, focused test for a single piece of functionality *before* writing the implementation code. This test **must fail** initially because the code doesn't exist yet.
2.  **GREEN:** Write the **absolute minimum** amount of implementation code required to make the failing test pass. Don't worry about elegance or efficiency at this stage.
3.  **REFACTOR:** Improve the implementation code written in the Green phase. Clean up duplication, improve clarity, enhance performance, and ensure it adheres to good design principles. Crucially, **re-run all relevant tests** after refactoring to ensure they still pass.

Repeat this cycle for each small piece of functionality.

## Testing Strategy by Module

We'll use `pytest` as our testing framework. Focus TDD efforts where they provide the most value – typically pure functions and complex logic.

*   **`src/mactop_report/utils.py`:**
    *   **Priority:** High (Good place to start TDD).
    *   **Focus:** Test utility functions with clear inputs/outputs.
    *   **Examples:**
        *   Test `get_data_dir`: Does it return the correct default path? Does it respect a user-provided path? Does it create the directory if it doesn't exist (use `pytest`'s `tmp_path` fixture)?
        *   Test `get_daily_csv_path`: Does it generate the correct filename format for today? For a specific date?

*   **`src/mactop_report/analyze.py`:**
    *   **Priority:** Very High (Core logic resides here).
    *   **Focus:** Extensively test the data loading, transformation, and calculation functions.
    *   **Examples:**
        *   Create small, sample CSV files or `polars.DataFrame` objects directly within tests.
        *   Test `calculate_derived_metrics`: Provide known input values (memory used/total, swap used) and assert the calculated percentages (`ram_percent`, `swap_pressure_percent`), including edge cases (e.g., division by zero if `memory_total` could be 0).
        *   Test `calculate_statistics`: Use a DataFrame with known values and verify the calculated `min`, `max`, `mean`, `median`, `p75`, `p95`, `std dev` for each metric.
        *   Test `prepare_heatmap_data`: Use sample data spanning different hours/days and verify the resulting dictionary structure and averaged values.
        *   Test `find_csv_files`: Use `tmp_path` to create mock directory structures with dated CSV files and test the date filtering logic.
        *   Test `load_data`: Test loading from single/multiple valid CSVs, empty CSVs, non-existent files (expecting specific errors or return values like `None` or empty DataFrame, based on implementation choice).
        *   Test `calculate_sufficiency_metrics`: Verify the percentile gap calculation.

*   **`src/mactop_report/record.py`:**
    *   **Priority:** Medium (Mix of testable logic and external interactions).
    *   **Focus:** Apply TDD to parsing and file writing. Use mocking for external interactions.
    *   **Examples:**
        *   **TDD:**
            *   Test the *parsing logic* within `fetch_and_parse_metrics`: Provide sample Prometheus text output (as strings) and assert the correctly parsed dictionary is returned.
            *   Test `ensure_csv_header` and `append_metrics_batch_to_csv` using `tmp_path` to verify CSV file contents.
        *   **Mocking/Integration Tests (Less TDD, more traditional testing):**
            *   Use `pytest-mock` to mock `requests.get`, `subprocess.Popen`, `time.sleep`.
            *   Test `check_mactop_running`: Mock `requests.get` to return success/failure and verify the boolean output.
            *   Test `start_mactop_subprocess`: Mock `subprocess.Popen` and `check_mactop_running` to verify the logic flow (e.g., message printing, process return).
            *   Test `recording_session`: Mock external calls (`check_mactop_running`, `fetch_and_parse_metrics`, `append_metrics_batch_to_csv`) to verify the main loop logic (batching, interval sleeping, shutdown handling, final flush).

*   **`src/mactop_report/visualize.py`:**
    *   **Priority:** Low (UI/Output heavy, harder to TDD reliably).
    *   **Focus:** Test data formatting helpers. Minimal testing on direct `rich` object generation.
    *   **Examples:**
        *   If you have helper functions that format numbers or text *before* creating `rich` objects, TDD those.
        *   Optionally, test that `create_statistics_table` or `render_compact_heatmap` produce `rich` objects (`Table`, `Panel`) without errors given valid input data. Avoid asserting exact rendered output string.

*   **`src/mactop_report/cli.py`:**
    *   **Priority:** Medium.
    *   **Focus:** Test command invocation, option parsing, and orchestration logic using `click.testing.CliRunner` and mocking.
    *   **Examples:**
        *   Use `CliRunner` to invoke commands (`mactop-report record --interval 5`).
        *   Assert exit codes (`result.exit_code == 0`).
        *   Mock the underlying functions (`record.recording_session`, `analyze.run_analysis`, `visualize.display_dashboard`) using `pytest-mock`'s `mocker` fixture.
        *   Verify that the mocked functions were called with the correct arguments derived from CLI options.
        *   Test error handling (e.g., providing an invalid date format).

## Tools

*   **Test Runner:** `pytest`
*   **Mocking:** `pytest-mock` (usually installed automatically with `pytest`)
*   **Coverage (Optional):** `pytest-cov` (Run with `pytest --cov=src/mactop_report`)

## Practical Considerations for Solo Dev

*   **Start Simple:** Begin TDD with `utils.py` or simple functions in `analyze.py`.
*   **Focus on Value:** Prioritize testing complex logic, calculations, and core algorithms (`analyze.py`).
*   **Be Pragmatic:** Don't force TDD onto everything. Direct external interactions (`record.py`) or complex UI (`visualize.py`) might warrant more integration-style tests or manual checks.
*   **Mock Wisely:** Use mocking for external boundaries (network, filesystem, subprocesses) but avoid over-mocking internal implementation details.
*   **Refactor Fearlessly:** The tests give you a safety net. Use the Refactor step to improve your code constantly.
*   **Test Granularity:** Keep tests small and focused on one behavior.
*   **Goal:** Aim for confidence in your core logic and a safety net against regressions, not necessarily 100% test coverage driven purely by TDD. 