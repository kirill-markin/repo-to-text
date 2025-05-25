"""Test the core module."""

import os
import tempfile
import shutil
from typing import Generator, IO
import pytest

from unittest.mock import patch, mock_open, MagicMock
import yaml # For creating mock settings files easily

from repo_to_text.core.core import (
    get_tree_structure,
    load_ignore_specs,
    should_ignore_file,
    is_ignored_path,
    save_repo_to_text,
    load_additional_specs,
    generate_output_content
)

# pylint: disable=redefined-outer-name

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def sample_repo(tmp_path: str) -> str:
    """Create a sample repository structure for testing."""
    tmp_path_str = str(tmp_path)
    # Create directories
    os.makedirs(os.path.join(tmp_path_str, "src"))
    os.makedirs(os.path.join(tmp_path_str, "tests"))

    # Create sample files
    files = {
        "README.md": "# Test Project",
        ".gitignore": """
*.pyc
__pycache__/
.git/
""",
        "src/main.py": "print('Hello World')",
        "tests/test_main.py": "def test_sample(): pass",
        ".repo-to-text-settings.yaml": """
gitignore-import-and-ignore: True
ignore-tree-and-content:
  - ".git/"
  - ".repo-to-text-settings.yaml"
ignore-content:
  - "README.md"
  - "package-lock.json"
"""
    }

    for file_path, content in files.items():
        full_path = os.path.join(tmp_path_str, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding='utf-8') as f:
            f.write(content)

    return tmp_path_str

