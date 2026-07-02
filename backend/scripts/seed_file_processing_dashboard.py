#!/usr/bin/env python3
"""Seed or refresh the File Processing dashboard (queries remote MPESA_DB_*)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.file_processing_dashboard import ensure_file_processing_dashboard

if __name__ == "__main__":
    ensure_file_processing_dashboard(force=True)
