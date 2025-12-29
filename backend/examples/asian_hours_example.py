"""
Example usage of the Asian Hours Analyzer Service

This demonstrates how to detect Korean retail activity patterns
using intraday volume analysis.
"""

import asyncio
from datetime import date
from app.services.asian_hours_analyzer import AsianHoursAnalyzerService


async def main():
    """Demonstrate Asian hours analyzer functionality"""

    # Initialize the service
    analyzer = AsianHoursAnalyzerService()

    ticker = "AGQ"  # 2x Silver ETF popular with Korean retail traders

    print(f"\n{'='*80}")
    print(f"Asian Hours Volume Analysis for {ticker}")
    print(f"{'='*80}\n")

    # Example 1: Get volume breakdown for a specific date
    print("1. Volume Breakdown by Trading Session")
    print("-" * 80)
    target_date = date(2025, 12, 27)
    session_data = await analyzer.get_volume_by_session(ticker, target_date)

    print(f"Date: {session_data['date']}")
    print(f"\nSession Volumes:")
    for session_name, data in session_data['sessions'].items():
        print(f"  {session_name:15s}: {data['volume']:,} (bars: {data['bar_count']})")

    print(f"\nAsian Hours Summary:")
    print(f"  Total Asian Hours Volume:  {session_data['asian_hours_volume']:,}")
    print(f"  Regular Hours Volume:      {session_data['regular_hours_volume']:,}")
    print(f"  Asian Volume Ratio:        {session_data['asian_volume_ratio']:.2%}")

    # Example 2: Analyze 30-day volume patterns
    print(f"\n\n2. 30-Day Asian Hours Volume Trend Analysis")
    print("-" * 80)
    analysis = await analyzer.analyze_asian_hours_volume(ticker, days=30)

    summary = analysis['summary']
    print(f"Analysis Period: {analysis['start_date']} to {analysis['end_date']}")
    print(f"Days with data: {summary['days_with_data']}")
    print(f"\nAsian Volume Ratio Statistics:")
    print(f"  Average:   {summary['avg_asian_volume_ratio']:.2%}")
    print(f"  Median:    {summary['median_asian_volume_ratio']:.2%}")
    print(f"  Std Dev:   {summary['std_asian_volume_ratio']:.2%}")
    print(f"  Min:       {summary['min_asian_volume_ratio']:.2%}")
    print(f"  Max:       {summary['max_asian_volume_ratio']:.2%}")
    print(f"\nTrend: {summary['trend'].upper()}")
    print(f"\nTotal Volumes:")
    print(f"  Asian Hours:   {summary['total_asian_hours_volume']:,}")
    print(f"  Regular Hours: {summary['total_regular_hours_volume']:,}")

    # Example 3: Calculate Korean retail proxy score
    print(f"\n\n3. Korean Retail Activity Proxy Score")
    print("-" * 80)
    proxy = await analyzer.calculate_korean_retail_proxy(ticker)

    print(f"Korean Retail Proxy Score: {proxy['korean_retail_proxy_score']:.1f}/100")
    print(f"Confidence: {proxy['confidence'].upper()}")
    print(f"\nInterpretation: {proxy['interpretation']}")

    print(f"\nSupporting Metrics:")
    metrics = proxy['metrics']
    print(f"  Recent (7d) Asian Ratio:    {metrics['recent_asian_ratio']:.2%}")
    print(f"  Baseline (90d) Asian Ratio: {metrics['baseline_asian_ratio']:.2%}")
    print(f"  Percentile Rank:            {metrics['ratio_percentile']:.1f}%")
    print(f"  Trend:                      {metrics['trend']}")
    print(f"  Consistency Score:          {metrics['consistency_score']:.2f}")

    print(f"\n{'='*80}\n")


if __name__ == "__main__":
    asyncio.run(main())