@pytest.fixture
def simple_word_count_repo(tmp_path: str) -> str:
    """Create a simple repository for word count testing."""
    repo_path = str(tmp_path)
    files_content = {
        "file1.txt": "This is file one. It has eight words.", # 8 words
        "file2.txt": "File two is here. This makes six words.", # 6 words
        "subdir/file3.txt": "Another file in a subdirectory, with ten words exactly." # 10 words
    }
    for file_path, content in files_content.items():
        full_path = os.path.join(repo_path, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    return repo_path

def count_words_for_test(text: str) -> int:
    """Helper to count words consistently with core logic for tests."""
    return len(text.split())

def test_is_ignored_path() -> None:
    """Test the is_ignored_path function."""
    assert is_ignored_path(".git/config") is True
    assert is_ignored_path("repo-to-text_output.txt") is True
    assert is_ignored_path("src/main.py") is False
    assert is_ignored_path("normal_file.txt") is False

def test_load_ignore_specs(sample_repo: str) -> None:
    """Test loading ignore specifications from files."""
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(
        sample_repo
    )

    assert gitignore_spec is not None
    assert content_ignore_spec is not None
    assert tree_and_content_ignore_spec is not None

    # Test gitignore patterns
    assert gitignore_spec.match_file("test.pyc") is True
    assert gitignore_spec.match_file("__pycache__/cache.py") is True
    assert gitignore_spec.match_file(".git/config") is True

    # Test content ignore patterns
    assert content_ignore_spec.match_file("README.md") is True

    # Test tree and content ignore patterns
    assert tree_and_content_ignore_spec.match_file(".git/config") is True

def test_should_ignore_file(sample_repo: str) -> None:
    """Test file ignoring logic."""
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(
        sample_repo
    )

    # Test various file paths
    assert should_ignore_file(
        ".git/config",
        ".git/config",
        gitignore_spec,
        content_ignore_spec,
        tree_and_content_ignore_spec
    ) is True

    assert should_ignore_file(
        "src/main.py",
        "src/main.py",
        gitignore_spec,
        content_ignore_spec,
        tree_and_content_ignore_spec
    ) is False

def test_get_tree_structure(sample_repo: str) -> None:
    """Test tree structure generation."""
    gitignore_spec, _, tree_and_content_ignore_spec = load_ignore_specs(sample_repo)
    tree_output = get_tree_structure(sample_repo, gitignore_spec, tree_and_content_ignore_spec)

    # Basic structure checks
    assert "src" in tree_output
    assert "tests" in tree_output
    assert "main.py" in tree_output
    assert "test_main.py" in tree_output
    assert ".git" not in tree_output

def test_save_repo_to_text(sample_repo: str) -> None:
    """Test the main save_repo_to_text function."""
    # Create output directory
    output_dir = os.path.join(sample_repo, "output")
    os.makedirs(output_dir, exist_ok=True)

    # Create .git directory to ensure it's properly ignored
    os.makedirs(os.path.join(sample_repo, ".git"))
    with open(os.path.join(sample_repo, ".git/config"), "w", encoding='utf-8') as f:
        f.write("[core]\n\trepositoryformatversion = 0\n")

    # Test file output
    output_file = save_repo_to_text(sample_repo, output_dir=output_dir)
    assert os.path.exists(output_file)
    assert os.path.dirname(output_file) == output_dir

    # Check file contents
    with open(output_file, 'r', encoding='utf-8') as f:
        content = f.read()

        # Basic content checks
        assert "Directory Structure:" in content

        # Check for expected files
        assert "src/main.py" in content
        assert "tests/test_main.py" in content

        # Check for file contents
        assert "print('Hello World')" in content
        assert "def test_sample(): pass" in content

        # Ensure ignored patterns are not in output
        assert ".git/config" not in content  # Check specific file
        assert "repo-to-text_" not in content
        assert ".repo-to-text-settings.yaml" not in content

        # Check that .gitignore content is not included
        assert "*.pyc" not in content
        assert "__pycache__" not in content

def test_save_repo_to_text_stdout(sample_repo: str) -> None:
    """Test save_repo_to_text with stdout output."""
    output = save_repo_to_text(sample_repo, to_stdout=True)
    assert isinstance(output, str)
    assert "Directory Structure:" in output
    assert "src/main.py" in output
    assert "tests/test_main.py" in output

def test_load_ignore_specs_with_cli_patterns(sample_repo: str) -> None:
    """Test loading ignore specs with CLI patterns."""
    cli_patterns = ["*.log", "temp/"]
    _, _, tree_and_content_ignore_spec = load_ignore_specs(sample_repo, cli_patterns)

    assert tree_and_content_ignore_spec.match_file("test.log") is True
    assert tree_and_content_ignore_spec.match_file("temp/file.txt") is True
    assert tree_and_content_ignore_spec.match_file("normal.txt") is False

def test_load_ignore_specs_without_gitignore(temp_dir: str) -> None:
    """Test loading ignore specs when .gitignore is missing."""
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(
        temp_dir
    )
    assert gitignore_spec is None
    assert content_ignore_spec is None
    assert tree_and_content_ignore_spec is not None

def test_get_tree_structure_with_special_chars(temp_dir: str) -> None:
    """Test tree structure generation with special characters in paths."""
    # Create files with special characters
    special_dir = os.path.join(temp_dir, "special chars")
    os.makedirs(special_dir)
    with open(os.path.join(special_dir, "file with spaces.txt"), "w", encoding='utf-8') as f:
        f.write("test")

    tree_output = get_tree_structure(temp_dir)
    assert "special chars" in tree_output
    assert "file with spaces.txt" in tree_output

def test_should_ignore_file_edge_cases(sample_repo: str) -> None:
    """Test edge cases for should_ignore_file function."""
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(
        sample_repo
    )

    # Test with dot-prefixed paths
    assert should_ignore_file(
        "./src/main.py",
        "./src/main.py",
        gitignore_spec,
        content_ignore_spec,
        tree_and_content_ignore_spec
    ) is False

    # Test with absolute paths
    abs_path = os.path.join(sample_repo, "src/main.py")
    rel_path = "src/main.py"
    assert should_ignore_file(
        abs_path,
        rel_path,
        gitignore_spec,
        content_ignore_spec,
        tree_and_content_ignore_spec
    ) is False

def test_save_repo_to_text_with_binary_files(temp_dir: str) -> None:
    """Test handling of binary files in save_repo_to_text."""
    # Create a binary file
    binary_path = os.path.join(temp_dir, "binary.bin")
    binary_content = b'\x00\x01\x02\x03'
    with open(binary_path, "wb") as f:
        f.write(binary_content)

    output = save_repo_to_text(temp_dir, to_stdout=True)

    # Check that the binary file is listed in the structure
    assert "binary.bin" in output
    # Check that the file content section exists with raw binary content
    expected_content = f"<content full_path=\"binary.bin\">\n{binary_content.decode('latin1')}\n</content>"
    assert expected_content in output

def test_save_repo_to_text_custom_output_dir(temp_dir: str) -> None:
    """Test save_repo_to_text with custom output directory."""
    # Create a simple file structure
    with open(os.path.join(temp_dir, "test.txt"), "w", encoding='utf-8') as f:
        f.write("test content")

    # Create custom output directory
    output_dir = os.path.join(temp_dir, "custom_output")
    output_file = save_repo_to_text(temp_dir, output_dir=output_dir)

    assert os.path.exists(output_file)
    assert os.path.dirname(output_file) == output_dir
    assert output_file.startswith(output_dir)

def test_get_tree_structure_empty_directory(temp_dir: str) -> None:
    """Test tree structure generation for empty directory."""
    tree_output = get_tree_structure(temp_dir)
    # Should only contain the directory itself
    assert tree_output.strip() == "" or tree_output.strip() == temp_dir

def test_empty_dirs_filtering(tmp_path: str) -> None:
    """Test filtering of empty directories in tree structure generation."""
    # Create test directory structure with normalized paths
    base_path = os.path.normpath(tmp_path)
    src_path = os.path.join(base_path, "src")
    empty_dir_path = os.path.join(base_path, "empty_dir")
    tests_path = os.path.join(base_path, "tests")

    os.makedirs(src_path)
    os.makedirs(empty_dir_path)
    os.makedirs(tests_path)

    # Create some files
    with open(os.path.join(src_path, "main.py"), "w", encoding='utf-8') as f:
        f.write("print('test')")
    with open(os.path.join(tests_path, "test_main.py"), "w", encoding='utf-8') as f:
        f.write("def test(): pass")

    # Get tree structure directly using the function
    tree_output = get_tree_structure(base_path)

    # Print debug information
    print("\nTree output:")
    print(tree_output)

    # Basic structure checks for directories with files
    assert "src" in tree_output
    assert "tests" in tree_output
    assert "main.py" in tree_output
    assert "test_main.py" in tree_output

    # Check that empty directory is not included by checking each line
    for line in tree_output.splitlines():
        # Skip the root directory line
        if base_path in line:
            continue
        # Check that no line contains 'empty_dir'
        assert "empty_dir" not in line, f"Found empty_dir in line: {line}"

# Tests for maximum_word_count_per_file functionality

def test_load_additional_specs_valid_max_words(tmp_path: str) -> None:
    """Test load_additional_specs with a valid maximum_word_count_per_file."""
    settings_content = {"maximum_word_count_per_file": 1000}
    settings_file = os.path.join(tmp_path, ".repo-to-text-settings.yaml")
    with open(settings_file, "w", encoding="utf-8") as f:
        yaml.dump(settings_content, f)

    specs = load_additional_specs(tmp_path)
    assert specs["maximum_word_count_per_file"] == 1000

def test_load_additional_specs_invalid_max_words_string(tmp_path: str, caplog) -> None:
    """Test load_additional_specs with an invalid string for maximum_word_count_per_file."""
    settings_content = {"maximum_word_count_per_file": "not-an-integer"}
    settings_file = os.path.join(tmp_path, ".repo-to-text-settings.yaml")
    with open(settings_file, "w", encoding="utf-8") as f:
        yaml.dump(settings_content, f)

    specs = load_additional_specs(tmp_path)
    assert specs["maximum_word_count_per_file"] is None
    assert "Invalid value for 'maximum_word_count_per_file': not-an-integer" in caplog.text

def test_load_additional_specs_invalid_max_words_negative(tmp_path: str, caplog) -> None:
    """Test load_additional_specs with a negative integer for maximum_word_count_per_file."""
    settings_content = {"maximum_word_count_per_file": -100}
    settings_file = os.path.join(tmp_path, ".repo-to-text-settings.yaml")
    with open(settings_file, "w", encoding="utf-8") as f:
        yaml.dump(settings_content, f)

    specs = load_additional_specs(tmp_path)
    assert specs["maximum_word_count_per_file"] is None
    assert "Invalid value for 'maximum_word_count_per_file': -100" in caplog.text

def test_load_additional_specs_max_words_is_none_in_yaml(tmp_path: str, caplog) -> None:
    """Test load_additional_specs when maximum_word_count_per_file is explicitly null in YAML."""
    settings_content = {"maximum_word_count_per_file": None} # In YAML, this is 'null'
    settings_file = os.path.join(tmp_path, ".repo-to-text-settings.yaml")
    with open(settings_file, "w", encoding="utf-8") as f:
        yaml.dump(settings_content, f)

    specs = load_additional_specs(tmp_path)
    assert specs["maximum_word_count_per_file"] is None
    assert "Invalid value for 'maximum_word_count_per_file'" not in caplog.text

def test_load_additional_specs_max_words_not_present(tmp_path: str) -> None:
    """Test load_additional_specs when maximum_word_count_per_file is not present."""
    settings_content = {"other_setting": "value"}
    settings_file = os.path.join(tmp_path, ".repo-to-text-settings.yaml")
    with open(settings_file, "w", encoding="utf-8") as f:
        yaml.dump(settings_content, f)

    specs = load_additional_specs(tmp_path)
    assert specs["maximum_word_count_per_file"] is None

def test_load_additional_specs_no_settings_file(tmp_path: str) -> None:
    """Test load_additional_specs when no settings file exists."""
    specs = load_additional_specs(tmp_path)
    assert specs["maximum_word_count_per_file"] is None

# Tests for generate_output_content related to splitting
def test_generate_output_content_no_splitting_max_words_not_set(simple_word_count_repo: str) -> None:
    """Test generate_output_content with no splitting when max_words is not set."""
    path = simple_word_count_repo
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path)
    tree_structure = get_tree_structure(path, gitignore_spec, tree_and_content_ignore_spec)

    segments = generate_output_content(
        path, tree_structure, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=None
    )
    assert len(segments) == 1
    assert "file1.txt" in segments[0]
    assert "This is file one." in segments[0]

