import os
from setuptools import setup, find_packages

setup(
    name="autotasktracker",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "streamlit",
        "pandas",
        "plotly",
        "memos",
        "sentence-transformers",
        "click>=8.0",
        "requests",
    ],
    entry_points={
        'console_scripts': [
            'autotask=autotasktracker.cli.main:cli',
        ],
    },
    python_requires='>=3.8',
    author="AutoTaskTracker Team",
    description="AI-powered passive task discovery from screenshots",
    long_description=open('README.md').read() if os.path.exists('README.md') else '',
    long_description_content_type="text/markdown",
)