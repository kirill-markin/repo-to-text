import os
import tempfile
import shutil
import pytest
from typing import Generator
from repo_to_text.core.core import (
    get_tree_structure,
    load_ignore_specs,
    should_ignore_file,
    is_ignored_path,
    remove_empty_dirs,
    save_repo_to_text
)

@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def sample_repo(temp_dir: str) -> str:
    """Create a sample repository structure for testing."""
    # Create directories
    os.makedirs(os.path.join(temp_dir, "src"))
    os.makedirs(os.path.join(temp_dir, "tests"))
    
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
"""
    }
    
    for file_path, content in files.items():
        full_path = os.path.join(temp_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
    
    return temp_dir

def test_is_ignored_path() -> None:
    """Test the is_ignored_path function."""
    assert is_ignored_path(".git/config") is True
    assert is_ignored_path("repo-to-text_output.txt") is True
    assert is_ignored_path("src/main.py") is False
    assert is_ignored_path("normal_file.txt") is False

def test_load_ignore_specs(sample_repo: str) -> None:
    """Test loading ignore specifications from files."""
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(sample_repo)
    
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
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(sample_repo)
    
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

def test_remove_empty_dirs(temp_dir: str) -> None:
    """Test removal of empty directories from tree output."""
    # Create test directory structure
    os.makedirs(os.path.join(temp_dir, "src"))
    os.makedirs(os.path.join(temp_dir, "empty_dir"))
    os.makedirs(os.path.join(temp_dir, "tests"))
    
    # Create some files
    with open(os.path.join(temp_dir, "src/main.py"), "w") as f:
        f.write("print('test')")
    with open(os.path.join(temp_dir, "tests/test_main.py"), "w") as f:
        f.write("def test(): pass")
    
    # Create a mock tree output that matches the actual tree command format
    tree_output = (
        f"{temp_dir}\n"
        f"├── {os.path.join(temp_dir, 'src')}\n"
        f"│   └── {os.path.join(temp_dir, 'src/main.py')}\n"
        f"├── {os.path.join(temp_dir, 'empty_dir')}\n"
        f"└── {os.path.join(temp_dir, 'tests')}\n"
        f"    └── {os.path.join(temp_dir, 'tests/test_main.py')}\n"
    )
    
    filtered_output = remove_empty_dirs(tree_output, temp_dir)
    
    # Check that empty_dir is removed but other directories remain
    assert "empty_dir" not in filtered_output
    assert os.path.join(temp_dir, "src") in filtered_output
    assert os.path.join(temp_dir, "tests") in filtered_output
    assert os.path.join(temp_dir, "src/main.py") in filtered_output
    assert os.path.join(temp_dir, "tests/test_main.py") in filtered_output

def test_save_repo_to_text(sample_repo: str) -> None:
    """Test the main save_repo_to_text function."""
    # Create output directory
    output_dir = os.path.join(sample_repo, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Create .git directory to ensure it's properly ignored
    os.makedirs(os.path.join(sample_repo, ".git"))
    with open(os.path.join(sample_repo, ".git/config"), "w") as f:
        f.write("[core]\n\trepositoryformatversion = 0\n")
    
    # Test file output
    output_file = save_repo_to_text(sample_repo, output_dir=output_dir)
    assert os.path.exists(output_file)
    assert os.path.dirname(output_file) == output_dir
    
    # Check file contents
    with open(output_file, 'r') as f:
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
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(sample_repo, cli_patterns)
    
    assert tree_and_content_ignore_spec.match_file("test.log") is True
    assert tree_and_content_ignore_spec.match_file("temp/file.txt") is True
    assert tree_and_content_ignore_spec.match_file("normal.txt") is False

def test_load_ignore_specs_without_gitignore(temp_dir: str) -> None:
    """Test loading ignore specs when .gitignore is missing."""
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(temp_dir)
    assert gitignore_spec is None
    assert content_ignore_spec is None
    assert tree_and_content_ignore_spec is not None

def test_get_tree_structure_with_special_chars(temp_dir: str) -> None:
    """Test tree structure generation with special characters in paths."""
    # Create files with special characters
    special_dir = os.path.join(temp_dir, "special chars")
    os.makedirs(special_dir)
    with open(os.path.join(special_dir, "file with spaces.txt"), "w") as f:
        f.write("test")
    
    tree_output = get_tree_structure(temp_dir)
    assert "special chars" in tree_output
    assert "file with spaces.txt" in tree_output

def test_should_ignore_file_edge_cases(sample_repo: str) -> None:
    """Test edge cases for should_ignore_file function."""
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(sample_repo)
    
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
    expected_content = f"Contents of binary.bin:\n```\n{binary_content.decode('latin1')}\n```"
    assert expected_content in output

def test_save_repo_to_text_custom_output_dir(temp_dir: str) -> None:
    """Test save_repo_to_text with custom output directory."""
    # Create a simple file structure
    with open(os.path.join(temp_dir, "test.txt"), "w") as f:
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

if __name__ == "__main__":
    pytest.main([__file__])