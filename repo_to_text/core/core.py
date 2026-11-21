"""
Core functionality for repo-to-text
"""

import os
from typing import Tuple, Optional, List, Dict, Any, NamedTuple
from datetime import datetime, timezone
from importlib.machinery import ModuleSpec
import logging
import yaml # type: ignore
import pathspec
from pathspec import PathSpec

from ..utils.utils import is_ignored_path

class TreeNode(NamedTuple):
    """One line of the directory tree with the lines nested under it."""
    label: str
    children: List['TreeNode']

def get_tree_structure(
        path: str = '.',
        gitignore_spec: Optional[PathSpec] = None,
        tree_and_content_ignore_spec: Optional[PathSpec] = None
    ) -> str:
    """Generate the tree lines below the root `.` line, without a trailing newline.

    Folders without kept entries are hidden, symlinks are shown as
    `path -> target` and never followed.
    """
    logging.debug('Generating tree structure for path: %s', path)
    nodes = _build_tree_nodes(
        path, '', os.listdir(path), gitignore_spec, tree_and_content_ignore_spec
    )
    return '\n'.join(_render_tree_lines(nodes, ''))

def _build_tree_nodes(
        directory: str,
        relative_directory: str,
        names: List[str],
        gitignore_spec: Optional[PathSpec],
        tree_and_content_ignore_spec: Optional[PathSpec]
    ) -> List[TreeNode]:
    """Build kept tree nodes for the entries of one directory."""
    nodes: List[TreeNode] = []
    for name in sorted(names, key=lambda entry: (entry.lower(), entry)):
        full_path = os.path.join(directory, name)
        relative_path = f'{relative_directory}/{name}' if relative_directory else name
        if should_ignore_file(
            full_path,
            relative_path,
            gitignore_spec,
            None,
            tree_and_content_ignore_spec
        ):
            continue

        label = _escape_tree_label(relative_path)
        if os.path.islink(full_path):
            target = _escape_tree_label(os.readlink(full_path))
            nodes.append(TreeNode(f'{label} -> {target}', []))
        elif os.path.isdir(full_path):
            try:
                child_names = os.listdir(full_path)
            except OSError as err:
                logging.warning('Cannot open directory %s: %s', full_path, err)
                nodes.append(TreeNode(f'{label}  [error opening dir]', []))
                continue
            children = _build_tree_nodes(
                full_path,
                relative_path,
                child_names,
                gitignore_spec,
                tree_and_content_ignore_spec
            )
            if children:
                nodes.append(TreeNode(label, children))
        else:
            nodes.append(TreeNode(label, []))
    return nodes

def _escape_tree_label(label: str) -> str:
    """Escape non-printable characters as backslash-octal UTF-8 bytes, like `tree`."""
    return ''.join(
        char if char.isprintable() else ''.join(
            f'\\{byte:03o}' for byte in char.encode('utf-8', 'surrogateescape')
        )
        for char in label
    )

def _render_tree_lines(nodes: List[TreeNode], prefix: str) -> List[str]:
    """Render tree nodes as `tree`-style lines with connectors."""
    lines: List[str] = []
    for index, node in enumerate(nodes):
        is_last = index == len(nodes) - 1
        lines.append(prefix + ('└── ' if is_last else '├── ') + node.label)
        lines.extend(
            _render_tree_lines(node.children, prefix + ('    ' if is_last else '│   '))
        )
    return lines

