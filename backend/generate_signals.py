#!/usr/bin/env python3
"""
Signal Generation Script
Run this script to generate trading signals for AGQ and UGL
"""

import asyncio
from loguru import logger
from app.services.signal_generator import SignalGeneratorService
from app.services.data_storage import data_storage


async def generate_signals_for_ticker(ticker: str):
    """Generate and save signals for a ticker"""
    logger.info(f"Generating signals for {ticker}...")

    signal_gen = SignalGeneratorService()

    # Generate signals
    signals = await signal_gen.generate_signals(ticker)

    if not signals:
        logger.warning(f"No signals generated for {ticker}")
        return 0

    # Save signals to database
    saved_count = 0
    for signal in signals:
        try:
            signal_id = await data_storage.save_signal(signal)
            logger.success(f"Saved signal {signal_id}: {signal['signal_type']} - {signal['direction']} (strength: {signal['strength']})")
            saved_count += 1
        except Exception as e:
            logger.error(f"Failed to save signal: {e}")

    return saved_count


async def main():
    """Main function to generate signals for all tickers"""
    logger.info("Starting signal generation for all tickers...")

    tickers = ['AGQ', 'UGL']
    total_signals = 0

    for ticker in tickers:
        count = await generate_signals_for_ticker(ticker)
        total_signals += count
        logger.info(f"Generated {count} signals for {ticker}")

    logger.success(f"Total signals generated: {total_signals}")


if __name__ == "__main__":
    asyncio.run(main())