def test_generate_output_content_no_splitting_content_less_than_limit(simple_word_count_repo: str) -> None:
    """Test generate_output_content with no splitting when content is less than max_words limit."""
    path = simple_word_count_repo
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path)
    tree_structure = get_tree_structure(path, gitignore_spec, tree_and_content_ignore_spec)

    segments = generate_output_content(
        path, tree_structure, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=500 # High limit
    )
    assert len(segments) == 1
    assert "file1.txt" in segments[0]

def test_generate_output_content_splitting_occurs(simple_word_count_repo: str) -> None:
    """Test generate_output_content when splitting occurs due to max_words limit."""
    path = simple_word_count_repo
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path)
    tree_structure = get_tree_structure(path, gitignore_spec, tree_and_content_ignore_spec)
    max_words = 30
    segments = generate_output_content(
        path, tree_structure, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=max_words
    )
    assert len(segments) > 1
    total_content = "".join(segments)
    assert "file1.txt" in total_content
    assert "This is file one." in total_content
    for i, segment in enumerate(segments):
        segment_word_count = count_words_for_test(segment)
        if i < len(segments) - 1: # For all but the last segment
             # A segment can be larger than max_words if a single chunk (e.g. file content block) is larger
             assert segment_word_count <= max_words or \
                    (segment_word_count > max_words and count_words_for_test(segment.splitlines()[-2]) > max_words)
        else: # Last segment can be smaller
             assert segment_word_count > 0

