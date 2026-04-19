import sys
from pathlib import Path


def pytest_collect_file(parent, file_path):
    """Add each test file's directory to sys.path so local imports resolve."""
    if file_path.name.startswith("test_") and file_path.suffix == ".py":
        directory = str(file_path.parent)
        if directory not in sys.path:
            sys.path.insert(0, directory)
