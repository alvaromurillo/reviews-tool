"""
Setup configuration for the reviews-tool package.
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="reviews-tool",
    version="0.1.0",
    author="Alvaro Murillo",
    author_email="dev@alvaromurillo.com",
    description="A Python tool for fetching app reviews from Google Play Store and App Store",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alvaromurillo/reviews-tool",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "reviews-tool=reviews_tool.cli:cli",
        ],
    },
    keywords="app reviews google play store app store scraping api",
    project_urls={
        "Bug Reports": "https://github.com/alvaromurillo/reviews-tool/issues",
        "Source": "https://github.com/alvaromurillo/reviews-tool",
        "Documentation": "https://github.com/alvaromurillo/reviews-tool#readme",
    },
)