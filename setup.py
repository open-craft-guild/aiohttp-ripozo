#! /usr/bin/env python
"""aiohttp_ripozo package setuptools installer."""
from setuptools import setup


params = dict(
    setup_requires=['pbr==3.0.0'],
    pbr=True,
)

if __name__ == '__main__':
    setuptools.setup(**params)