def load_ignore_specs(
        path: str = '.',
        cli_ignore_patterns: Optional[List[str]] = None
    ) -> Tuple[Optional[PathSpec], Optional[PathSpec], PathSpec]:
    """Load ignore specifications from various sources.
    
    Args:
        path: Base directory path
        cli_ignore_patterns: List of patterns from command line
        
    Returns:
        Tuple[Optional[PathSpec], Optional[PathSpec], PathSpec]: Tuple of gitignore_spec,
        content_ignore_spec, and tree_and_content_ignore_spec
    """
    gitignore_spec = None
    content_ignore_spec = None
    tree_and_content_ignore_list: List[str] = []
    use_gitignore = True

    repo_settings_path = os.path.join(path, '.repo-to-text-settings.yaml')
    if os.path.exists(repo_settings_path):
        logging.debug(
            'Loading .repo-to-text-settings.yaml for ignore specs from path: %s',
            repo_settings_path
        )
        with open(repo_settings_path, 'r', encoding='utf-8') as f:
            settings: Dict[str, Any] = yaml.safe_load(f)
            use_gitignore = settings.get('gitignore-import-and-ignore', True)
            if 'ignore-content' in settings:
                content_ignore_spec = pathspec.PathSpec.from_lines(
                    'gitwildmatch', settings['ignore-content']
                )
            if 'ignore-tree-and-content' in settings:
                tree_and_content_ignore_list.extend(
                    settings.get('ignore-tree-and-content', [])
                )

    if cli_ignore_patterns:
        tree_and_content_ignore_list.extend(cli_ignore_patterns)

    if use_gitignore:
        gitignore_path = os.path.join(path, '.gitignore')
        if os.path.exists(gitignore_path):
            logging.debug('Loading .gitignore from path: %s', gitignore_path)
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', f)

    tree_and_content_ignore_spec = pathspec.PathSpec.from_lines(
        'gitwildmatch', tree_and_content_ignore_list
    )
    return gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec

def load_additional_specs(path: str = '.') -> Dict[str, Any]:
    """Load additional specifications from the settings file."""
    additional_specs: Dict[str, Any] = {
        'maximum_word_count_per_file': None
    }
    repo_settings_path = os.path.join(path, '.repo-to-text-settings.yaml')
    if os.path.exists(repo_settings_path):
        logging.debug(
            'Loading .repo-to-text-settings.yaml for additional specs from path: %s',
            repo_settings_path
        )
        with open(repo_settings_path, 'r', encoding='utf-8') as f:
            settings: Dict[str, Any] = yaml.safe_load(f)
            if 'maximum_word_count_per_file' in settings:
                max_words = settings['maximum_word_count_per_file']
                if isinstance(max_words, int) and max_words > 0:
                    additional_specs['maximum_word_count_per_file'] = max_words
                elif max_words is not None: # Allow null/None to mean "not set"
                    logging.warning(
                        "Invalid value for 'maximum_word_count_per_file': %s. "
                        "It must be a positive integer or null. Ignoring.", max_words
                    )
    return additional_specs

def should_ignore_file(
    file_path: str,
    relative_path: str,
    gitignore_spec: Optional[PathSpec],
    content_ignore_spec: Optional[PathSpec],
    tree_and_content_ignore_spec: Optional[PathSpec]
) -> bool:
    """Check if a file should be ignored based on various ignore specifications.
    
    Args:
        file_path: Full path to the file
        relative_path: Path relative to the repository root
        gitignore_spec: PathSpec object for gitignore patterns
        content_ignore_spec: PathSpec object for content ignore patterns
        tree_and_content_ignore_spec: PathSpec object for tree and content ignore patterns
        
    Returns:
        bool: True if file should be ignored, False otherwise
    """
    relative_path = relative_path.replace(os.sep, '/')

    if relative_path.startswith('./'):
        relative_path = relative_path[2:]

    if os.path.isdir(file_path):
        relative_path += '/'

    result = (
        is_ignored_path(file_path) or
        bool(
            gitignore_spec and
            gitignore_spec.match_file(relative_path)
        ) or
        bool(
            content_ignore_spec and
            content_ignore_spec.match_file(relative_path)
        ) or
        bool(
            tree_and_content_ignore_spec and
            tree_and_content_ignore_spec.match_file(relative_path)
        ) or
        os.path.basename(file_path).startswith('repo-to-text_')
    )

    logging.debug('Checking if file should be ignored:')
    logging.debug('    file_path: %s', file_path)
    logging.debug('    relative_path: %s', relative_path)
    logging.debug('    Result: %s', result)
    return result

