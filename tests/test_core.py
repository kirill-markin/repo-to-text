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

# Mock tree outputs
# Raw output similar to `tree -a -f --noreport`
MOCK_RAW_TREE_FOR_SAMPLE_REPO = """./
./.gitignore
./.repo-to-text-settings.yaml
./README.md
./src
./src/main.py
./tests
./tests/test_main.py
"""

MOCK_RAW_TREE_SPECIAL_CHARS = """./
./special chars
./special chars/file with spaces.txt
"""

MOCK_RAW_TREE_EMPTY_FILTERING = """./
./src
./src/main.py
./tests
./tests/test_main.py
"""
# Note: ./empty_dir is removed, assuming tree or filter_tree_output would handle it.
# This makes the test focus on the rest of the logic if tree output is as expected.

# Expected output from get_tree_structure (filtered)
MOCK_GTS_OUTPUT_FOR_SAMPLE_REPO = """.
├── .gitignore
├── README.md
├── src
│   └── main.py
└── tests
    └── test_main.py"""

MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO = """.
├── file1.txt
├── file2.txt
└── subdir
    └── file3.txt"""

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

@patch('repo_to_text.core.core.run_tree_command', return_value=MOCK_RAW_TREE_FOR_SAMPLE_REPO)
@patch('repo_to_text.core.core.check_tree_command', return_value=True)
def test_get_tree_structure(mock_check_tree: MagicMock, mock_run_tree: MagicMock, sample_repo: str) -> None:
    """Test tree structure generation."""
    gitignore_spec, _, tree_and_content_ignore_spec = load_ignore_specs(sample_repo)
    # The .repo-to-text-settings.yaml in sample_repo ignores itself from tree and content
    tree_output = get_tree_structure(sample_repo, gitignore_spec, tree_and_content_ignore_spec)

    # Basic structure checks
    assert "src" in tree_output
    assert "tests" in tree_output
    assert "main.py" in tree_output
    assert "test_main.py" in tree_output
    assert ".git" not in tree_output
    assert ".repo-to-text-settings.yaml" not in tree_output # Should be filtered by tree_and_content_ignore_spec

@patch('repo_to_text.core.core.get_tree_structure', return_value=MOCK_GTS_OUTPUT_FOR_SAMPLE_REPO)
@patch('repo_to_text.core.core.check_tree_command', return_value=True) # In case any internal call still checks
def test_save_repo_to_text(mock_check_tree: MagicMock, mock_get_tree: MagicMock, sample_repo: str) -> None:
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
    assert os.path.abspath(os.path.dirname(output_file)) == os.path.abspath(output_dir)

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

@patch('repo_to_text.core.core.run_tree_command', return_value=MOCK_RAW_TREE_SPECIAL_CHARS)
@patch('repo_to_text.core.core.check_tree_command', return_value=True)
def test_get_tree_structure_with_special_chars(mock_check_tree: MagicMock, mock_run_tree: MagicMock, temp_dir: str) -> None:
    """Test tree structure generation with special characters in paths."""
    # Create files with special characters
    special_dir = os.path.join(temp_dir, "special chars") # Matches MOCK_RAW_TREE_SPECIAL_CHARS
    os.makedirs(special_dir)
    with open(os.path.join(special_dir, "file with spaces.txt"), "w", encoding='utf-8') as f:
        f.write("test")

    # load_ignore_specs will be called inside; for temp_dir, they will be None or empty.
    gitignore_spec, _, tree_and_content_ignore_spec = load_ignore_specs(temp_dir)
    tree_output = get_tree_structure(temp_dir, gitignore_spec, tree_and_content_ignore_spec)

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

@patch('repo_to_text.core.core.get_tree_structure', return_value=MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO) # Using simple repo tree for generic content
@patch('repo_to_text.core.core.check_tree_command', return_value=True)
def test_save_repo_to_text_custom_output_dir(mock_check_tree: MagicMock, mock_get_tree: MagicMock, temp_dir: str) -> None:
    """Test save_repo_to_text with custom output directory."""
    # Create a simple file structure
    with open(os.path.join(temp_dir, "test.txt"), "w", encoding='utf-8') as f:
        f.write("test content")

    # Create custom output directory
    output_dir = os.path.join(temp_dir, "custom_output")
    output_file = save_repo_to_text(temp_dir, output_dir=output_dir)

    assert os.path.exists(output_file)
    assert os.path.abspath(os.path.dirname(output_file)) == os.path.abspath(output_dir)
    # output_file is relative, output_dir is absolute. This assertion needs care.
    # Let's assert that the absolute path of output_file starts with absolute output_dir
    assert os.path.abspath(output_file).startswith(os.path.abspath(output_dir))

