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
        print("The 'tree' command is not found. Please install it using one of the following commands:")
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
        logging.debug(f'Path ignored: {file_path}')
    return result

def remove_empty_dirs(tree_output: str, path: str = '.') -> str:
    """Remove empty directories from tree output.
    
    Args:
        tree_output: Output from tree command
        path: Base path for the tree
        
    Returns:
        str: Tree output with empty directories removed
    """
    logging.debug('Removing empty directories from tree output')
    lines = tree_output.splitlines()
    non_empty_dirs: Set[str] = set()
    filtered_lines: List[str] = []

    for line in lines:
        parts = line.strip().split()
        if parts:
            full_path = parts[-1]
            if os.path.isdir(full_path) and not any(os.path.isfile(os.path.join(full_path, f)) for f in os.listdir(full_path)):
                logging.debug(f'Directory is empty and will be removed: {full_path}')
                continue
            non_empty_dirs.add(os.path.dirname(full_path))
            filtered_lines.append(line)
    
    final_lines: List[str] = []
    for line in filtered_lines:
        parts = line.strip().split()
        if parts:
            full_path = parts[-1]
            if os.path.isdir(full_path) and full_path not in non_empty_dirs:
                logging.debug(f'Directory is empty and will be removed: {full_path}')
                continue
            final_lines.append(line)
    
    logging.debug('Empty directory removal complete')
    return '\n'.join(filtered_lines) 