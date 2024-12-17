"""
CLI for repo-to-text
"""

import argparse
import textwrap
import os
import logging
import sys
from typing import NoReturn

from ..utils.utils import setup_logging
from ..core.core import save_repo_to_text

def create_default_settings_file() -> None:
    """Create a default .repo-to-text-settings.yaml file."""
    settings_file = '.repo-to-text-settings.yaml'
    if os.path.exists(settings_file):
        raise FileExistsError(
            f"The settings file '{settings_file}' already exists. "
            "Please remove it or rename it if you want to create a new default settings file."
        )

    default_settings = textwrap.dedent("""\
        # Details: https://github.com/kirill-markin/repo-to-text
        # Syntax: gitignore rules

        # Ignore files and directories for all sections from gitignore file
        # Default: True
        gitignore-import-and-ignore: True

        # Ignore files and directories for tree
        # and "Contents of ..." sections
        ignore-tree-and-content:
          - ".repo-to-text-settings.yaml"

        # Ignore files and directories for "Contents of ..." section
        ignore-content:
          - "README.md"
          - "LICENSE"
    """)
    with open('.repo-to-text-settings.yaml', 'w', encoding='utf-8') as f:
        f.write(default_settings)
    print("Default .repo-to-text-settings.yaml created.")

def parse_args() -> argparse.Namespace:
    """Parse command line arguments.
    
    Returns:
        argparse.Namespace: Parsed command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Convert repository structure and contents to text'
    )
    parser.add_argument('input_dir', nargs='?', default='.', help='Directory to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--output-dir', type=str, help='Directory to save the output file')
    parser.add_argument(
        '--create-settings',
        '--init',
        action='store_true',
        help='Create default .repo-to-text-settings.yaml file'
    )
    parser.add_argument('--stdout', action='store_true', help='Output to stdout instead of a file')
    parser.add_argument(
        '--ignore-patterns',
        nargs='*',
        help="List of files or directories to ignore in both tree and content sections. "
        "Supports wildcards (e.g., '*')."
    )
    return parser.parse_args()

def main() -> NoReturn:
    """Main entry point for the CLI.
    
    Raises:
        SystemExit: Always exits with code 0 on success
    """
    args = parse_args()
    setup_logging(debug=args.debug)
    logging.debug('repo-to-text script started')

    try:
        if args.create_settings:
            create_default_settings_file()
            logging.debug('.repo-to-text-settings.yaml file created')
        else:
            save_repo_to_text(
                path=args.input_dir,
                output_dir=args.output_dir,
                to_stdout=args.stdout,
                cli_ignore_patterns=args.ignore_patterns
            )

        logging.debug('repo-to-text script finished')
        sys.exit(0)
    except (FileNotFoundError, FileExistsError, PermissionError, OSError) as e:
        logging.error('Error occurred: %s', str(e))
        sys.exit(1)