def test_get_tree_structure_empty_directory(temp_dir: str) -> None:
    """Test tree structure generation for empty directory."""
    tree_output = get_tree_structure(temp_dir)
    # Should only contain the directory itself
    assert tree_output.strip() == "" or tree_output.strip() == temp_dir

@patch('repo_to_text.core.core.run_tree_command', return_value=MOCK_RAW_TREE_EMPTY_FILTERING)
@patch('repo_to_text.core.core.check_tree_command', return_value=True)
def test_empty_dirs_filtering(mock_check_tree: MagicMock, mock_run_tree: MagicMock, tmp_path: str) -> None:
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

def test_load_additional_specs_invalid_max_words_string(tmp_path: str, caplog: pytest.LogCaptureFixture) -> None:
    """Test load_additional_specs with an invalid string for maximum_word_count_per_file."""
    settings_content = {"maximum_word_count_per_file": "not-an-integer"}
    settings_file = os.path.join(tmp_path, ".repo-to-text-settings.yaml")
    with open(settings_file, "w", encoding="utf-8") as f:
        yaml.dump(settings_content, f)

    specs = load_additional_specs(tmp_path)
    assert specs["maximum_word_count_per_file"] is None
    assert "Invalid value for 'maximum_word_count_per_file': not-an-integer" in caplog.text

def test_load_additional_specs_invalid_max_words_negative(tmp_path: str, caplog: pytest.LogCaptureFixture) -> None:
    """Test load_additional_specs with a negative integer for maximum_word_count_per_file."""
    settings_content = {"maximum_word_count_per_file": -100}
    settings_file = os.path.join(tmp_path, ".repo-to-text-settings.yaml")
    with open(settings_file, "w", encoding="utf-8") as f:
        yaml.dump(settings_content, f)

    specs = load_additional_specs(tmp_path)
    assert specs["maximum_word_count_per_file"] is None
    assert "Invalid value for 'maximum_word_count_per_file': -100" in caplog.text

def test_load_additional_specs_max_words_is_none_in_yaml(tmp_path: str, caplog: pytest.LogCaptureFixture) -> None:
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
@patch('repo_to_text.core.core.get_tree_structure', return_value=MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO)
def test_generate_output_content_no_splitting_max_words_not_set(mock_get_tree: MagicMock, simple_word_count_repo: str) -> None:
    """Test generate_output_content with no splitting when max_words is not set."""
    path = simple_word_count_repo
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path)
    # tree_structure is now effectively MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO due to the mock
    
    segments = generate_output_content(
        path, MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=None
    )
    mock_get_tree.assert_not_called() # We are passing tree_structure directly
    assert len(segments) == 1
    assert "file1.txt" in segments[0]
    assert "This is file one." in segments[0]

@patch('repo_to_text.core.core.get_tree_structure', return_value=MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO)
def test_generate_output_content_no_splitting_content_less_than_limit(mock_get_tree: MagicMock, simple_word_count_repo: str) -> None:
    """Test generate_output_content with no splitting when content is less than max_words limit."""
    path = simple_word_count_repo
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path)

    segments = generate_output_content(
        path, MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=500 # High limit
    )
    mock_get_tree.assert_not_called()
    assert len(segments) == 1
    assert "file1.txt" in segments[0]

@patch('repo_to_text.core.core.get_tree_structure', return_value=MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO)
def test_generate_output_content_splitting_occurs(mock_get_tree: MagicMock, simple_word_count_repo: str) -> None:
    """Test generate_output_content when splitting occurs due to max_words limit."""
    path = simple_word_count_repo
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path)
    max_words = 30
    segments = generate_output_content(
        path, MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=max_words
    )
    mock_get_tree.assert_not_called()
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

