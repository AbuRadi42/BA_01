"""
conftest.py — shared fixtures and runner for the morph_efficiency_project test suite.

Usage (from workspace root):
    python -m pytest morph_efficiency_project/tests/ -v
    python -m pytest morph_efficiency_project/tests/ar/ -v
"""
import sys
import os

# Ensure workspace root is on sys.path so imports work from any working directory.
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
