#!/usr/bin/env python3
"""Seed or refresh the Rejection Reasons dashboard (queries remote MPESA_DB_*)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rejection_reasons_dashboard import ensure_rejection_reasons_dashboard

if __name__ == "__main__":
    ensure_rejection_reasons_dashboard(force=True)