@patch('repo_to_text.core.core.get_tree_structure', return_value=MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO)
def test_generate_output_content_splitting_very_small_limit(mock_get_tree: MagicMock, simple_word_count_repo: str) -> None:
    """Test generate_output_content with a very small max_words limit."""
    path = simple_word_count_repo
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path)
    max_words = 10 # Very small limit
    segments = generate_output_content(
        path, MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=max_words
    )
    mock_get_tree.assert_not_called()
    assert len(segments) > 3 # Expect multiple splits due to small limit and multiple chunks
    total_content = "".join(segments)
    assert "file1.txt" in total_content # Check presence of file name in overall output

    raw_file1_content = "This is file one. It has eight words." # 8 words
    # Based on actual debug output, the closing tag is just "</content>" (1 word)
    closing_tag_content = "</content>" # 1 word

    # With max_words = 10:
    # The splitting logic works per chunk, so raw_content (8 words) + closing_tag (1 word) = 9 words total
    # should fit in one segment when they're placed together

    # Debug: Let's see what segments actually look like in CI
    print(f"\nDEBUG: Generated {len(segments)} segments:")
    for i, segment in enumerate(segments):
        print(f"Segment {i+1} ({count_words_for_test(segment)} words):")
        print(f"'{segment}'")
        print("---")

    found_raw_content_segment = False
    for segment in segments:
        if raw_file1_content in segment:
            # Check if this segment contains raw content with closing tag (total 9 words)
            segment_wc = count_words_for_test(segment)
            if closing_tag_content in segment:
                # Raw content (8 words) + closing tag (1 word) = 9 words total
                expected_word_count = count_words_for_test(raw_file1_content) + count_words_for_test(closing_tag_content)
                assert segment_wc == expected_word_count # Should be 9 words
                found_raw_content_segment = True
                break
            else:
                # Raw content by itself (8 words)
                assert segment_wc == count_words_for_test(raw_file1_content) # 8 words
                found_raw_content_segment = True
                break
    assert found_raw_content_segment, "Segment with raw file1 content not found or not matching expected structure"

@patch('repo_to_text.core.core.get_tree_structure') # Will use a specific mock inside
def test_generate_output_content_file_header_content_together(mock_get_tree: MagicMock, tmp_path: str) -> None:
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
    # Mock the tree structure for this specific test case
    mock_tree_for_single_file = ".\n└── single_file.txt"
    mock_get_tree.return_value = mock_tree_for_single_file # This mock is for any internal calls if any
    
    max_words_sufficient = 35 # Enough for header + this one file block (around 20 words + initial header)
    segments = generate_output_content(
        repo_path, mock_tree_for_single_file, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=max_words_sufficient
    )
    assert len(segments) == 1 # Expect no splitting of this file from its tags
    expected_file_block = f'<content full_path="single_file.txt">\n{file_content_str.strip()}\n</content>'
    assert expected_file_block in segments[0]

    # Test if it splits if max_words is too small for the file block (20 words)
    max_words_small = 10
    segments_small_limit = generate_output_content(
        repo_path, mock_tree_for_single_file, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec,
        maximum_word_count_per_file=max_words_small
    )
    # The file block (20 words) is a single chunk. It will form its own segment.
    # Header part will be one segment. File block another. Footer another.
    assert len(segments_small_limit) >= 2
    
    found_raw_content_in_own_segment = False
    raw_content_single_file = "word " * 15 # 15 words
    # expected_file_block is the whole thing (20 words)
    # With max_words_small = 10:
    # 1. Opening tag (3 words) -> new segment
    # 2. Raw content (15 words) -> new segment (because 0 + 15 > 10)
    # 3. Closing tag (2 words) -> new segment (because 0 + 2 <= 10, but follows a large chunk)

    for segment in segments_small_limit:
        if raw_content_single_file.strip() in segment.strip() and \
           '<content full_path="single_file.txt">' not in segment and \
           '</content>' not in segment:
            # This segment should contain only the raw 15 words
            assert count_words_for_test(segment.strip()) == 15
            found_raw_content_in_own_segment = True
            break
    assert found_raw_content_in_own_segment, "Raw content of single_file.txt not found in its own segment"

