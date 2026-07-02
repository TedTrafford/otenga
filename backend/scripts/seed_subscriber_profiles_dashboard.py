#!/usr/bin/env python3
"""Seed or refresh the Customer Scoring dashboard (queries remote MPESA_DB_*)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.subscriber_profiles_dashboard import ensure_subscriber_profiles_dashboard

if __name__ == "__main__":
    ensure_subscriber_profiles_dashboard(force=True)
