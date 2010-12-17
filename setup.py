#! /usr/bin/env python
# -*- coding: utf-8 -*-

import codecs

try:
    from setuptools import setup, find_packages, Command
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages, Command

import htmltreediff

long_description = codecs.open("README.rst", "r", "utf-8").read()

setup(
    name="html-tree-diff",
    version=htmltreediff.__version__,
    description=htmltreediff.__doc__,
    author=htmltreediff.__author__,
    author_email=htmltreediff.__contact__,
    url=htmltreediff.__homepage__,
    platforms=["any"],
    license="BSD",
    packages=find_packages(),
    scripts=[],
    zip_safe=False,
    install_requires=[],
    cmdclass={},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Text Processing :: Markup :: HTML",
        "Topic :: Text Processing :: Markup :: XML",
    ],
    long_description=long_description,
)
