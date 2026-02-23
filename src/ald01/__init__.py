"""
ALD-01: Advanced Local Desktop Intelligence
Your Personal AI Agent — Open-source, privacy-first, fully local.

Built with Python for maximum stability and zero build errors.
"""

__version__ = "1.0.0"
__author__ = "Aditya Shenvi"
__project__ = "ALD-01"
__description__ = "Advanced Local Desktop Intelligence — Your Personal AI Agent"

import os
import sys

# Ensure the package directory is in the path
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(PACKAGE_DIR))

# Default configuration directory
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".ald01")
DATA_DIR = os.path.join(CONFIG_DIR, "data")
LOGS_DIR = os.path.join(CONFIG_DIR, "logs")
MEMORY_DIR = os.path.join(CONFIG_DIR, "memory")

# Create directories on import
for d in [CONFIG_DIR, DATA_DIR, LOGS_DIR, MEMORY_DIR]:
    os.makedirs(d, exist_ok=True)
