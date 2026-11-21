"""This module contains utility functions for the repo_to_text package."""

import os
import logging
from typing import List

def setup_logging(debug: bool = False) -> None:
    """Set up logging configuration.
    
    Args:
        debug: If True, sets logging level to DEBUG, otherwise INFO
    """
    logging_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

def is_ignored_path(file_path: str) -> bool:
    """Check if a file path should be ignored based on predefined rules.
    
    Args:
        file_path: Path to check
        
    Returns:
        bool: True if path should be ignored, False otherwise
    """
    ignored_files: List[str] = ['.gitignore', '.gitkeep']
    ignored_files_prefix: List[str] = ['repo-to-text_']
    path_parts: List[str] = file_path.replace(os.sep, '/').split('/')
    # `.git` is a folder in a repository and a file in a submodule
    is_git_path = '.git' in path_parts
    is_ignored_file = path_parts[-1] in ignored_files
    is_ignored_prefix = any(file_path.startswith(prefix) for prefix in ignored_files_prefix)
    result = is_git_path or is_ignored_file or is_ignored_prefix
    if result:
        logging.debug('Path ignored: %s', file_path)
    return result
