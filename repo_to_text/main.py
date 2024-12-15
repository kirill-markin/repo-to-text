import os
import subprocess
import shutil
import logging
import argparse
import yaml
from datetime import datetime, timezone
import textwrap

# Importing the missing pathspec module
import pathspec

def setup_logging(debug=False):
    logging_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

def check_tree_command():
    """Check if the `tree` command is available, and suggest installation if not."""
    if shutil.which('tree') is None:
        print("The 'tree' command is not found. Please install it using one of the following commands:")
        print("For Debian-based systems (e.g., Ubuntu): sudo apt-get install tree")
        print("For Red Hat-based systems (e.g., Fedora, CentOS): sudo yum install tree")
        return False
    return True

def get_tree_structure(path='.', gitignore_spec=None, tree_and_content_ignore_spec=None) -> str:
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
        # Find the index where the path starts (look for './' or absolute path)
        idx = line.find('./')
        if idx == -1:
            idx = line.find(path)
        if idx != -1:
            full_path = line[idx:].strip()
        else:
            # If neither './' nor the absolute path is found, skip the line
            continue
        
        # Skip the root directory '.'
        if full_path == '.':
            continue

        # Normalize paths
        relative_path = os.path.relpath(full_path, path)
        relative_path = relative_path.replace(os.sep, '/')
        if os.path.isdir(full_path):
            relative_path += '/'

        # Check if the file should be ignored
        if not should_ignore_file(full_path, relative_path, gitignore_spec, None, tree_and_content_ignore_spec):
            # Remove './' from display output for clarity
            display_line = line.replace('./', '', 1)
            filtered_lines.append(display_line)
        else:
            logging.debug(f'Ignored: {relative_path}')

    filtered_tree_output = '\n'.join(filtered_lines)
    logging.debug(f'Filtered tree structure:\n{filtered_tree_output}')
    logging.debug('Tree structure filtering complete')
    return filtered_tree_output

def load_ignore_specs(path='.', cli_ignore_patterns=None):
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

def should_ignore_file(file_path, relative_path, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec):
    # Normalize relative_path to use forward slashes
    relative_path = relative_path.replace(os.sep, '/')

    # Remove leading './' if present
    if relative_path.startswith('./'):
        relative_path = relative_path[2:]

    # Append '/' to directories to match patterns ending with '/'
    if os.path.isdir(file_path):
        relative_path += '/'

    result = (
        is_ignored_path(file_path) or
        (gitignore_spec and gitignore_spec.match_file(relative_path)) or
        (content_ignore_spec and content_ignore_spec.match_file(relative_path)) or
        (tree_and_content_ignore_spec and tree_and_content_ignore_spec.match_file(relative_path)) or
        os.path.basename(file_path).startswith('repo-to-text_')
    )

    logging.debug(f'Checking if file should be ignored:')
    logging.debug(f'    file_path: {file_path}')
    logging.debug(f'    relative_path: {relative_path}')
    logging.debug(f'    Result: {result}')
    return result

def is_ignored_path(file_path: str) -> bool:
    ignored_dirs = ['.git']
    ignored_files_prefix = ['repo-to-text_']
    is_ignored_dir = any(ignored in file_path for ignored in ignored_dirs)
    is_ignored_file = any(file_path.startswith(prefix) for prefix in ignored_files_prefix)
    result = is_ignored_dir or is_ignored_file
    if result:
        logging.debug(f'Path ignored: {file_path}')
    return result

def remove_empty_dirs(tree_output: str, path='.') -> str:
    logging.debug('Removing empty directories from tree output')
    lines = tree_output.splitlines()
    non_empty_dirs = set()
    filtered_lines = []

    for line in lines:
        parts = line.strip().split()
        if parts:
            full_path = parts[-1]
            if os.path.isdir(full_path) and not any(os.path.isfile(os.path.join(full_path, f)) for f in os.listdir(full_path)):
                logging.debug(f'Directory is empty and will be removed: {full_path}')
                continue
            non_empty_dirs.add(os.path.dirname(full_path))
            filtered_lines.append(line)
    
    final_lines = []
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

def save_repo_to_text(path='.', output_dir=None, to_stdout=False, cli_ignore_patterns=None) -> str:
    logging.debug(f'Starting to save repo structure to text for path: {path}')
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path, cli_ignore_patterns)
    tree_structure = get_tree_structure(path, gitignore_spec, tree_and_content_ignore_spec)
    tree_structure = remove_empty_dirs(tree_structure, path)
    logging.debug(f'Final tree structure to be written: {tree_structure}')
    
    # Add timestamp to the output file name with a descriptive name
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M-%S-UTC')
    output_file = f'repo-to-text_{timestamp}.txt'
    
    # Determine the full path to the output file
    if output_dir:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file = os.path.join(output_dir, output_file)
    
    output_content = []
    project_name = os.path.basename(os.path.abspath(path))
    output_content.append(f'Directory: {project_name}\n\n')
    output_content.append('Directory Structure:\n')
    output_content.append('```\n.\n')

    # Insert .gitignore if it exists
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
    
    # Try to copy to clipboard if pyperclip is installed
    try:
        import importlib.util
        if importlib.util.find_spec("pyperclip"):
            # Import pyperclip only if it's available
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

def create_default_settings_file():
    settings_file = '.repo-to-text-settings.yaml'
    if os.path.exists(settings_file):
        raise FileExistsError(f"The settings file '{settings_file}' already exists. Please remove it or rename it if you want to create a new default settings file.")
    
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
    with open('.repo-to-text-settings.yaml', 'w') as f:
        f.write(default_settings)
    print("Default .repo-to-text-settings.yaml created.")

def main():
    parser = argparse.ArgumentParser(description='Convert repository structure and contents to text')
    parser.add_argument('input_dir', nargs='?', default='.', help='Directory to process')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--output-dir', type=str, help='Directory to save the output file')
    parser.add_argument('--create-settings', '--init', action='store_true', help='Create default .repo-to-text-settings.yaml file')
    parser.add_argument('--stdout', action='store_true', help='Output to stdout instead of a file')
    parser.add_argument('--ignore-patterns', nargs='*', help="List of files or directories to ignore in both tree and content sections. Supports wildcards (e.g., '*').")
    args = parser.parse_args()

    setup_logging(debug=args.debug)
    logging.debug('repo-to-text script started')
    
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

if __name__ == '__main__':
    main()
