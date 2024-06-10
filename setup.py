from setuptools import setup, find_packages

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='repo-to-text',
    version='0.2.2',
    author='Kirill Markin',
    author_email='markinkirill@gmail.com',
    description='Convert a directory structure and its contents into a single text file, including the tree output and file contents in markdown code blocks. It may be useful to chat with LLM about your code.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/kirill-markin/repo-to-text',
    license='MIT',
    packages=find_packages(),
    install_requires=required,
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'repo-to-text=repo_to_text.main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
