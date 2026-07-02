#!/usr/bin/env python3
"""Seed or refresh the Customer Funnel dashboard (queries remote MPESA_DB_*)."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.customer_funnel_dashboard import ensure_customer_funnel_dashboard

if __name__ == "__main__":
    ensure_customer_funnel_dashboard(force=True)
