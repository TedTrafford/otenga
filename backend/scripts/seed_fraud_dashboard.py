#!/usr/bin/env python3
"""Seed or refresh the Fraud Rules dashboard (queries remote MPESA_DB_*)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.fraud_dashboard import ensure_fraud_dashboard

if __name__ == "__main__":
    ensure_fraud_dashboard(force=True)
