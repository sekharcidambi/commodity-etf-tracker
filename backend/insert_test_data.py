#!/usr/bin/env python3
"""
Insert test data for dashboard demonstration
"""

import asyncio
from datetime import datetime, timedelta
import random
from decimal import Decimal

from app.db.database import AsyncSessionLocal
from app.models import ETFPrice, ETFFlow, InstitutionalHolding
from loguru import logger


async def insert_test_price_data():
    """Insert test price data for AGQ and UGL"""
    logger.info("Inserting test price data...")

    async with AsyncSessionLocal() as session:
        # Generate 365 days of price data for AGQ
        start_date = datetime.now() - timedelta(days=365)
        base_price_agq = 30.0
        base_price_ugl = 50.0

        for ticker, base_price in [("AGQ", base_price_agq), ("UGL", base_price_ugl)]:
            logger.info(f"Generating data for {ticker}...")

            for i in range(365):
                date = start_date + timedelta(days=i)

                # Generate realistic price movements
                change = random.uniform(-0.05, 0.05)  # ±5% daily change
                price = base_price * (1 + change)

                open_price = price * random.uniform(0.98, 1.02)
                high_price = max(open_price, price) * random.uniform(1.0, 1.03)
                low_price = min(open_price, price) * random.uniform(0.97, 1.0)
                close_price = price
                volume = random.randint(500000, 5000000)

                price_record = ETFPrice(
                    timestamp=date,
                    ticker=ticker,
                    open=Decimal(str(round(open_price, 2))),
                    high=Decimal(str(round(high_price, 2))),
                    low=Decimal(str(round(low_price, 2))),
                    close=Decimal(str(round(close_price, 2))),
                    volume=volume,
                    adj_close=Decimal(str(round(close_price, 2))),
                    vwap=Decimal(str(round((high_price + low_price + close_price) / 3, 2)))
                )

                session.add(price_record)

                # Update base price for next day
                base_price = close_price

            logger.success(f"Generated 365 days of price data for {ticker}")

        await session.commit()
        logger.success("All price data inserted successfully!")


async def insert_test_flow_data():
    """Insert test flow data"""
    logger.info("Inserting test flow data...")

    async with AsyncSessionLocal() as session:
        # Generate 52 weeks of flow data
        start_date = datetime.now() - timedelta(weeks=52)

        ticker_config = {
            "AGQ": {"base_aum": 500.0},
            "UGL": {"base_aum": 800.0},
            "GDXU": {"base_aum": 350.0}
        }

        for ticker, config in ticker_config.items():
            logger.info(f"Generating flow data for {ticker}...")

            base_aum = config["base_aum"]

            for i in range(52):
                week_ending = (start_date + timedelta(weeks=i)).date()

                # Generate realistic flows (can be positive or negative)
                net_flow = random.uniform(-50, 50)  # in millions
                aum = base_aum + random.uniform(-50, 50)
                shares_outstanding = random.randint(5000000, 20000000)
                premium_discount = random.uniform(-0.02, 0.02)

                flow_record = ETFFlow(
                    week_ending=week_ending,
                    ticker=ticker,
                    net_flow=Decimal(str(round(net_flow, 2))),
                    aum=Decimal(str(round(aum, 2))),
                    shares_outstanding=shares_outstanding,
                    premium_discount=Decimal(str(round(premium_discount, 4))),
                    source="test_data"
                )

                session.add(flow_record)

                base_aum = aum

            logger.success(f"Generated 52 weeks of flow data for {ticker}")

        await session.commit()
        logger.success("All flow data inserted successfully!")


async def insert_test_institutional_data():
    """Insert test institutional holdings"""
    logger.info("Inserting test institutional holdings...")

    institutions = [
        "Vanguard Group Inc",
        "BlackRock Inc",
        "State Street Corp",
        "Fidelity",
        "Morgan Stanley",
        "Goldman Sachs",
        "JPMorgan Chase",
        "Bank of America",
        "Wells Fargo",
        "Citadel Advisors"
    ]

    async with AsyncSessionLocal() as session:
        for ticker in ["AGQ", "UGL"]:
            logger.info(f"Generating institutional holdings for {ticker}...")

            filing_date = (datetime.now() - timedelta(days=45)).date()

            for i, institution in enumerate(institutions):
                shares = random.randint(100000, 2000000)
                value_usd = shares * random.uniform(25, 55)
                percent_of_portfolio = random.uniform(0.001, 0.05)
                change_shares = random.randint(-100000, 100000)
                change_percent = (change_shares / shares) * 100 if shares > 0 else 0

                holding = InstitutionalHolding(
                    filing_date=filing_date,
                    ticker=ticker,
                    institution_name=institution,
                    shares=shares,
                    value_usd=Decimal(str(round(value_usd, 2))),
                    percent_of_portfolio=Decimal(str(round(percent_of_portfolio, 4))),
                    change_shares=change_shares,
                    change_percent=Decimal(str(round(change_percent, 2)))
                )

                session.add(holding)

            logger.success(f"Generated institutional holdings for {ticker}")

        await session.commit()
        logger.success("All institutional holdings inserted successfully!")


async def main():
    """Main function"""
    logger.info("Starting test data insertion...")

    try:
        await insert_test_price_data()
        await insert_test_flow_data()
        await insert_test_institutional_data()

        logger.success("✅ All test data inserted successfully!")
        logger.info("You can now view the dashboard at http://localhost:5173")

    except Exception as e:
        logger.error(f"Error inserting test data: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
