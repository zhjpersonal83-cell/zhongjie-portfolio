#!/usr/bin/env python3
"""Convenience entry point: python3 build.py [--base-url URL]."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).resolve().parent / 'scripts/build.py'), run_name='__main__')
