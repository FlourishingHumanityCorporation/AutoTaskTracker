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
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
    ],
)