def test_generate_output_content_splitting_very_small_limit(simple_word_count_repo: str) -> None:
    """Test generate_output_content with a very small max_words limit."""
    path = simple_word_count_repo
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path)
    tree_structure = get_tree_structure(path, gitignore_spec, tree_and_content_ignore_spec)
    max_words = 10 # Very small limit
    segments = generate_output_content(
        path, tree_structure, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=max_words
    )
    assert len(segments) > 3 # Expect multiple splits
    total_content = "".join(segments)
    assert "file1.txt" in total_content
    # Check if file content (which is a chunk) forms its own segment if it's > max_words
    found_file1_content_chunk = False
    expected_file1_chunk = "<content full_path=\"file1.txt\">\nThis is file one. It has eight words.\n</content>"
    for segment in segments:
        if expected_file1_chunk.strip() in segment.strip(): # Check for the core content
            # This segment should contain the file1.txt content and its tags
            # The chunk itself is ~13 words. If max_words is 10, this chunk will be its own segment.
            assert count_words_for_test(segment) == count_words_for_test(expected_file1_chunk)
            assert count_words_for_test(segment) > max_words
            found_file1_content_chunk = True
            break
    assert found_file1_content_chunk

def test_generate_output_content_file_header_content_together(tmp_path: str) -> None:
    """Test that file header and its content are not split if word count allows."""
    repo_path = str(tmp_path)
    file_content_str = "word " * 15 # 15 words
    # Tags: <content full_path="single_file.txt">\n (3) + \n</content> (2) = 5 words. Total block = 20 words.
    files_content = {"single_file.txt": file_content_str.strip()}
    for file_path_key, content_val in files_content.items():
        full_path = os.path.join(repo_path, file_path_key)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content_val)

    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(repo_path)
    tree_structure = get_tree_structure(repo_path, gitignore_spec, tree_and_content_ignore_spec)
    
    max_words_sufficient = 35 # Enough for header + this one file block (around 20 words + initial header)
    segments = generate_output_content(
        repo_path, tree_structure, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=max_words_sufficient
    )
    assert len(segments) == 1 # Expect no splitting of this file from its tags
    expected_file_block = f'<content full_path="single_file.txt">\n{file_content_str.strip()}\n</content>'
    assert expected_file_block in segments[0]

    # Test if it splits if max_words is too small for the file block (20 words)
    max_words_small = 10
    segments_small_limit = generate_output_content(
        repo_path, tree_structure, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=max_words_small
    )
    # The file block (20 words) is a single chunk. It will form its own segment.
    # Header part will be one segment. File block another. Footer another.
    assert len(segments_small_limit) >= 2
    
    found_file_block_in_own_segment = False
    for segment in segments_small_limit:
        if expected_file_block in segment:
            assert count_words_for_test(segment) == count_words_for_test(expected_file_block)
            found_file_block_in_own_segment = True
            break
    assert found_file_block_in_own_segment

