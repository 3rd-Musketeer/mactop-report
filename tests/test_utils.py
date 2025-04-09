import pytest
from pathlib import Path
from datetime import date
from freezegun import freeze_time

# Assuming project is installed editable (`pip install -e .`)
# Use absolute imports relative to the package
from mactop_report.utils import (
    get_data_dir,
    get_daily_csv_path,
    DEFAULT_DATA_DIR_NAME,
    CSV_FILENAME_TEMPLATE,
)

# --- Tests for get_data_dir ---

def test_get_data_dir_default(tmp_path, monkeypatch):
    """Test get_data_dir uses default path under mocked home and creates it."""
    # Mock Path.home() to return tmp_path for isolation during testing
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    expected_path = tmp_path / DEFAULT_DATA_DIR_NAME

    # Ensure the directory does not exist beforehand
    assert not expected_path.exists()

    # Call the function
    result_path = get_data_dir()

    # Assertions
    assert result_path == expected_path
    assert expected_path.exists(), "Default directory should be created"
    assert expected_path.is_dir(), "Default path should be a directory"

def test_get_data_dir_user_provided_relative_in_tmp(tmp_path):
    """Test get_data_dir with a user-provided path relative to tmp_path."""
    # We use tmp_path as a simulated CWD for resolving relative paths
    relative_user_dir = "my_custom_data"
    # Construct the path string as if the user typed './my_custom_data' within tmp_path
    user_provided_path_str = str(tmp_path / relative_user_dir)
    expected_path = Path(user_provided_path_str).resolve() # resolve should handle it

    # Ensure the directory does not exist beforehand
    assert not expected_path.exists()

    # Call the function
    result_path = get_data_dir(user_path=user_provided_path_str)

    # Assertions
    assert result_path == expected_path
    assert expected_path.exists(), "User-specified directory should be created"
    assert expected_path.is_dir(), "User-specified path should be a directory"

def test_get_data_dir_user_provided_absolute(tmp_path):
    """Test get_data_dir with a user-provided absolute path within tmp_path."""
    absolute_path_str = str(tmp_path / "absolute_data_dir")
    expected_path = Path(absolute_path_str)

    # Ensure the directory does not exist beforehand
    assert not expected_path.exists()

    # Call the function
    result_path = get_data_dir(user_path=absolute_path_str)

    # Assertions
    assert result_path == expected_path
    assert expected_path.exists(), "User-specified absolute directory should be created"
    assert expected_path.is_dir(), "User-specified absolute path should be a directory"

# --- Tests for get_daily_csv_path ---

@freeze_time("2023-10-27")
def test_get_daily_csv_path_default_date(tmp_path):
    """Test get_daily_csv_path generates correct path for today (mocked)."""
    test_data_dir = tmp_path / "test_data"
    # Note: get_daily_csv_path does *not* create the directory, get_data_dir does.
    # We only need the base path for testing the filename generation.

    mocked_today = date(2023, 10, 27)
    expected_filename = CSV_FILENAME_TEMPLATE.format(date=mocked_today)
    expected_path = test_data_dir / expected_filename

    # Call the function
    result_path = get_daily_csv_path(test_data_dir)

    # Assertions
    assert result_path == expected_path
    assert result_path.name == expected_filename
    # Verify the function doesn't create the file itself
    assert not expected_path.exists()

def test_get_daily_csv_path_specific_date(tmp_path):
    """Test get_daily_csv_path generates correct path for a specific date."""
    test_data_dir = tmp_path / "specific_date_data"

    specific_date = date(2024, 1, 15)
    expected_filename = CSV_FILENAME_TEMPLATE.format(date=specific_date)
    expected_path = test_data_dir / expected_filename

    # Call the function
    result_path = get_daily_csv_path(test_data_dir, file_date=specific_date)

    # Assertions
    assert result_path == expected_path
    assert result_path.name == expected_filename
    assert not expected_path.exists() 