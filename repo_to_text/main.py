import os
import subprocess

def get_tree_structure(path='.') -> str:
    result = subprocess.run(['tree', path], stdout=subprocess.PIPE)
    return result.stdout.decode('utf-8')

def save_repo_to_text(path='.') -> None:
    tree_structure: str = get_tree_structure(path)
    with open('repo_structure.txt', 'w') as file:
        file.write(tree_structure + '\n')

        for root, _, files in os.walk(path):
            for filename in files:
                file_path: str = os.path.join(root, filename)
                relative_path: str = os.path.relpath(file_path, path)
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