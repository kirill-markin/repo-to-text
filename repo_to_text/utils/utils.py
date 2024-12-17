"""This module contains utility functions for the repo_to_text package."""

import os
import shutil
import logging
from typing import List, Set

def setup_logging(debug: bool = False) -> None:
    """Set up logging configuration.
    
    Args:
        debug: If True, sets logging level to DEBUG, otherwise INFO
    """
    logging_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

def check_tree_command() -> bool:
    """Check if the `tree` command is available, and suggest installation if not.
    
    Returns:
        bool: True if tree command is available, False otherwise
    """
    if shutil.which('tree') is None:
        print(
            "The 'tree' command is not found. "
            + "Please install it using one of the following commands:"
        )
        print("For Debian-based systems (e.g., Ubuntu): sudo apt-get install tree")
        print("For Red Hat-based systems (e.g., Fedora, CentOS): sudo yum install tree")
        return False
    return True

def is_ignored_path(file_path: str) -> bool:
    """Check if a file path should be ignored based on predefined rules.
    
    Args:
        file_path: Path to check
        
    Returns:
        bool: True if path should be ignored, False otherwise
    """
    ignored_dirs: List[str] = ['.git']
    ignored_files_prefix: List[str] = ['repo-to-text_']
    is_ignored_dir = any(ignored in file_path for ignored in ignored_dirs)
    is_ignored_file = any(file_path.startswith(prefix) for prefix in ignored_files_prefix)
    result = is_ignored_dir or is_ignored_file
    if result:
        logging.debug('Path ignored: %s', file_path)
    return result

def remove_empty_dirs(tree_output: str) -> str:
    """Remove empty directories from tree output."""
    logging.debug('Removing empty directories from tree output')
    lines = tree_output.splitlines()
    filtered_lines: List[str] = []

    # Track directories that have files or subdirectories
    non_empty_dirs: Set[str] = set()

    # First pass: identify non-empty directories
    for line in reversed(lines):
        stripped_line = line.strip()
        if not stripped_line.endswith('/'):
            # This is a file, mark its parent directory as non-empty
            parent_dir: str = os.path.dirname(stripped_line)
            while parent_dir:
                non_empty_dirs.add(parent_dir)
                parent_dir = os.path.dirname(parent_dir)

    # Second pass: filter out empty directories
    for line in lines:
        stripped_line = line.strip()
        if stripped_line.endswith('/'):
            # This is a directory
            dir_path = stripped_line[:-1]  # Remove trailing slash
            if dir_path not in non_empty_dirs:
                logging.debug('Directory is empty and will be removed: %s', dir_path)
                continue
        filtered_lines.append(line)

    logging.debug('Empty directory removal complete')
    return '\n'.join(filtered_lines)
