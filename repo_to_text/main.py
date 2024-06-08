import os
import subprocess
import pathspec

def get_tree_structure(path='.', gitignore_spec=None) -> str:
    result = subprocess.run(['tree', '-a', '-f', '--noreport', path], stdout=subprocess.PIPE)
    tree_output = result.stdout.decode('utf-8')

    if not gitignore_spec:
        return tree_output

    filtered_lines = []
    for line in tree_output.splitlines():
        parts = line.strip().split()
        if parts:
            full_path = parts[-1]
            relative_path = os.path.relpath(full_path, path)
            if not gitignore_spec.match_file(relative_path) and not is_ignored_path(relative_path):
                filtered_lines.append(line.replace('./', '', 1))
    
    return '\n'.join(filtered_lines)

def load_gitignore(path='.'):
    gitignore_path = os.path.join(path, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    return None

def is_ignored_path(file_path: str) -> bool:
    ignored_dirs = ['.git']
    return any(ignored in file_path for ignored in ignored_dirs)

def remove_empty_dirs(tree_output: str) -> str:
    lines = tree_output.splitlines()
    non_empty_dirs = set()
    filtered_lines = []

    for line in reversed(lines):
        if line.strip().endswith('/'):
            if any(line.strip() in dir_line for dir_line in non_empty_dirs):
                filtered_lines.append(line)
        else:
            non_empty_dirs.add(line)
            filtered_lines.append(line)
    
    return '\n'.join(reversed(filtered_lines))

def save_repo_to_text(path='.') -> None:
    gitignore_spec = load_gitignore(path)
    tree_structure = get_tree_structure(path, gitignore_spec)
    tree_structure = remove_empty_dirs(tree_structure)
    
    with open('repo_structure.txt', 'w') as file:
        file.write(tree_structure + '\n')

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
                    file.write('[Could not decode file contents]\n')
                file.write('\n```\n')

def main() -> None:
    save_repo_to_text()

if __name__ == '__main__':
    main()
