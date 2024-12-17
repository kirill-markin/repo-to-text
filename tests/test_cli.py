"""Test the CLI module."""

import os
import tempfile
import shutil
from typing import Generator
from unittest.mock import patch, MagicMock
import pytest
from repo_to_text.cli.cli import (
    create_default_settings_file,
    parse_args,
    main
)

# pylint: disable=redefined-outer-name

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)

def test_parse_args_defaults() -> None:
    """Test parsing command line arguments with default values."""
    with patch('sys.argv', ['repo-to-text']):
        args = parse_args()
        assert args.input_dir == '.'
        assert not args.debug
        assert args.output_dir is None
        assert not args.create_settings
        assert not args.stdout
        assert args.ignore_patterns is None

def test_parse_args_with_values() -> None:
    """Test parsing command line arguments with provided values."""
    test_args = [
        'repo-to-text',
        'input/path',
        '--debug',
        '--output-dir', 'output/path',
        '--ignore-patterns', '*.log', 'temp/'
    ]
    with patch('sys.argv', test_args):
        args = parse_args()
        assert args.input_dir == 'input/path'
        assert args.debug
        assert args.output_dir == 'output/path'
        assert args.ignore_patterns == ['*.log', 'temp/']

def test_create_default_settings_file(temp_dir: str) -> None:
    """Test creation of default settings file."""
    os.chdir(temp_dir)
    create_default_settings_file()

    settings_file = '.repo-to-text-settings.yaml'
    assert os.path.exists(settings_file)

    with open(settings_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert 'gitignore-import-and-ignore: True' in content
        assert 'ignore-tree-and-content:' in content
        assert 'ignore-content:' in content

def test_create_default_settings_file_already_exists(temp_dir: str) -> None:
    """Test handling of existing settings file."""
    os.chdir(temp_dir)
    # Create the file first
    create_default_settings_file()

    # Try to create it again
    with pytest.raises(FileExistsError) as exc_info:
        create_default_settings_file()
    assert "already exists" in str(exc_info.value)

@patch('repo_to_text.cli.cli.save_repo_to_text')
def test_main_normal_execution(mock_save_repo: MagicMock) -> None:
    """Test main function with normal execution."""
    with patch('sys.argv', ['repo-to-text', '--stdout']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        mock_save_repo.assert_called_once_with(
            path='.',
            output_dir=None,
            to_stdout=True,
            cli_ignore_patterns=None
        )

@patch('repo_to_text.cli.cli.create_default_settings_file')
def test_main_create_settings(mock_create_settings: MagicMock) -> None:
    """Test main function with create settings option."""
    with patch('sys.argv', ['repo-to-text', '--create-settings']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        mock_create_settings.assert_called_once()

@patch('repo_to_text.cli.cli.setup_logging')
@patch('repo_to_text.cli.cli.create_default_settings_file')
def test_main_with_debug_logging(
    mock_create_settings: MagicMock,
    mock_setup_logging: MagicMock
) -> None:
    """Test main function with debug logging enabled."""
    with patch('sys.argv', ['repo-to-text', '--debug', '--create-settings']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        mock_setup_logging.assert_called_once_with(debug=True)
        mock_create_settings.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__])
