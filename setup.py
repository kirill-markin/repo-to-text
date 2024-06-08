from setuptools import setup, find_packages

setup(
    name='repo-to-text',
    version='0.1',
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'repo-to-text=repo_to_text.main:main',
        ],
    },
)