def save_repo_to_text(
        path: str = '.',
        output_dir: Optional[str] = None,
        to_stdout: bool = False,
        cli_ignore_patterns: Optional[List[str]] = None,
        skip_binary: bool = False
    ) -> str:
    """Save repository structure and contents to a text file or multiple files."""
    # pylint: disable=too-many-locals
    logging.debug('Starting to save repo structure to text for path: %s', path)
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = (
        load_ignore_specs(path, cli_ignore_patterns)
    )
    additional_specs = load_additional_specs(path)
    maximum_word_count_per_file = additional_specs.get(
        'maximum_word_count_per_file'
    )

    tree_structure: str = get_tree_structure(
        path, gitignore_spec, tree_and_content_ignore_spec
    )
    logging.debug('Final tree structure to be written: %s', tree_structure)

    output_content_segments = generate_output_content(
        path,
        tree_structure,
        gitignore_spec,
        content_ignore_spec,
        tree_and_content_ignore_spec,
        maximum_word_count_per_file,
        skip_binary
    )

    if to_stdout:
        for segment in output_content_segments:
            print(segment, end='') # Avoid double newlines if segments naturally end with one
        # Return joined content for consistency, though primarily printed
        return "".join(output_content_segments)

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M-%S-UTC')
    base_output_name_stem = f'repo-to-text_{timestamp}'
    
    output_filepaths: List[str] = []

    if not output_content_segments:
        logging.warning(
            "generate_output_content returned no segments. No output file will be created."
        )
        return "" # Or handle by creating an empty placeholder file

    if len(output_content_segments) == 1:
        single_filename = f"{base_output_name_stem}.txt"
        full_path_single_file = (
            os.path.join(output_dir, single_filename) if output_dir else single_filename
        )
        
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        with open(full_path_single_file, 'w', encoding='utf-8') as f:
            f.write(output_content_segments[0])
        output_filepaths.append(full_path_single_file)
        copy_to_clipboard(output_content_segments[0])
        # Use basename for safe display in case relpath fails
        display_path = os.path.basename(full_path_single_file)
        print(
            "[SUCCESS] Repository structure and contents successfully saved to "
            f"file: \"{display_path}\""
        )
    else: # Multiple segments
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir) # Create output_dir once if needed

        for i, segment_content in enumerate(output_content_segments):
            part_filename = f"{base_output_name_stem}_part_{i+1}.txt"
            full_path_part_file = (
                os.path.join(output_dir, part_filename) if output_dir else part_filename
            )
            
            with open(full_path_part_file, 'w', encoding='utf-8') as f:
                f.write(segment_content)
            output_filepaths.append(full_path_part_file)
        
        print(
            f"[SUCCESS] Repository structure and contents successfully saved to "
            f"{len(output_filepaths)} files:"
        )
        for fp in output_filepaths:
            # Use basename for safe display in case relpath fails
            display_path = os.path.basename(fp)
            print(f"  - \"{display_path}\"")
            
    if output_filepaths:
        # Return the actual file path for existence checks
        return output_filepaths[0]
    return ""

