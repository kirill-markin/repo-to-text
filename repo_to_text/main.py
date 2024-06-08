import os
import subprocess
import pathspec

def get_tree_structure(path='.', gitignore_spec=None) -> str:
    # Run the tree command and get its output
    result = subprocess.run(['tree', path], stdout=subprocess.PIPE)
    tree_output = result.stdout.decode('utf-8')

    if not gitignore_spec:
        return tree_output

    # Filter the tree output to exclude files in .gitignore (excluding .gitignore itself)
    filtered_lines = []
    for line in tree_output.splitlines():
        parts = line.split()
        if not any(gitignore_spec.match_file(os.path.join(path, part)) for part in parts if part != '.gitignore'):
            filtered_lines.append(line)
    return '\n'.join(filtered_lines)

def load_gitignore(path='.'):
    gitignore_path = os.path.join(path, '.gitignore')
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            return pathspec.PathSpec.from_lines('gitwildmatch', f)
    return None

def is_ignored_file(file_path: str) -> bool:
    # Check if the file is part of .git or should be ignored according to .gitignore rules
    return '.git' in file_path.split(os.sep) or file_path.endswith('.gitignore')

def save_repo_to_text(path='.') -> None:
    gitignore_spec = load_gitignore(path)
    tree_structure: str = get_tree_structure(path, gitignore_spec)
    with open('repo_structure.txt', 'w') as file:
        file.write(tree_structure + '\n')

        for root, _, files in os.walk(path):
            for filename in files:
                file_path: str = os.path.join(root, filename)
                relative_path: str = os.path.relpath(file_path, path)
                
                # Check if the file should be ignored
                if is_ignored_file(file_path) or (gitignore_spec and gitignore_spec.match_file(file_path)):
                    continue
                
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
