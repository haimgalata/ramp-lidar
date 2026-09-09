"""Ensures the backend/ directory is on sys.path so `import app...` works
regardless of where pytest is invoked from."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
