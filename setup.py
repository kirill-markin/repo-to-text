from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='repo-to-text',
    version='0.1',
    packages=find_packages(),
    install_requires=required,
    entry_points={
        'console_scripts': [
            'repo-to-text=repo_to_text.main:main',
        ],
    },
)