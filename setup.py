#! /usr/bin/env python
# -*- coding: utf-8 -*-

import codecs

try:
    from setuptools import setup, find_packages, Command
except ImportError:
    from ez_setup import use_setuptools
    use_setuptools()
    from setuptools import setup, find_packages, Command

long_description = codecs.open("README.rst", "r", "utf-8").read()

setup(
    name="html-tree-diff",
    version="0.1.1",
    description="Structure-aware diff for html and xml documents",
    author="Christian Oudard",
    author_email="christian.oudard@gmail.com",
    url="http://github.com/christian-oudard/htmltreediff/",
    platforms=["any"],
    license="BSD",
    packages=find_packages(),
    scripts=[],
    zip_safe=False,
    install_requires=['html5lib'],
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
