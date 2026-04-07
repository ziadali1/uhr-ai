"""pytest configuration — adds backend directory to sys.path for imports."""
import sys
import os

# Allow importing modules directly (e.g., `from services.rag.context_block import ...`)
sys.path.insert(0, os.path.dirname(__file__))
