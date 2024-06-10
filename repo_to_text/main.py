import os
import subprocess
import pathspec
import logging
import argparse
import yaml
from datetime import datetime
import pyperclip

def setup_logging(debug=False):
    logging_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

def get_tree_structure(path='.', gitignore_spec=None, tree_and_content_ignore_spec=None) -> str:
    logging.debug(f'Generating tree structure for path: {path}')
    result = subprocess.run(['tree', '-a', '-f', '--noreport', path], stdout=subprocess.PIPE)
    tree_output = result.stdout.decode('utf-8')
    logging.debug(f'Tree output generated: {tree_output}')

    if not gitignore_spec and not tree_and_content_ignore_spec:
        logging.debug('No .gitignore or ignore-tree-and-content specification found')
        return tree_output

    logging.debug('Filtering tree output based on .gitignore and ignore-tree-and-content specification')
    filtered_lines = []
    for line in tree_output.splitlines():
        stripped_line = line.strip()
        if stripped_line:
            # Extract the path by removing the leading tree branch symbols
            full_path = stripped_line.split(maxsplit=1)[-1]
            relative_path = os.path.relpath(full_path, path)
            if not should_ignore_file(full_path, relative_path, gitignore_spec, None, tree_and_content_ignore_spec):
                filtered_lines.append(line.replace('./', '', 1))

    filtered_tree_output = '\n'.join(filtered_lines)
    logging.debug(f'Filtered tree structure: {filtered_tree_output}')
    logging.debug('Tree structure filtering complete')
    return filtered_tree_output

def load_ignore_specs(path='.'):
    gitignore_spec = None
    content_ignore_spec = None
    tree_and_content_ignore_spec = None
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
                tree_and_content_ignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', settings['ignore-tree-and-content'])

    if use_gitignore:
        gitignore_path = os.path.join(path, '.gitignore')
        if os.path.exists(gitignore_path):
            logging.debug(f'Loading .gitignore from path: {gitignore_path}')
            with open(gitignore_path, 'r') as f:
                gitignore_spec = pathspec.PathSpec.from_lines('gitwildmatch', f)

    return gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec

def should_ignore_file(file_path, relative_path, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec):
    result = (
        is_ignored_path(file_path) or
        (gitignore_spec and gitignore_spec.match_file(relative_path)) or
        (content_ignore_spec and content_ignore_spec.match_file(relative_path)) or
        (tree_and_content_ignore_spec and tree_and_content_ignore_spec.match_file(relative_path)) or
        os.path.basename(file_path).startswith('repo-to-text_')
    )
    
    logging.debug(f'Checking if file should be ignored: {file_path}, relative path: {relative_path}, result: {result}')
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
    return '\n'.join(final_lines)

def save_repo_to_text(path='.', output_dir=None) -> str:
    logging.debug(f'Starting to save repo structure to text for path: {path}')
    gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec = load_ignore_specs(path)
    tree_structure = get_tree_structure(path, gitignore_spec, tree_and_content_ignore_spec)
    tree_structure = remove_empty_dirs(tree_structure, path)
    logging.debug(f'Final tree structure to be written: {tree_structure}')
    
    # Add timestamp to the output file name with a descriptive name
    timestamp = datetime.utcnow().strftime('%Y-%m-%d-%H-%M-%S-UTC')
    output_file = f'repo-to-text_{timestamp}.txt'
    
    # Determine the full path to the output file
    if output_dir:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file = os.path.join(output_dir, output_file)
    
    with open(output_file, 'w') as file:
        project_name = os.path.basename(os.path.abspath(path))
        file.write(f'Directory: {project_name}\n\n')
        file.write('Directory Structure:\n')
        file.write('```\n.\n')

        # Insert .gitignore if it exists
        if os.path.exists(os.path.join(path, '.gitignore')):
            file.write('├── .gitignore\n')
        
        file.write(tree_structure + '\n' + '```\n')
        logging.debug('Tree structure written to file')

        for root, _, files in os.walk(path):
            for filename in files:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, path)
                
                if should_ignore_file(file_path, relative_path, gitignore_spec, content_ignore_spec, tree_and_content_ignore_spec):
                    continue

                relative_path = relative_path.replace('./', '', 1)
                
                file.write(f'\nContents of {relative_path}:\n')
                file.write('```\n')
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file.write(f.read())
                except UnicodeDecodeError:
                    logging.debug(f'Could not decode file contents: {file_path}')
                    file.write('[Could not decode file contents]\n')
                file.write('\n```\n')

        file.write('\n')
        logging.debug('Repository contents written to file')
    
    # Read the contents of the generated file
    with open(output_file, 'r') as file:
        repo_text = file.read()
    
    # Copy the contents to the clipboard
    pyperclip.copy(repo_text)
    logging.debug('Repository structure and contents copied to clipboard')
    
    return output_file

def main():
    parser = argparse.ArgumentParser(description='Convert repository structure and contents to text')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--output-dir', type=str, help='Directory to save the output file')
    args = parser.parse_args()

    setup_logging(debug=args.debug)
    logging.debug('repo-to-text script started')
    save_repo_to_text(output_dir=args.output_dir)
    logging.debug('repo-to-text script finished')

if __name__ == '__main__':
    main()
