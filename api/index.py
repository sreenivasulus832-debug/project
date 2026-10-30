"""
api/index.py
Serverless entry point for Vercel deployment.
Exposes the Flask 'app' instance to Vercel's Python runtime.
"""

import sys
import os

# Add root folder to sys.path so app, database, templates, and static are accessible
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app