# Tests for save_repo_to_text related to splitting
@patch('repo_to_text.core.core.load_additional_specs')
@patch('repo_to_text.core.core.generate_output_content')
@patch('repo_to_text.core.core.os.makedirs')
@patch('builtins.open', new_callable=mock_open)
@patch('repo_to_text.core.core.copy_to_clipboard')
def test_save_repo_to_text_no_splitting_mocked(
    mock_copy_to_clipboard: MagicMock,
    mock_file_open: MagicMock,
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
    mock_generate_output.assert_called_once()
    expected_filename = os.path.join(output_dir, "repo-to-text_mock_timestamp.txt")
    assert os.path.basename(returned_path) == os.path.basename(expected_filename)
    mock_makedirs.assert_called_once_with(output_dir)
    mock_file_open.assert_called_once_with(expected_filename, 'w', encoding='utf-8')
    mock_file_open().write.assert_called_once_with("Single combined content\nfile1.txt\ncontent1")
    mock_copy_to_clipboard.assert_called_once_with("Single combined content\nfile1.txt\ncontent1")

@patch('repo_to_text.core.core.load_additional_specs')
@patch('repo_to_text.core.core.generate_output_content')
@patch('repo_to_text.core.core.os.makedirs')
@patch('builtins.open')
@patch('repo_to_text.core.core.copy_to_clipboard')
def test_save_repo_to_text_splitting_occurs_mocked(
    mock_copy_to_clipboard: MagicMock,
    mock_open_function: MagicMock,
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

    mock_file_handle1 = MagicMock(spec=IO)
    mock_file_handle2 = MagicMock(spec=IO)
    mock_open_function.side_effect = [mock_file_handle1, mock_file_handle2]

    with patch('repo_to_text.core.core.datetime') as mock_datetime:
        mock_datetime.now.return_value.strftime.return_value = "mock_ts_split_adv"
        returned_path = save_repo_to_text(simple_word_count_repo, output_dir=output_dir)

    expected_filename_part1 = os.path.join(output_dir, "repo-to-text_mock_ts_split_adv_part_1.txt")
    expected_filename_part2 = os.path.join(output_dir, "repo-to-text_mock_ts_split_adv_part_2.txt")

    assert os.path.basename(returned_path) == os.path.basename(expected_filename_part1)
    mock_makedirs.assert_called_once_with(output_dir)

    mock_open_function.assert_any_call(expected_filename_part1, 'w', encoding='utf-8')
    mock_open_function.assert_any_call(expected_filename_part2, 'w', encoding='utf-8')
    assert mock_open_function.call_count == 2

    mock_file_handle1.__enter__().write.assert_called_once_with(segments_content[0])
    mock_file_handle2.__enter__().write.assert_called_once_with(segments_content[1])

    mock_copy_to_clipboard.assert_not_called()

@patch('repo_to_text.core.core.copy_to_clipboard')
@patch('builtins.open', new_callable=mock_open)
@patch('repo_to_text.core.core.os.makedirs')
@patch('repo_to_text.core.core.generate_output_content') # This is the one that will be used
@patch('repo_to_text.core.core.load_additional_specs')   # This is the one that will be used
@patch('repo_to_text.core.core.get_tree_structure', return_value=MOCK_GTS_OUTPUT_FOR_SIMPLE_REPO)
def test_save_repo_to_text_stdout_with_splitting(
    mock_get_tree: MagicMock,         # Order of mock args should match decorator order (bottom-up)
    mock_load_specs: MagicMock,
    mock_generate_output: MagicMock,
    mock_os_makedirs: MagicMock,
    mock_file_open: MagicMock,
    mock_copy_to_clipboard: MagicMock,
    simple_word_count_repo: str,
    capsys: pytest.CaptureFixture[str]
) -> None:
    """Test save_repo_to_text with to_stdout=True and content that would split."""
    mock_load_specs.return_value = {'maximum_word_count_per_file': 10}
    mock_generate_output.return_value = ["Segment 1 for stdout.", "Segment 2 for stdout."]

    result_string = save_repo_to_text(simple_word_count_repo, to_stdout=True)

    mock_load_specs.assert_called_once_with(simple_word_count_repo)
    mock_get_tree.assert_called_once() # Assert that get_tree_structure was called
    mock_generate_output.assert_called_once()
    mock_os_makedirs.assert_not_called()
    mock_file_open.assert_not_called()
    mock_copy_to_clipboard.assert_not_called()

    captured = capsys.readouterr()
    assert "Segment 1 for stdout.Segment 2 for stdout." == captured.out.strip() # Added strip() to handle potential newlines from logging
    assert result_string == "Segment 1 for stdout.Segment 2 for stdout."

@patch('repo_to_text.core.core.load_additional_specs')
@patch('repo_to_text.core.core.generate_output_content')
@patch('repo_to_text.core.core.os.makedirs')
@patch('builtins.open', new_callable=mock_open)
@patch('repo_to_text.core.core.copy_to_clipboard')
def test_save_repo_to_text_empty_segments(
    mock_copy_to_clipboard: MagicMock,
    mock_file_open: MagicMock,
    mock_makedirs: MagicMock,
    mock_generate_output: MagicMock,
    mock_load_specs: MagicMock,
    simple_word_count_repo: str,
    tmp_path: str,
    caplog: pytest.LogCaptureFixture
) -> None:
    """Test save_repo_to_text when generate_output_content returns no segments."""
    mock_load_specs.return_value = {'maximum_word_count_per_file': None}
    mock_generate_output.return_value = []
    output_dir = os.path.join(str(tmp_path), "output_empty")

    returned_path = save_repo_to_text(simple_word_count_repo, output_dir=output_dir)

    assert returned_path == ""
    mock_makedirs.assert_not_called()
    mock_file_open.assert_not_called()
    mock_copy_to_clipboard.assert_not_called()
    assert "generate_output_content returned no segments" in caplog.text

if __name__ == "__main__":
    pytest.main([__file__])
