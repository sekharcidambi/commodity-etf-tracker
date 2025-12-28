"""
Example usage of the PremiumDiscountCalculatorService

This script demonstrates how to use the premium/discount calculator service
to analyze leveraged precious metals ETFs.
"""

import asyncio
from app.services.premium_discount_calculator import premium_discount_calculator


async def main():
    """Main example function"""

    print("=" * 80)
    print("Premium/Discount Calculator Service - Usage Examples")
    print("=" * 80)

    # Example 1: Calculate current premium/discount for a single ETF
    print("\n1. Calculate current premium/discount for AGQ (2x Silver ETF)")
    print("-" * 80)
    agq_result = await premium_discount_calculator.calculate_premium_discount("AGQ")
    if agq_result:
        print(f"Ticker: {agq_result['ticker']}")
        print(f"ETF Name: {agq_result['etf_name']}")
        print(f"ETF Price: ${agq_result['etf_price']:.2f}")
        print(f"Estimated NAV: ${agq_result['estimated_nav']:.2f}")
        print(f"Premium/Discount: {agq_result['premium_discount_pct']:.2f}%")
        print(f"Underlying: {agq_result['commodity_symbol']} @ ${agq_result['commodity_price']:.2f}")
    else:
        print("Could not calculate premium/discount (insufficient data)")

    # Example 2: Get historical premium/discount data
    print("\n\n2. Get 30-day historical premium/discount for UGL (2x Gold ETF)")
    print("-" * 80)
    ugl_historical = await premium_discount_calculator.get_historical_premium_discount(
        ticker="UGL",
        days=30
    )
    if ugl_historical:
        print(f"Retrieved {len(ugl_historical)} historical records")
        print("\nMost recent 5 records:")
        for i, record in enumerate(ugl_historical[:5], 1):
            print(f"  {i}. {record['date']}: Premium/Discount = {record['premium_discount_pct']:.2f}%")

        # Calculate summary statistics
        prem_disc_values = [r['premium_discount_pct'] for r in ugl_historical]
        avg_prem_disc = sum(prem_disc_values) / len(prem_disc_values)
        max_prem = max(prem_disc_values)
        min_disc = min(prem_disc_values)

        print(f"\nSummary (last 30 days):")
        print(f"  Average Premium/Discount: {avg_prem_disc:.2f}%")
        print(f"  Maximum Premium: {max_prem:.2f}%")
        print(f"  Maximum Discount: {min_disc:.2f}%")
    else:
        print("Could not retrieve historical data")

    # Example 3: Detect extreme premium/discount levels
    print("\n\n3. Detect extreme premium/discount for ZSL (-2x Silver ETF)")
    print("-" * 80)
    zsl_extreme = await premium_discount_calculator.detect_premium_discount_extreme(
        ticker="ZSL",
        threshold=1.5  # 1.5 standard deviations
    )
    if zsl_extreme:
        print("ALERT: Extreme premium/discount detected!")
        print(f"  Direction: {zsl_extreme['direction']}")
        print(f"  Severity: {zsl_extreme['severity']}")
        print(f"  Current Premium/Discount: {zsl_extreme['current_premium_discount_pct']:.2f}%")
        print(f"  Z-Score: {zsl_extreme['z_score']:.2f}")
        print(f"  Percentile: {zsl_extreme['percentile']:.1f}%")
        print(f"  Historical Mean: {zsl_extreme['mean']:.2f}%")
        print(f"  Notes: {zsl_extreme['notes']}")
    else:
        print("No extreme premium/discount detected (within normal range)")

    # Example 4: Get premium/discount for all configured ETFs
    print("\n\n4. Get premium/discount for all configured ETFs")
    print("-" * 80)
    all_results = await premium_discount_calculator.get_all_etf_premium_discounts()
    for result in all_results:
        print(f"{result['ticker']:4s} ({result['etf_name']:30s}): "
              f"Premium/Discount = {result['premium_discount_pct']:+6.2f}%")

    # Example 5: Check all ETFs for extreme levels
    print("\n\n5. Check all ETFs for extreme premium/discount levels")
    print("-" * 80)
    all_extremes = await premium_discount_calculator.check_all_etf_extremes(threshold=1.5)
    if all_extremes:
        print(f"Found {len(all_extremes)} ETF(s) with extreme levels:")
        for extreme in all_extremes:
            print(f"  - {extreme['ticker']}: {extreme['severity']} {extreme['direction']} "
                  f"({extreme['current_premium_discount_pct']:.2f}%, z-score={extreme['z_score']:.2f})")
    else:
        print("No ETFs with extreme premium/discount levels")

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
