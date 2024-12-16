import os
import subprocess
import logging
import yaml
from datetime import datetime, timezone
from typing import Tuple, Optional
import pathspec
from pathspec import PathSpec

from ..utils.utils import check_tree_command, is_ignored_path, remove_empty_dirs

def get_tree_structure(path: str = '.', gitignore_spec: Optional[PathSpec] = None, tree_and_content_ignore_spec: Optional[PathSpec] = None) -> str:
    """Generate tree structure of the directory.
    
    Args:
        path: Directory path to generate tree for
        gitignore_spec: PathSpec object for gitignore patterns
        tree_and_content_ignore_spec: PathSpec object for tree and content ignore patterns
        
    Returns:
        str: Generated tree structure
    """
    if not check_tree_command():
        return ""
    
    logging.debug(f'Generating tree structure for path: {path}')
    result = subprocess.run(['tree', '-a', '-f', '--noreport', path], stdout=subprocess.PIPE)
    tree_output = result.stdout.decode('utf-8')
    logging.debug(f'Tree output generated:\n{tree_output}')

    if not gitignore_spec and not tree_and_content_ignore_spec:
        logging.debug('No .gitignore or ignore-tree-and-content specification found')
        return tree_output

    logging.debug('Filtering tree output based on .gitignore and ignore-tree-and-content specification')
    filtered_lines = []

    for line in tree_output.splitlines():
        idx = line.find('./')
        if idx == -1:
            idx = line.find(path)
        if idx != -1:
            full_path = line[idx:].strip()
        else:
            continue
        
        if full_path == '.':
            continue

        relative_path = os.path.relpath(full_path, path)
        relative_path = relative_path.replace(os.sep, '/')
        if os.path.isdir(full_path):
            relative_path += '/'

        if not should_ignore_file(full_path, relative_path, gitignore_spec, None, tree_and_content_ignore_spec):
            display_line = line.replace('./', '', 1)
            filtered_lines.append(display_line)
        else:
            logging.debug(f'Ignored: {relative_path}')

    filtered_tree_output = '\n'.join(filtered_lines)
    logging.debug(f'Filtered tree structure:\n{filtered_tree_output}')
    logging.debug('Tree structure filtering complete')
    return filtered_tree_output

def load_ignore_specs(path: str = '.', cli_ignore_patterns: Optional[list] = None) -> Tuple[Optional[PathSpec], Optional[PathSpec], PathSpec]:
    """Load ignore specifications from various sources.
    
    Args:
        path: Base directory path
        cli_ignore_patterns: List of patterns from command line
        
    Returns:
        Tuple[Optional[PathSpec], Optional[PathSpec], PathSpec]: Tuple of gitignore_spec, content_ignore_spec, and tree_and_content_ignore_spec
    """
    gitignore_spec = None
    content_ignore_spec = None
    tree_and_content_ignore_list = []
    use_gitignore = True

    repo_settings_path = os.path.join(path, '.repo-to-text-settings.yaml')
    if os.path.exists(repo_settings_path):
        logging.debug(f'Loading .repo-to-text-settings.yaml from path: {repo_settings_path}')
        with open(repo_settings_path, 'r') as f:
            settings = yaml.safe_load(f)
            use_gitignore = settings.get('gitignore-import-and-ignore', True)
            if 'ignore-content' in settings:
                content_ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', settings['ignore-content'])
            if 'ignore-tree-and-content' in settings:
                tree_and_content_ignore_list.extend(settings['ignore-tree-and-content'])

    if cli_ignore_patterns:
        tree_and_content_ignore_list.extend(cli_ignore_patterns)

    if use_gitignore:
        gitignore_path = os.path.join(path, '.gitignore')
        if os.path.exists(gitignore_path):
            logging.debug(f'Loading .gitignore from path: {gitignore_path}')
            with open(gitignore_path, 'r') as f:
                gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', f)

    tree_and_content_ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', tree_and_content_ignore_list)
    return gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec

def should_ignore_file(file_path: str, relative_path: str, gitignore_spec: Optional[PathSpec], 
                      content_ignore_spec: Optional[PathSpec], tree_and_content_ignore_spec: Optional[PathSpec]) -> bool:
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
        bool(gitignore_spec and gitignore_spec.match_file(relative_path)) or
        bool(content_ignore_spec and content_ignore_spec.match_file(relative_path)) or
        bool(tree_and_content_ignore_spec and tree_and_content_ignore_spec.match_file(relative_path)) or
        os.path.basename(file_path).startswith('repo-to-text_')
    )

    logging.debug(f'Checking if file should be ignored:')
    logging.debug(f'    file_path: {file_path}')
    logging.debug(f'    relative_path: {relative_path}')
    logging.debug(f'    Result: {result}')
    return result

def save_repo_to_text(path: str = '.', output_dir: Optional[str] = None, to_stdout: bool = False, cli_ignore_patterns: Optional[list] = None) -> str:
    """Save repository structure and contents to a text file.
    
    Args:
        path: Repository path
        output_dir: Directory to save output file
        to_stdout: Whether to output to stdout instead of file
        cli_ignore_patterns: List of patterns from command line
        
    Returns:
        str: Path to the output file or the output text if to_stdout is True
    """
    logging.debug(f'Starting to save repo structure to text for path: {path}')
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path, cli_ignore_patterns)
    tree_structure = get_tree_structure(path, gitignore_spec, tree_and_content_ignore_spec)
    tree_structure = remove_empty_dirs(tree_structure, path)
    logging.debug(f'Final tree structure to be written: {tree_structure}')
    
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M-%S-UTC')
    output_file = f'repo-to-text_{timestamp}.txt'
    
    if output_dir:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file = os.path.join(output_dir, output_file)
    
    output_content = []
    project_name = os.path.basename(os.path.abspath(path))
    output_content.append(f'Directory: {project_name}\n\n')
    output_content.append('Directory Structure:\n')
    output_content.append('```\n.\n')

    if os.path.exists(os.path.join(path, '.gitignore')):
        output_content.append('├── .gitignore\n')
    
    output_content.append(tree_structure + '\n' + '```\n')
    logging.debug('Tree structure written to output content')

    for root, _, files in os.walk(path):
        for filename in files:
            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, path)
            
            if should_ignore_file(file_path, relative_path, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec):
                continue

            relative_path = relative_path.replace('./', '', 1)
            
            output_content.append(f'\nContents of {relative_path}:\n')
            output_content.append('```\n')
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    output_content.append(f.read())
            except UnicodeDecodeError:
                logging.debug(f'Could not decode file contents: {file_path}')
                output_content.append('[Could not decode file contents]\n')
            output_content.append('\n```\n')

    output_content.append('\n')
    logging.debug('Repository contents written to output content')
    
    output_text = ''.join(output_content)
    
    if to_stdout:
        print(output_text)
        return output_text

    with open(output_file, 'w') as file:
        file.write(output_text)
    
    try:
        import importlib.util
        if importlib.util.find_spec("pyperclip"):
            import pyperclip # type: ignore
            pyperclip.copy(output_text)
            logging.debug('Repository structure and contents copied to clipboard')
        else:
            print("Tip: Install 'pyperclip' package to enable automatic clipboard copying:")
            print("     pip install pyperclip")
    except Exception as e:
        logging.warning('Could not copy to clipboard. You might be running this script over SSH or without clipboard support.')
        logging.debug(f'Clipboard copy error: {e}')
    
    print(f"[SUCCESS] Repository structure and contents successfully saved to file: \"./{output_file}\"")
    
    return output_file 