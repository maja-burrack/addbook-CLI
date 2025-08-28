from setuptools import setup
from addbook import __version__

setup(
    name="addbook",
    version=__version__,
    py_modules=["addbook"],
    install_requires=[
        "requests",
        "python-dotenv",
        "pyzotero",
    ],
    entry_points={
        "console_scripts": [
            "addbook=addbook:main",
        ],
    },
)
