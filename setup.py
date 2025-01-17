from setuptools import setup, find_packages
import sys

CURRENT_PYTHON = sys.version_info[:2]
REQUIRED_PYTHON = (3,8)

if CURRENT_PYTHON < REQUIRED_PYTHON:
    sys.stderr.write(
             """
==========================
Unsupported Python version
==========================
This version of Requests requires at least Python {}.{}, but
you're trying to install it on Python {}.{}. To resolve this,
consider upgrading to a supported Python version.

If you can't upgrade your Python version, you'll need to
pin to an older version of Requests (<2.32.0).
""".format(
            *(REQUIRED_PYTHON + CURRENT_PYTHON)
        )
    )
    sys.exit(1)
    
 
requires = [
    "cryptography",
    "PyQt6",
]

test_requires = [
    "pytest",
]

    
setup(
    name="chate2e",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=requires,
    tests_require=test_requires,
    entry_points={
        "console_scripts": [
            "chate2e = chate2e.main:main",
        ]
    },
)