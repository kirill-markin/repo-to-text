import os
import subprocess
import pathspec
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_tree_structure(path='.', gitignore_spec=None) -> str:
    logging.debug(f'Generating tree structure for path: {path}')
    result = subprocess.run(['tree', '-a', '-f', '--noreport', path], stdout=subprocess.PIPE)
    tree_output = result.stdout.decode('utf-8')

    if not gitignore_spec:
        logging.debug('No .gitignore specification found')
        return tree_output

    logging.debug('Filtering tree output based on .gitignore specification')
    filtered_lines = []
    for line in tree_output.splitlines():
        parts = line.strip().split()
        if parts:
            full_path = parts[-1]
            relative_path = os.path.relpath(full_path, path)
            if not gitignore_spec.match_file(relative_path) and not is_ignored_path(relative_path):
                filtered_lines.append(line.replace('./', '', 1))
    
    logging.debug('Tree structure filtering complete')
    return '\n'.join(filtered_lines)

def load_gitignore(path='.'):
    gitignore_path = os.path.join(path, '.gitignore')
    if os.path.exists(gitignore_path):
        logging.debug(f'Loading .gitignore from path: {gitignore_path}')
        with open(gitignore_path, 'r') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    logging.debug('.gitignore not found')
    return None

def is_ignored_path(file_path: str) -> bool:
    ignored_dirs = ['.git']
    result = any(ignored in file_path for ignored in ignored_dirs)
    if result:
        logging.debug(f'Path ignored: {file_path}')
    return result

def remove_empty_dirs(tree_output: str) -> str:
    logging.debug('Removing empty directories from tree output')
    lines = tree_output.splitlines()
    non_empty_dirs = set()
    filtered_lines = []

    for line in reversed(lines):
        logging.debug(f'Processing line: {line}')
        if line.strip().endswith('/'):
            logging.debug('Line is a directory')
            if any(line.strip() in dir_line for dir_line in non_empty_dirs):
                filtered_lines.append(line)
        else:
            non_empty_dirs.add(line)
            filtered_lines.append(line)
    
    logging.debug('Empty directory removal complete')
    return '\n'.join(reversed(filtered_lines))

def save_repo_to_text(path='.') -> None:
    logging.debug(f'Starting to save repo structure to text for path: {path}')
    gitignore_spec = load_gitignore(path)
    tree_structure = get_tree_structure(path, gitignore_spec)
    tree_structure = remove_empty_dirs(tree_structure)
    
    output_file = 'repo_structure.txt'
    with open(output_file, 'w') as file:
        file.write(tree_structure + '\n')
        logging.debug('Tree structure written to file')

        for root, _, files in os.walk(path):
            for filename in files:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, path)
                
                if is_ignored_path(file_path) or (gitignore_spec and gitignore_spec.match_file(relative_path)):
                    continue

                relative_path = relative_path.replace('./', '', 1)
                
                file.write(f'\n{relative_path}\n')
                file.write('```\n')
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file.write(f.read())
                except UnicodeDecodeError:
                    logging.error(f'Could not decode file contents: {file_path}')
                    file.write('[Could not decode file contents]\n')
                file.write('\n```\n')
        logging.debug('Repository contents written to file')

def main() -> None:
    save_repo_to_text()

if __name__ == '__main__':
    logging.debug('repo-to-text script started')
    main()
    logging.debug('repo-to-text script finished')
