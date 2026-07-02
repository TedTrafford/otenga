#!/usr/bin/env python3
"""Seed or refresh the Raw M-Pesa Statements dashboard (queries remote MPESA_DB_*)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.raw_mpesa_statements_dashboard import ensure_raw_mpesa_statements_dashboard

if __name__ == "__main__":
    ensure_raw_mpesa_statements_dashboard(force=True)
