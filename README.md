# repo-to-text

`repo-to-text` is an open-source project that converts the structure and contents of a directory (repository) into a single text file. By executing a simple command in the terminal, this tool generates a text representation of the directory, including the output of the `tree` command and the contents of each file, formatted for easy reading and sharing.

## Features

- Generates a text representation of a directory's structure.
- Includes the output of the `tree` command.
- Saves the contents of each file, encapsulated in markdown code blocks.
- Easy to install and use via `pip` and Homebrew.

## Installation

### Using pip

To install `repo-to-text` via pip, run the following command:

```bash
pip install git+https://github.com/yourusername/repo-to-text.git
```

### Using Homebrew

To install `repo-to-text` via Homebrew, run the following command:

```bash
brew install yourusername/repo-to-text
```

### Install Locally

To install `repo-to-text` locally for development, follow these steps:

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/repo-to-text.git
   cd repo-to-text
   ```

2. Install the package locally:
   ```bash
   pip install -e .
   ```

## Usage

After installation, you can use the `repo-to-text` command in your terminal. Navigate to the directory you want to convert and run:

```bash
repo-to-text
```

This will create a file named `repo_structure.txt` in the current directory with the text representation of the repository.

## Enabling Debug Logging

By default, repo-to-text runs with INFO logging level. To enable DEBUG logging, use the --debug flag:

```bash
repo-to-text --debug
```

## Example Output

The generated text file will include the directory structure and contents of each file. For example:

```
.
├── README.md
├── repo_to_text
│   ├── __init__.py
│   └── main.py
├── requirements.txt
├── setup.py
└── tests
    ├── __init__.py
    └── test_main.py

README.md
```
```
# Contents of README.md
...
```
```
# Contents of repo_to_text/__init__.py
...
```
...

## Running Tests

To run the tests, use the following command:

```bash
pytest
```

Make sure you have `pytest` installed. If not, you can install it using:

```bash
pip install pytest
```

## Uninstall Locally

To uninstall the locally installed package, run the following command from the directory where the repository is located:

```bash
pip uninstall repo-to-text
```

## Contributing

Contributions are welcome! If you have any suggestions or find a bug, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For any inquiries or feedback, please contact [yourname](mailto:youremail@example.com).
