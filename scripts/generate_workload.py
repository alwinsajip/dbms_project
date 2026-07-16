"""
Workload generator for SEDBMS test scenarios.
Simulates an OLTP + analytics mixed workload with intentional drift.
"""
import argparse
import asyncio
import random
import time
from datetime import datetime

import asyncpg


class WorkloadGenerator:
    def __init__(self, dsn: str, schema_name: str = "public"):
        self.dsn = dsn
        self.schema = schema_name
        self._pool = None
        self._running = False

    async def setup_schema(self):
        await self._pool.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.schema}.orders (
                order_id BIGSERIAL PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                unit_price NUMERIC(10,2) NOT NULL,
                total_amount NUMERIC(12,2) NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                region TEXT NOT NULL DEFAULT 'us-east',
                order_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                shipped_date TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS {self.schema}.customers (
                customer_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                tier TEXT NOT NULL DEFAULT 'standard',
                signup_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_active TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS {self.schema}.products (
                product_id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price NUMERIC(10,2) NOT NULL,
                stock INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
        """)
        await self._seed_data()

    async def _seed_data(self):
        exists = await self._pool.fetchval("SELECT COUNT(*) FROM customers")
        if exists > 0:
            return
        print("[workload] Seeding initial data...")
        for i in range(100):
            await self._pool.execute(
                "INSERT INTO customers (name, email, tier) VALUES ($1, $2, $3)",
                f"Customer_{i}", f"cust{i}@example.com",
                random.choice(["standard", "premium", "enterprise"]),
            )
        for i in range(50):
            await self._pool.execute(
                "INSERT INTO products (name, category, price, stock) VALUES ($1, $2, $3, $4)",
                f"Product_{i}", random.choice(["electronics", "clothing", "food", "books"]),
                round(random.uniform(5, 500), 2), random.randint(0, 1000),
            )
        for i in range(1000):
            await self._insert_order()
        print("[workload] Seed data loaded.")

    async def _insert_order(self):
        cid = random.randint(1, 100)
        pid = random.randint(1, 50)
        qty = random.randint(1, 5)
        price = round(random.uniform(10, 200), 2)
        await self._pool.execute(
            "INSERT INTO orders (customer_id, product_id, quantity, unit_price, total_amount, region) "
            "VALUES ($1, $2, $3, $4, $5, $6)",
            cid, pid, qty, price, round(price * qty, 2),
            random.choice(["us-east", "us-west", "eu-west", "ap-southeast"]),
        )

    async def run_oltp_queries(self, count: int = 20):
        for _ in range(count):
            q = random.choices([
                self._q_order_lookup,
                self._q_customer_orders,
                self._q_product_stock,
                self._q_recent_orders,
                self._q_region_summary,
                self._q_insert_order,
                self._q_update_status,
                self._q_join_customer_order,
            ], weights=[25, 20, 10, 15, 10, 10, 5, 5])[0]
            await q()

    async def _q_order_lookup(self):
        oid = random.randint(1, 50000)
        await self._pool.fetch(f"SELECT * FROM orders WHERE order_id = {oid}")

    async def _q_customer_orders(self):
        cid = random.randint(1, 100)
        await self._pool.fetch(f"SELECT * FROM orders WHERE customer_id = {cid} ORDER BY order_date DESC LIMIT 20")

    async def _q_product_stock(self):
        pid = random.randint(1, 50)
        await self._pool.fetchrow(f"SELECT stock, price FROM products WHERE product_id = {pid}")

    async def _q_recent_orders(self):
        await self._pool.fetch("SELECT * FROM orders WHERE order_date > NOW() - INTERVAL '1 hour' ORDER BY order_date DESC LIMIT 50")

    async def _q_region_summary(self):
        await self._pool.fetch("SELECT region, COUNT(*), SUM(total_amount) FROM orders GROUP BY region")

    async def _q_insert_order(self):
        await self._insert_order()

    async def _q_update_status(self):
        oid = random.randint(1, min(50000, 100))
        await self._pool.execute(f"UPDATE orders SET status = 'shipped', shipped_date = NOW() WHERE order_id = {oid}")

    async def _q_join_customer_order(self):
        await self._pool.fetch("""
            SELECT c.name, o.order_id, o.total_amount, o.order_date
            FROM customers c JOIN orders o ON c.customer_id = o.customer_id
            WHERE o.total_amount > 100
            ORDER BY o.order_date DESC LIMIT 20
        """)

    async def start_loop(self, duration_minutes: float = 10, drift_after_minutes: float = 2, opm: int = 60):
        print(f"[workload] Starting for {duration_minutes}min, drift at t={drift_after_minutes}min, ~{opm} ops/min")
        self._running = True
        start = time.time()
        drift_started = False
        drift_active = False
        interval = 60.0 / opm

        while self._running:
            elapsed = (time.time() - start) / 60.0
            if elapsed > duration_minutes:
                break

            if elapsed > drift_after_minutes and not drift_started:
                drift_started = True
                print("[workload] *** DRIFT: shifting query pattern to region-based filter ***")

            if drift_started and not drift_active:
                for _ in range(10):
                    await self._pool.execute(
                        "INSERT INTO orders (customer_id, product_id, quantity, unit_price, total_amount, region) "
                        "VALUES ($1, $2, $3, $4, $5, $6)",
                        random.randint(1, 100), random.randint(1, 50),
                        random.randint(1, 5), round(random.uniform(10, 200), 2),
                        round(random.uniform(10, 1000), 2), "ap-southeast",
                    )
                drift_active = True
                print("[workload] Drift data inserted - queries will now target ap-southeast region")

            if drift_active:
                for _ in range(5):
                    region = random.choices(
                        ["ap-southeast", "us-east", "us-west", "eu-west"],
                        weights=[70, 10, 10, 10]
                    )[0]
                    await self._pool.fetch(
                        "SELECT * FROM orders WHERE region = $1 AND order_date > NOW() - INTERVAL '1 day' ORDER BY order_date DESC LIMIT 50",
                        region,
                    )

            await self.run_oltp_queries(random.randint(5, 15))
            await asyncio.sleep(interval)

    async def stop(self):
        self._running = False
        if self._pool:
            await self._pool.close()

    async def __aenter__(self):
        self._pool = await asyncpg.create_pool(self.dsn, min_size=2, max_size=5)
        return self

    async def __aexit__(self, *args):
        await self.stop()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dsn", default="postgresql://postgres@localhost:5542/sedbms_prod")
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--drift-after", type=float, default=2.0)
    parser.add_argument("--opm", type=int, default=60)
    args = parser.parse_args()

    async with WorkloadGenerator(args.dsn) as wg:
        await wg.setup_schema()
        await wg.start_loop(
            duration_minutes=args.duration,
            drift_after_minutes=args.drift_after,
            opm=args.opm,
        )


if __name__ == "__main__":
    asyncio.run(main())
