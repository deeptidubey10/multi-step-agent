"""Seed sample data for the multi-step agent demo."""

import sqlite3
from datetime import datetime, timedelta
import random


def seed_database(db_path: str = "agent_data.db") -> None:
    """Create and populate sample SQLite database for demo scenario."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create sales table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            product_id INTEGER,
            product_name TEXT,
            region TEXT,
            quarter TEXT,
            revenue REAL,
            target REAL,
            PRIMARY KEY (product_id, region, quarter)
        )
    """)

    # Create product_logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS product_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            log_date TEXT,
            log_message TEXT,
            severity TEXT
        )
    """)

    # Clear existing data
    cursor.execute("DELETE FROM sales")
    cursor.execute("DELETE FROM product_logs")

    # Sample products
    products = [
        (1, "Product A"),
        (2, "Product B"),
        (3, "Product C"),
        (4, "Product D"),
        (5, "Product E"),
        (6, "Product F - FAILING"),
        (7, "Product G - FAILING"),
        (8, "Product H - FAILING"),
        (9, "Product I"),
        (10, "Product J"),
    ]

    regions = ["North", "South", "East", "West"]
    quarters = ["Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026"]

    # Insert sales data - make Q3 2026 North region data for products 6,7,8 to underperform
    for product_id, product_name in products:
        for region in regions:
            for quarter in quarters:
                # Base target is 100,000
                target = 100000

                if region == "North" and quarter == "Q3 2026":
                    if product_id in [6, 7, 8]:
                        # These products are failing - only 30-40% of target
                        revenue = target * random.uniform(0.30, 0.40)
                    else:
                        # Other products doing fine in North Q3
                        revenue = target * random.uniform(0.85, 1.15)
                else:
                    # Other regions/quarters perform normally
                    revenue = target * random.uniform(0.80, 1.10)

                cursor.execute(
                    "INSERT INTO sales VALUES (?, ?, ?, ?, ?, ?)",
                    (product_id, product_name, region, quarter, round(revenue, 2), target),
                )

    # Insert sample logs for the failing products in Q3
    failing_products = [6, 7, 8]
    log_messages = [
        "Supply chain disruption - delayed shipments",
        "Manufacturing defect found in batch 2026-Q3-001",
        "Key customer cancelled order",
        "Pricing mismatch with competitors",
        "Market demand shifted to alternative products",
        "Quality control issues detected",
        "Distribution network problem in North region",
        "Negative customer reviews impacting sales",
    ]

    base_date = datetime(2026, 7, 1)
    for product_id in failing_products:
        for i in range(random.randint(3, 6)):
            log_date = base_date + timedelta(days=random.randint(0, 90))
            severity = random.choice(["WARNING", "ERROR", "CRITICAL"])
            message = random.choice(log_messages)

            cursor.execute(
                "INSERT INTO product_logs (product_id, log_date, log_message, severity) VALUES (?, ?, ?, ?)",
                (product_id, log_date.isoformat(), message, severity),
            )

    conn.commit()
    conn.close()
    print(f"[OK] Database seeded at {db_path}")
    print("  - sales table: 10 products x 4 regions x 4 quarters")
    print("  - product_logs table: 12-18 log entries for failing products")
    print("  - Q3 2026 North region: Products 6, 7, 8 are underperforming (30-40% of target)")


if __name__ == "__main__":
    seed_database("agent_data.db")