def _read_file_content(file_path: str, skip_binary: bool = False) -> str:
    """Read file content, handling binary files and broken symlinks.
    
    Args:
        file_path: Path to the file to read
        skip_binary: Whether to skip binary files
        
    Returns:
        str: File content or appropriate message for special cases
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        if skip_binary:
            logging.debug('Skipping binary file: %s', file_path)
            return "binary content skipped"
        logging.debug('Handling binary file contents: %s', file_path)
        with open(file_path, 'rb') as f_bin:
            binary_content: bytes = f_bin.read()
        return binary_content.decode('latin1')
    except FileNotFoundError as e:
        # Minimal handling for bad symlinks
        if os.path.islink(file_path) and not os.path.exists(file_path):
            try:
                target = os.readlink(file_path)
            except OSError:
                target = ''
            return f"[symlink] -> {target}"
        raise e


def generate_output_content(
        path: str,
        tree_structure: str,
        gitignore_spec: Optional[PathSpec],
        content_ignore_spec: Optional[PathSpec],
        tree_and_content_ignore_spec: Optional[PathSpec],
        maximum_word_count_per_file: Optional[int] = None,
        skip_binary: bool = False
    ) -> List[str]:
    """Generate the output content for the repository, potentially split into segments."""
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-positional-arguments
    output_segments: List[str] = []
    current_segment_builder: List[str] = []
    current_segment_word_count: int = 0
    project_name = os.path.basename(os.path.abspath(path))

    def count_words(text: str) -> int:
        return len(text.split())

    def _finalize_current_segment():
        nonlocal current_segment_word_count # Allow modification
        if current_segment_builder:
            output_segments.append("".join(current_segment_builder))
            current_segment_builder.clear()
            current_segment_word_count = 0
    
    def _add_chunk_to_output(chunk: str):
        nonlocal current_segment_word_count
        chunk_wc = count_words(chunk)

        if maximum_word_count_per_file is not None:
            # If current segment is not empty, and adding this chunk would exceed limit,
            # finalize the current segment before adding this new chunk.
            if (current_segment_builder and 
                current_segment_word_count + chunk_wc > maximum_word_count_per_file):
                _finalize_current_segment()
        
        current_segment_builder.append(chunk)
        current_segment_word_count += chunk_wc
        
        # This logic ensures that if a single chunk itself is larger than the limit,
        # it forms its own segment. The next call to _add_chunk_to_output
        # or the final _finalize_current_segment will commit it.

    _add_chunk_to_output('<repo-to-text>\n')
    _add_chunk_to_output(f'Directory: {project_name}\n\n')
    _add_chunk_to_output('Directory Structure:\n')
    _add_chunk_to_output('<directory_structure>\n.\n')
    _add_chunk_to_output(tree_structure + '\n' + '</directory_structure>\n')
    logging.debug('Tree structure added to output content segment builder')

    for root, _, files in os.walk(path):
        for filename in files:
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, path)

            if should_ignore_file(
                file_path,
                relative_path,
                gitignore_spec,
                content_ignore_spec,
                tree_and_content_ignore_spec
            ):
                continue

            cleaned_relative_path = relative_path.replace('./', '', 1)
            
            _add_chunk_to_output(f'\n<content full_path="{cleaned_relative_path}">\n')
            file_content = _read_file_content(file_path, skip_binary)
            _add_chunk_to_output(file_content)
            _add_chunk_to_output('\n</content>\n')

    _add_chunk_to_output('\n</repo-to-text>\n')
    
    _finalize_current_segment() # Finalize any remaining content in the builder

    logging.debug(
        'Repository contents generated into %s segment(s)', len(output_segments)
    )
    
    # Ensure at least one segment is returned, even if it's just the empty repo structure
    if not output_segments and not current_segment_builder:
        # This case implies an empty repo and an extremely small word limit that split
        # even the minimal tags. Or, if all content was filtered out.
        # Return a minimal valid structure if everything else resulted in empty.
        # However, the _add_chunk_to_output for repo tags should ensure
        # current_segment_builder is not empty. And _finalize_current_segment ensures
        # output_segments gets it. If output_segments is truly empty, it means an error
        # or unexpected state. For safety, if it's empty, return a list with one empty
        # string or minimal tags. Given the logic, this path is unlikely.
        logging.warning(
            "No output segments were generated. Returning a single empty segment."
        )
        return ["<repo-to-text>\n</repo-to-text>\n"]


    return output_segments


# The original write_output_to_file function is no longer needed as its logic
# is incorporated into save_repo_to_text for handling single/multiple files.

def copy_to_clipboard(output_content: str) -> None:
    """Copy the output content to the clipboard if possible."""
    try:
        import importlib.util  # pylint: disable=import-outside-toplevel
        spec: Optional[ModuleSpec] = importlib.util.find_spec("pyperclip")  # type: ignore
        if spec:
            import pyperclip  # pylint: disable=import-outside-toplevel # type: ignore
            pyperclip.copy(output_content)  # type: ignore
            logging.debug('Repository structure and contents copied to clipboard')
        else:
            print("Tip: Install 'pyperclip' package to enable automatic clipboard copying:")
            print("     pip install pyperclip")
    except ImportError as e:
        logging.warning(
            'Could not copy to clipboard. You might be running this '
            'script over SSH or without clipboard support.'
        )
        logging.debug('Clipboard copy error: %s', e)