# Tests for save_repo_to_text related to splitting
@patch('repo_to_text.core.core.load_additional_specs')
@patch('repo_to_text.core.core.generate_output_content')
@patch('repo_to_text.core.core.os.makedirs')
@patch('builtins.open', new_callable=mock_open)
@patch('repo_to_text.core.core.pyperclip.copy')
def test_save_repo_to_text_no_splitting_mocked(
    mock_pyperclip_copy: MagicMock,
    mock_file_open: MagicMock, # This is the mock_open instance
    mock_makedirs: MagicMock,
    mock_generate_output: MagicMock,
    mock_load_specs: MagicMock,
    simple_word_count_repo: str,
    tmp_path: str
) -> None:
    """Test save_repo_to_text: no splitting, single file output."""
    mock_load_specs.return_value = {'maximum_word_count_per_file': None}
    mock_generate_output.return_value = ["Single combined content\nfile1.txt\ncontent1"]
    output_dir = os.path.join(str(tmp_path), "output")

    with patch('repo_to_text.core.core.datetime') as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "mock_timestamp"
        returned_path = save_repo_to_text(simple_word_count_repo, output_dir=output_dir)

    mock_load_specs.assert_called_once_with(simple_word_count_repo)
    mock_generate_output.assert_called_once() # Args are complex, basic check
    expected_filename = os.path.join(output_dir, "repo-to-text_mock_timestamp.txt")
    assert returned_path == os.path.relpath(expected_filename)
    mock_makedirs.assert_called_once_with(output_dir)
    mock_file_open.assert_called_once_with(expected_filename, 'w', encoding='utf-8')
    mock_file_open().write.assert_called_once_with("Single combined content\nfile1.txt\ncontent1")
    mock_pyperclip_copy.assert_called_once_with("Single combined content\nfile1.txt\ncontent1")

