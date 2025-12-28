"""
Example usage of the COT Collector Service

This demonstrates how to use the CFTC Commitment of Traders data collector
to analyze precious metals positioning.
"""

import asyncio
from datetime import date, timedelta


async def example_usage():
    """Demonstrate COT collector usage"""

    # Import the collector
    from app.services.cot_collector import cot_collector

    print("=" * 80)
    print("CFTC COT Collector - Example Usage")
    print("=" * 80)

    # Example 1: Get current positioning for gold
    print("\n1. Current Gold Positioning:")
    print("-" * 80)
    gold_position = await cot_collector.get_commodity_positioning('gold')
    if gold_position:
        print(f"Report Date: {gold_position['report_date']}")
        print(f"Open Interest: {gold_position['open_interest']:,}")
        print(f"\nManaged Money (Speculators):")
        print(f"  Long: {gold_position['managed_money_long']:,}")
        print(f"  Short: {gold_position['managed_money_short']:,}")
        print(f"  Net: {gold_position['managed_money_net']:,}")
        print(f"  Net % of OI: {gold_position['managed_money_net_pct']:.2f}%")
        print(f"  Long/Short Ratio: {gold_position['managed_money_long_short_ratio']:.2f}")
        print(f"\nCommercial (Hedgers):")
        print(f"  Net: {gold_position['commercial_net']:,}")
        print(f"  Net % of OI: {gold_position['commercial_net_pct']:.2f}%")

    # Example 2: Check for extreme positioning (contrarian indicator)
    print("\n\n2. Extreme Positioning Analysis (Gold):")
    print("-" * 80)
    extremes = await cot_collector.detect_extreme_positioning('gold', lookback_weeks=52)
    if extremes:
        current = extremes['current_positioning']
        extreme = extremes['extreme_positioning']

        print(f"Current Net Position: {current['managed_money_net']:,}")
        print(f"Percentile: {current['percentile']:.1f}th")
        print(f"Z-Score: {current['z_score']:.2f}")
        print(f"\nIs Extreme: {extreme['is_extreme']}")
        if extreme['contrarian_signal']:
            print(f"Contrarian Signal: {extreme['contrarian_signal'].upper()}")
        print(f"\nInterpretation:")
        print(extremes['interpretation'])

    # Example 3: Get all precious metals positioning
    print("\n\n3. All Precious Metals Net Positioning:")
    print("-" * 80)
    all_positions = await cot_collector.calculate_net_positioning()
    for commodity, position in all_positions.items():
        print(f"\n{commodity.upper()}:")
        print(f"  Managed Money Net: {position['managed_money_net']:,} ({position['managed_money_net_pct']:.1f}% of OI)")
        print(f"  Commercial Net: {position['commercial_net']:,} ({position['commercial_net_pct']:.1f}% of OI)")

    # Example 4: Get historical positioning (last 12 weeks)
    print("\n\n4. Historical Silver Positioning (Last 12 Weeks):")
    print("-" * 80)
    history = await cot_collector.get_historical_positioning('silver', weeks=12)
    if history:
        print(f"{'Date':<12} {'MM Net':>12} {'MM Net %':>10} {'Commercial Net':>15}")
        print("-" * 80)
        for record in history:
            print(
                f"{record['report_date']:<12} "
                f"{record['managed_money_net']:>12,} "
                f"{record['managed_money_net_pct']:>10.2f} "
                f"{record['commercial_net']:>15,}"
            )

    # Example 5: Get comprehensive summary for all commodities
    print("\n\n5. Comprehensive Summary (All Precious Metals):")
    print("-" * 80)
    summary = await cot_collector.get_all_commodities_summary()
    for commodity, data in summary['commodities'].items():
        print(f"\n{commodity.upper()}:")
        pos = data['current_positioning']
        print(f"  Report Date: {pos['report_date']}")
        print(f"  Open Interest: {pos['open_interest']:,}")
        print(f"  Managed Money Net: {pos['managed_money_net']:,} ({pos['managed_money_net_pct']:.1f}%)")

        if data['extreme_analysis']:
            ext = data['extreme_analysis']['extreme_positioning']
            if ext['is_extreme']:
                print(f"  ⚠️  EXTREME POSITIONING DETECTED")
                if ext['contrarian_signal']:
                    print(f"  Contrarian Signal: {ext['contrarian_signal'].upper()}")

    # Clean up
    await cot_collector.close()

    print("\n" + "=" * 80)
    print("Example complete!")
    print("=" * 80)


if __name__ == "__main__":
    # Run the async examples
    asyncio.run(example_usage())
