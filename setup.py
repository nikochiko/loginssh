import os
from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="loginssh",
    version="0.1",
    author="Kaustubh Maske Patil",
    author_email="ktvm42@gmail.com",
    description=("A tool to manage SSH connections and their passwords"),
    license="MIT",
    keywords="ssh ssh-manager",
    url="http://packages.python.org/an_example_pypi_project",
    packages=["ssh_manager"],
    include_package_data=True,
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    classifiers=[
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
    ],
    py_modules=["ssh_manager"],
    install_required=["Click", "cryptography"],
    python_requires=">3.8.0",
    entry_points={
        "console_scripts": [
            "loginssh = ssh_manager.ssh_manager:cli"
        ]
    }
)