@patch('repo_to_text.core.core.load_additional_specs')
@patch('repo_to_text.core.core.generate_output_content')
@patch('repo_to_text.core.core.os.makedirs')
@patch('builtins.open') # Patch builtins.open to get the mock of the function
@patch('repo_to_text.core.core.pyperclip.copy')
def test_save_repo_to_text_splitting_occurs_mocked(
    mock_pyperclip_copy: MagicMock,
    mock_open_function: MagicMock, # This is the mock for the open function itself
    mock_makedirs: MagicMock,
    mock_generate_output: MagicMock,
    mock_load_specs: MagicMock,
    simple_word_count_repo: str,
    tmp_path: str
) -> None:
    """Test save_repo_to_text: splitting occurs, multiple file outputs with better write check."""
    mock_load_specs.return_value = {'maximum_word_count_per_file': 50}
    segments_content = ["Segment 1 content data", "Segment 2 content data"]
    mock_generate_output.return_value = segments_content
    output_dir = os.path.join(str(tmp_path), "output_split_adv")

    # Mock file handles that 'open' will return when called in a 'with' statement
    mock_file_handle1 = MagicMock(spec=IO)
    mock_file_handle2 = MagicMock(spec=IO)
    # Configure the mock_open_function to return these handles sequentially
    mock_open_function.side_effect = [mock_file_handle1, mock_file_handle2]

    with patch('repo_to_text.core.core.datetime') as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "mock_ts_split_adv"
        returned_path = save_repo_to_text(simple_word_count_repo, output_dir=output_dir)

    expected_filename_part1 = os.path.join(output_dir, "repo-to-text_mock_ts_split_adv_part_1.txt")
    expected_filename_part2 = os.path.join(output_dir, "repo-to-text_mock_ts_split_adv_part_2.txt")
    
    assert returned_path == os.path.relpath(expected_filename_part1)
    mock_makedirs.assert_called_once_with(output_dir)
    
    # Check calls to the open function
    mock_open_function.assert_any_call(expected_filename_part1, 'w', encoding='utf-8')
    mock_open_function.assert_any_call(expected_filename_part2, 'w', encoding='utf-8')
    assert mock_open_function.call_count == 2 # Exactly two calls for writing output

    # Check writes to the mocked file handles (returned by open's side_effect)
    # __enter__() is called by the 'with' statement
    mock_file_handle1.__enter__().write.assert_called_once_with(segments_content[0])
    mock_file_handle2.__enter__().write.assert_called_once_with(segments_content[1])
    
    mock_pyperclip_copy.assert_not_called()

@patch('repo_to_text.core.core.load_additional_specs')
@patch('repo_to_text.core.core.generate_output_content')
@patch('repo_to_text.core.core.os.makedirs')
@patch('builtins.open', new_callable=mock_open)
@patch('repo_to_text.core.core.pyperclip.copy')
def test_save_repo_to_text_stdout_with_splitting(
    mock_pyperclip_copy: MagicMock,
    mock_file_open: MagicMock,
    mock_os_makedirs: MagicMock,
    mock_generate_output: MagicMock,
    mock_load_specs: MagicMock,
    simple_word_count_repo: str,
    capsys
) -> None:
    """Test save_repo_to_text with to_stdout=True and content that would split."""
    mock_load_specs.return_value = {'maximum_word_count_per_file': 10} # Assume causes splitting
    mock_generate_output.return_value = ["Segment 1 for stdout.", "Segment 2 for stdout."]

    result_string = save_repo_to_text(simple_word_count_repo, to_stdout=True)

    mock_load_specs.assert_called_once_with(simple_word_count_repo)
    mock_generate_output.assert_called_once()
    mock_os_makedirs.assert_not_called()
    mock_file_open.assert_not_called()
    mock_pyperclip_copy.assert_not_called()

    captured = capsys.readouterr()
    # core.py uses print(segment, end=''), so segments are joined directly.
    assert "Segment 1 for stdout.Segment 2 for stdout." == captured.out
    assert result_string == "Segment 1 for stdout.Segment 2 for stdout."

@patch('repo_to_text.core.core.load_additional_specs')
@patch('repo_to_text.core.core.generate_output_content')
@patch('repo_to_text.core.core.os.makedirs')
@patch('builtins.open', new_callable=mock_open)
@patch('repo_to_text.core.core.pyperclip.copy')
def test_save_repo_to_text_empty_segments(
    mock_pyperclip_copy: MagicMock,
    mock_file_open: MagicMock,
    mock_makedirs: MagicMock,
    mock_generate_output: MagicMock,
    mock_load_specs: MagicMock,
    simple_word_count_repo: str,
    tmp_path: str,
    caplog
) -> None:
    """Test save_repo_to_text when generate_output_content returns no segments."""
    mock_load_specs.return_value = {'maximum_word_count_per_file': None}
    mock_generate_output.return_value = [] # Empty list
    output_dir = os.path.join(str(tmp_path), "output_empty")

    returned_path = save_repo_to_text(simple_word_count_repo, output_dir=output_dir)

    assert returned_path == ""
    mock_makedirs.assert_not_called()
    mock_file_open.assert_not_called()
    mock_pyperclip_copy.assert_not_called()
    assert "generate_output_content returned no segments" in caplog.text

if __name__ == "__main__":
    pytest.main([__file__])
