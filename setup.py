from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="queuectl",
    version="1.0.0",
    description="QueueCTL - CLI-based background job queue system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="QueueCTL Developer",
    author_email="",
    url="https://github.com/yourusername/queuectl",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Distributed Computing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    install_requires=[
        "click>=8.1.0",
        "Flask>=2.3.0",
    ],
    entry_points={
        "console_scripts": [
            "queuectl=queuectl.cli:main",
        ],
    },
    python_requires=">=3.7",
    include_package_data=True,
)

