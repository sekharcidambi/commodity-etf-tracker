"""Composite signal scorer service combining multiple data signals into actionable scores"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from loguru import logger

from app.services.flow_statistics import FlowStatisticsService
from app.services.premium_discount_calculator import premium_discount_calculator
from app.services.cot_collector import cot_collector
from app.services.google_trends_collector import google_trends_collector
from app.services.asian_hours_analyzer import AsianHoursAnalyzerService
from app.services.signal_generator import SignalGeneratorService
from app.services.data_storage import DataStorageService
from app.services.reddit_sentiment_collector import reddit_sentiment_collector
from app.core.config import settings


class CompositeSignalScorer:
    """
    Combine multiple signal factors into a single actionable score for each ticker.

    Score ranges from -100 (Strong SELL) to +100 (Strong BUY):
    - > +60: Strong BUY
    - +30 to +60: Moderate BUY
    - -30 to +30: NEUTRAL
    - -60 to -30: Moderate SELL
    - < -60: Strong SELL
    """

    # Factor weights (must sum to 100%)
    FACTOR_WEIGHTS = {
        'flow_momentum': 0.20,           # 20% - Flow momentum (z-score)
        'korean_retail': 0.15,           # 15% - Korean retail contrarian
        'institutional': 0.15,           # 15% - Institutional accumulation
        'futures_basis': 0.10,           # 10% - Futures basis
        'cot_positioning': 0.15,         # 15% - COT positioning (contrarian)
        'premium_discount': 0.10,        # 10% - Premium/discount
        'google_trends': 0.10,           # 10% - Google Trends sentiment
        'reddit_sentiment': 0.05,        # 5% - Reddit sentiment
    }

    # Commodity mapping for tickers
    COMMODITY_MAPPING = {
        'AGQ': {'commodity': 'silver', 'futures_symbol': 'SI=F'},
        'UGL': {'commodity': 'gold', 'futures_symbol': 'GC=F'},
        'ZSL': {'commodity': 'silver', 'futures_symbol': 'SI=F'},
    }

    def __init__(self):
        """Initialize the composite signal scorer with required services"""
        self.flow_stats = FlowStatisticsService()
        self.asian_hours = AsianHoursAnalyzerService()
        self.signal_gen = SignalGeneratorService()
        self.data_storage = DataStorageService()

        # Verify weights sum to 1.0
        total_weight = sum(self.FACTOR_WEIGHTS.values())
        if abs(total_weight - 1.0) > 0.001:
            logger.warning(
                f"Factor weights sum to {total_weight:.3f}, not 1.0. "
                "Scores may be skewed."
            )

    async def calculate_composite_score(self, ticker: str) -> Dict[str, Any]:
        """
        Calculate composite score combining all available factors

        Args:
            ticker: ETF ticker symbol (AGQ, UGL, ZSL)

        Returns:
            Dictionary with composite score, factor breakdown, and metadata:
            {
                'ticker': 'AGQ',
                'composite_score': 45.5,  # -100 to +100
                'recommendation': 'Moderate BUY',
                'confidence': 'high',  # high, medium, low
                'factor_scores': {...},  # Individual normalized scores
                'factor_contributions': {...},  # Weighted contributions
                'factors_available': 7,  # Number of factors with data
                'factors_total': 8,
                'calculated_at': '2025-12-28T...'
            }
        """
        try:
            logger.info(f"Calculating composite score for {ticker}")

            # Get all factor scores
            factor_scores = await self._get_all_factor_scores(ticker)

            # Calculate weighted composite score
            composite_score = 0.0
            factor_contributions = {}
            factors_available = 0
            total_weight_available = 0.0

            for factor_name, factor_weight in self.FACTOR_WEIGHTS.items():
                factor_data = factor_scores.get(factor_name, {})
                normalized_score = factor_data.get('normalized_score')

                if normalized_score is not None:
                    # Score is normalized to -1 to +1, convert to contribution
                    contribution = normalized_score * factor_weight * 100
                    composite_score += contribution
                    factor_contributions[factor_name] = round(contribution, 2)
                    factors_available += 1
                    total_weight_available += factor_weight
                else:
                    factor_contributions[factor_name] = None

            # Adjust for missing factors by rescaling
            if total_weight_available > 0 and total_weight_available < 1.0:
                scaling_factor = 1.0 / total_weight_available
                composite_score *= scaling_factor
                logger.info(
                    f"Rescaled score by {scaling_factor:.2f} due to missing factors "
                    f"({factors_available}/{len(self.FACTOR_WEIGHTS)} available)"
                )

            # Determine confidence based on data availability
            confidence = self._calculate_confidence(factors_available, len(self.FACTOR_WEIGHTS))

            # Get recommendation
            recommendation = self._get_recommendation(composite_score)

            result = {
                'ticker': ticker,
                'composite_score': round(composite_score, 2),
                'recommendation': recommendation,
                'confidence': confidence,
                'factor_scores': factor_scores,
                'factor_contributions': factor_contributions,
                'factors_available': factors_available,
                'factors_total': len(self.FACTOR_WEIGHTS),
                'calculated_at': datetime.utcnow().isoformat()
            }

            logger.success(
                f"{ticker}: Composite score = {composite_score:.2f} ({recommendation}) "
                f"[{factors_available}/{len(self.FACTOR_WEIGHTS)} factors, {confidence} confidence]"
            )

            return result

        except Exception as e:
            logger.error(f"Error calculating composite score for {ticker}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._empty_score_response(ticker)

    async def get_factor_breakdown(self, ticker: str) -> Dict[str, Any]:
        """
        Get detailed breakdown of individual factor scores

        Args:
            ticker: ETF ticker symbol

        Returns:
            Dictionary with detailed factor information
        """
        try:
            factor_scores = await self._get_all_factor_scores(ticker)

            breakdown = {
                'ticker': ticker,
                'factors': {},
                'calculated_at': datetime.utcnow().isoformat()
            }

            for factor_name, factor_data in factor_scores.items():
                weight = self.FACTOR_WEIGHTS[factor_name]

                breakdown['factors'][factor_name] = {
                    'weight': weight,
                    'normalized_score': factor_data.get('normalized_score'),
                    'raw_value': factor_data.get('raw_value'),
                    'available': factor_data.get('normalized_score') is not None,
                    'interpretation': factor_data.get('interpretation'),
                    'metadata': factor_data.get('metadata', {})
                }

            return breakdown

        except Exception as e:
            logger.error(f"Error getting factor breakdown for {ticker}: {e}")
            return {'ticker': ticker, 'factors': {}, 'error': str(e)}

    async def get_all_ticker_scores(self) -> List[Dict[str, Any]]:
        """
        Calculate composite scores for all primary tickers

        Returns:
            List of composite score dictionaries for each ticker
        """
        tickers = settings.PRIMARY_TICKERS
        logger.info(f"Calculating composite scores for {len(tickers)} tickers: {tickers}")

        results = []

        for ticker in tickers:
            try:
                score = await self.calculate_composite_score(ticker)
                results.append(score)
            except Exception as e:
                logger.error(f"Error calculating score for {ticker}: {e}")
                results.append(self._empty_score_response(ticker))

        # Sort by absolute score (strongest signals first)
        results.sort(key=lambda x: abs(x.get('composite_score', 0)), reverse=True)

        return results

    async def get_signal_recommendation(self, ticker: str) -> Dict[str, Any]:
        """
        Get human-readable recommendation with rationale

        Args:
            ticker: ETF ticker symbol

        Returns:
            Dictionary with recommendation and supporting rationale
        """
        try:
            score_data = await self.calculate_composite_score(ticker)

            composite_score = score_data['composite_score']
            recommendation = score_data['recommendation']
            confidence = score_data['confidence']

            # Build rationale from top contributing factors
            contributions = score_data.get('factor_contributions', {})

            # Get factors sorted by absolute contribution
            sorted_factors = sorted(
                [(k, v) for k, v in contributions.items() if v is not None],
                key=lambda x: abs(x[1]),
                reverse=True
            )

            # Top 3 factors
            top_factors = sorted_factors[:3]

            rationale_parts = []
            for factor_name, contribution in top_factors:
                factor_data = score_data['factor_scores'].get(factor_name, {})
                interpretation = factor_data.get('interpretation', '')

                direction = "bullish" if contribution > 0 else "bearish"
                rationale_parts.append(
                    f"{factor_name.replace('_', ' ').title()}: {interpretation} "
                    f"({direction}, {abs(contribution):.1f} pts)"
                )

            rationale = "; ".join(rationale_parts) if rationale_parts else "Insufficient data"

            return {
                'ticker': ticker,
                'recommendation': recommendation,
                'composite_score': composite_score,
                'confidence': confidence,
                'rationale': rationale,
                'top_factors': [
                    {
                        'name': factor_name,
                        'contribution': contribution,
                        'interpretation': score_data['factor_scores'].get(factor_name, {}).get('interpretation')
                    }
                    for factor_name, contribution in top_factors
                ],
                'timestamp': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting recommendation for {ticker}: {e}")
            return {
                'ticker': ticker,
                'recommendation': 'ERROR',
                'error': str(e)
            }

    async def get_confidence_level(self, ticker: str) -> Dict[str, Any]:
        """
        Get confidence level based on data availability

        Args:
            ticker: ETF ticker symbol

        Returns:
            Dictionary with confidence metrics
        """
        try:
            factor_scores = await self._get_all_factor_scores(ticker)

            available_factors = sum(
                1 for f in factor_scores.values()
                if f.get('normalized_score') is not None
            )
            total_factors = len(self.FACTOR_WEIGHTS)

            availability_pct = (available_factors / total_factors) * 100
            confidence = self._calculate_confidence(available_factors, total_factors)

            # Check data freshness
            data_freshness = self._assess_data_freshness(factor_scores)

            return {
                'ticker': ticker,
                'confidence': confidence,
                'available_factors': available_factors,
                'total_factors': total_factors,
                'availability_pct': round(availability_pct, 1),
                'data_freshness': data_freshness,
                'factors_status': {
                    factor_name: {
                        'available': factor_data.get('normalized_score') is not None,
                        'last_updated': factor_data.get('metadata', {}).get('timestamp')
                    }
                    for factor_name, factor_data in factor_scores.items()
                },
                'calculated_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error calculating confidence for {ticker}: {e}")
            return {
                'ticker': ticker,
                'confidence': 'low',
                'error': str(e)
            }

    # ========== INTERNAL METHODS ==========

    async def _get_all_factor_scores(self, ticker: str) -> Dict[str, Dict[str, Any]]:
        """
        Get all individual factor scores normalized to -1 to +1

        Returns:
            Dictionary mapping factor names to score data
        """
        scores = {}

        # 1. Flow momentum (z-score)
        scores['flow_momentum'] = await self._get_flow_momentum_score(ticker)

        # 2. Korean retail contrarian
        scores['korean_retail'] = await self._get_korean_retail_score(ticker)

        # 3. Institutional accumulation
        scores['institutional'] = await self._get_institutional_score(ticker)

        # 4. Futures basis
        scores['futures_basis'] = await self._get_futures_basis_score(ticker)

        # 5. COT positioning (contrarian)
        scores['cot_positioning'] = await self._get_cot_score(ticker)

        # 6. Premium/discount
        scores['premium_discount'] = await self._get_premium_discount_score(ticker)

        # 7. Google Trends sentiment
        scores['google_trends'] = await self._get_google_trends_score(ticker)

        # 8. Reddit sentiment
        scores['reddit_sentiment'] = await self._get_reddit_sentiment_score(ticker)

        return scores

    async def _get_flow_momentum_score(self, ticker: str) -> Dict[str, Any]:
        """
        Flow momentum score based on z-score
        Normalized: z-score / 3 (clamped to -1, +1)
        """
        try:
            stats = await self.flow_stats.calculate_flow_statistics(ticker, "13w")

            if not stats or stats.get('z_score') is None:
                return {'normalized_score': None, 'raw_value': None}

            z_score = stats['z_score']

            # Normalize: z-score of ±3 = ±1.0
            normalized = np.clip(z_score / 3.0, -1.0, 1.0)

            interpretation = f"Z-score: {z_score:.2f}"
            if z_score > 2.0:
                interpretation += " (Very strong inflows)"
            elif z_score > 1.0:
                interpretation += " (Strong inflows)"
            elif z_score < -2.0:
                interpretation += " (Very strong outflows)"
            elif z_score < -1.0:
                interpretation += " (Strong outflows)"
            else:
                interpretation += " (Neutral flows)"

            return {
                'normalized_score': float(normalized),
                'raw_value': float(z_score),
                'interpretation': interpretation,
                'metadata': {
                    'window': '13w',
                    'percentile': stats.get('percentile'),
                    'timestamp': datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error calculating flow momentum for {ticker}: {e}")
            return {'normalized_score': None, 'raw_value': None}

    async def _get_korean_retail_score(self, ticker: str) -> Dict[str, Any]:
        """
        Korean retail contrarian score
        High retail activity = negative signal (contrarian)
        Normalized: -proxy_score / 100
        """
        try:
            proxy = await self.asian_hours.calculate_korean_retail_proxy(ticker)

            if not proxy or proxy.get('korean_retail_proxy_score') is None:
                return {'normalized_score': None, 'raw_value': None}

            score = proxy['korean_retail_proxy_score']

            # Contrarian: high score = sell signal = negative
            # Normalize to -1 to +1 (inverted)
            normalized = -np.clip(score / 100.0, -1.0, 1.0)

            interpretation = proxy.get('interpretation', '')

            return {
                'normalized_score': float(normalized),
                'raw_value': float(score),
                'interpretation': f"Contrarian: {interpretation}",
                'metadata': {
                    'confidence': proxy.get('confidence'),
                    'trend': proxy.get('metrics', {}).get('trend'),
                    'timestamp': datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error calculating Korean retail score for {ticker}: {e}")
            return {'normalized_score': None, 'raw_value': None}

    async def _get_institutional_score(self, ticker: str) -> Dict[str, Any]:
        """
        Institutional accumulation score
        Based on quarters of accumulation
        Normalized: quarters / 3 (clamped to -1, +1)
        """
        try:
            # Get institutional holdings
            holdings = await self.data_storage.get_institutional_holdings(ticker, limit=100)

            if not holdings:
                return {'normalized_score': None, 'raw_value': None}

            # Group by quarter
            quarterly_changes = {}
            for h in holdings:
                filing_date = h['filing_date']
                change_shares = h['change_shares']

                if filing_date not in quarterly_changes:
                    quarterly_changes[filing_date] = 0
                if change_shares:
                    quarterly_changes[filing_date] += change_shares

            # Get last 3 quarters
            sorted_quarters = sorted(quarterly_changes.keys(), reverse=True)[:3]

            if len(sorted_quarters) < 2:
                return {'normalized_score': None, 'raw_value': None}

            # Count accumulation vs distribution quarters
            accumulation_quarters = sum(1 for q in sorted_quarters if quarterly_changes[q] > 0)
            distribution_quarters = sum(1 for q in sorted_quarters if quarterly_changes[q] < 0)

            # Net quarters: +3 (all accumulation) to -3 (all distribution)
            net_quarters = accumulation_quarters - distribution_quarters

            # Normalize to -1 to +1
            normalized = np.clip(net_quarters / 3.0, -1.0, 1.0)

            interpretation = f"{accumulation_quarters}/{len(sorted_quarters)} quarters accumulating"

            return {
                'normalized_score': float(normalized),
                'raw_value': accumulation_quarters,
                'interpretation': interpretation,
                'metadata': {
                    'accumulation_quarters': accumulation_quarters,
                    'distribution_quarters': distribution_quarters,
                    'total_quarters': len(sorted_quarters),
                    'timestamp': datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error calculating institutional score for {ticker}: {e}")
            return {'normalized_score': None, 'raw_value': None}

    async def _get_futures_basis_score(self, ticker: str) -> Dict[str, Any]:
        """
        Futures basis score
        Contango = negative (unfavorable for long ETFs)
        Backwardation = positive (favorable for long ETFs)
        Normalized: basis_pct / 5.0 (clamped)
        """
        try:
            if ticker not in self.COMMODITY_MAPPING:
                return {'normalized_score': None, 'raw_value': None}

            futures_symbol = self.COMMODITY_MAPPING[ticker]['futures_symbol']

            # Get futures price
            futures_prices = await self.data_storage.get_commodity_price_data(
                futures_symbol, limit=1
            )

            if not futures_prices:
                return {'normalized_score': None, 'raw_value': None}

            futures_price = float(futures_prices[0]['close'])

            # Get ETF price as spot proxy
            etf_prices = await self.data_storage.get_price_data(ticker, limit=1)

            if not etf_prices:
                return {'normalized_score': None, 'raw_value': None}

            etf_price = float(etf_prices[0]['close'])

            # Estimate spot from ETF price
            leverage = 2.0 if ticker in ['AGQ', 'UGL'] else -2.0
            estimated_spot = etf_price / abs(leverage)

            # Calculate basis percentage
            basis_pct = (futures_price - estimated_spot) / estimated_spot * 100

            # Normalize (inverted): contango = negative
            # ±5% basis = ±1.0
            normalized = -np.clip(basis_pct / 5.0, -1.0, 1.0)

            # Adjust for inverse ETFs
            if ticker == 'ZSL':
                normalized = -normalized

            interpretation = f"Basis: {basis_pct:.2f}%"
            if basis_pct > 2.0:
                interpretation += " (Strong contango - unfavorable)"
            elif basis_pct < -1.0:
                interpretation += " (Backwardation - favorable)"
            else:
                interpretation += " (Neutral)"

            return {
                'normalized_score': float(normalized),
                'raw_value': float(basis_pct),
                'interpretation': interpretation,
                'metadata': {
                    'futures_price': futures_price,
                    'estimated_spot': float(estimated_spot),
                    'timestamp': datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error calculating futures basis score for {ticker}: {e}")
            return {'normalized_score': None, 'raw_value': None}

    async def _get_cot_score(self, ticker: str) -> Dict[str, Any]:
        """
        COT positioning score (contrarian)
        Extreme bullish positioning = negative signal
        Extreme bearish positioning = positive signal
        Normalized: -z_score / 3 (inverted, clamped)
        """
        try:
            if ticker not in self.COMMODITY_MAPPING:
                return {'normalized_score': None, 'raw_value': None}

            commodity = self.COMMODITY_MAPPING[ticker]['commodity']

            extreme_data = await cot_collector.detect_extreme_positioning(
                commodity=commodity,
                lookback_weeks=52,
                percentile_threshold=90.0
            )

            if not extreme_data:
                return {'normalized_score': None, 'raw_value': None}

            current_pos = extreme_data.get('current_positioning', {})
            z_score = current_pos.get('z_score', 0)
            percentile = current_pos.get('percentile', 50)

            # Contrarian: positive z-score (bullish positioning) = negative signal
            # Normalize: ±3 z-score = ±1.0 (inverted)
            normalized = -np.clip(z_score / 3.0, -1.0, 1.0)

            # Adjust for inverse ETFs
            if ticker == 'ZSL':
                normalized = -normalized

            interpretation = f"Managed Money at {percentile:.0f}th percentile"

            extreme_pos = extreme_data.get('extreme_positioning', {})
            if extreme_pos.get('is_extreme_bullish'):
                interpretation += " (Extreme bullish - contrarian SELL)"
            elif extreme_pos.get('is_extreme_bearish'):
                interpretation += " (Extreme bearish - contrarian BUY)"

            return {
                'normalized_score': float(normalized),
                'raw_value': float(z_score),
                'interpretation': interpretation,
                'metadata': {
                    'percentile': percentile,
                    'managed_money_net': current_pos.get('managed_money_net'),
                    'contrarian_signal': extreme_pos.get('contrarian_signal'),
                    'timestamp': extreme_data.get('report_date')
                }
            }

        except Exception as e:
            logger.error(f"Error calculating COT score for {ticker}: {e}")
            return {'normalized_score': None, 'raw_value': None}

    async def _get_premium_discount_score(self, ticker: str) -> Dict[str, Any]:
        """
        Premium/discount score
        Premium = negative (overpriced, sell)
        Discount = positive (underpriced, buy)
        Normalized: -z_score / 3 (inverted, clamped)
        """
        try:
            extreme = await premium_discount_calculator.detect_premium_discount_extreme(
                ticker, threshold=1.0
            )

            if not extreme:
                # Not extreme, but still calculate current P/D
                current = await premium_discount_calculator.calculate_premium_discount(ticker)

                if not current:
                    return {'normalized_score': None, 'raw_value': None}

                # Use P/D percentage directly (small values)
                pd_pct = current['premium_discount_pct']

                # Normalize: ±3% P/D = ±1.0 (inverted)
                normalized = -np.clip(pd_pct / 3.0, -1.0, 1.0)

                interpretation = f"P/D: {pd_pct:.2f}% (Normal range)"

                return {
                    'normalized_score': float(normalized),
                    'raw_value': float(pd_pct),
                    'interpretation': interpretation,
                    'metadata': {
                        'etf_price': current['etf_price'],
                        'estimated_nav': current['estimated_nav'],
                        'timestamp': current['calculated_at']
                    }
                }

            # Extreme P/D detected
            z_score = extreme['z_score']
            pd_pct = extreme['current_premium_discount_pct']

            # Normalize: inverted (premium = negative)
            normalized = -np.clip(z_score / 3.0, -1.0, 1.0)

            interpretation = f"{extreme['severity']} {extreme['direction']}: {pd_pct:.2f}%"

            return {
                'normalized_score': float(normalized),
                'raw_value': float(z_score),
                'interpretation': interpretation,
                'metadata': {
                    'premium_discount_pct': pd_pct,
                    'percentile': extreme['percentile'],
                    'direction': extreme['direction'],
                    'severity': extreme['severity'],
                    'timestamp': extreme['calculated_at']
                }
            }

        except Exception as e:
            logger.error(f"Error calculating premium/discount score for {ticker}: {e}")
            return {'normalized_score': None, 'raw_value': None}

    async def _get_google_trends_score(self, ticker: str) -> Dict[str, Any]:
        """
        Google Trends sentiment score
        High interest = contrarian negative (retail euphoria)
        Normalized: -normalized_score / 150 (inverted, clamped)
        """
        try:
            if ticker not in self.COMMODITY_MAPPING:
                return {'normalized_score': None, 'raw_value': None}

            commodity = self.COMMODITY_MAPPING[ticker]['commodity']

            interest_score = await google_trends_collector.calculate_interest_score(
                commodity=commodity,
                timeframe="now 7-d"
            )

            if not interest_score:
                return {'normalized_score': None, 'raw_value': None}

            # Use normalized score (current / avg * 100)
            norm_score = interest_score.get('normalized_score', 100)

            # Contrarian: high interest (>150) = negative signal
            # Normalize: 150+ = -1.0, 50 = +0.33
            normalized = -np.clip((norm_score - 100) / 50.0, -1.0, 1.0)

            interpretation = f"Interest: {norm_score:.0f}% of average"
            if norm_score > 150:
                interpretation += " (High retail interest - caution)"
            elif norm_score < 75:
                interpretation += " (Low retail interest - opportunity)"

            return {
                'normalized_score': float(normalized),
                'raw_value': float(norm_score),
                'interpretation': interpretation,
                'metadata': {
                    'current_score': interest_score.get('current_score'),
                    'avg_score': interest_score.get('avg_score'),
                    'timeframe': interest_score.get('timeframe'),
                    'timestamp': interest_score.get('timestamp')
                }
            }

        except Exception as e:
            logger.debug(f"Error calculating Google Trends score for {ticker}: {e}")
            return {'normalized_score': None, 'raw_value': None}

    async def _get_reddit_sentiment_score(self, ticker: str) -> Dict[str, Any]:
        """
        Reddit sentiment score
        Positive sentiment = slightly positive (but lower weight due to noise)
        Normalized: sentiment_score (already -1 to +1)
        """
        try:
            if ticker not in self.COMMODITY_MAPPING:
                return {'normalized_score': None, 'raw_value': None}

            commodity = self.COMMODITY_MAPPING[ticker]['commodity']

            summary = await reddit_sentiment_collector.get_daily_sentiment_summary(
                commodity=commodity,
                hours=24
            )

            if not summary or summary.get('mentions', 0) == 0:
                return {'normalized_score': None, 'raw_value': None}

            sentiment_score = summary.get('sentiment_score', 0.0)
            mentions = summary.get('mentions', 0)

            # Use sentiment directly (already -1 to +1)
            # But reduce magnitude if low mentions (less reliable)
            confidence_multiplier = min(mentions / 10.0, 1.0)  # Full confidence at 10+ mentions
            normalized = sentiment_score * confidence_multiplier

            interpretation = f"Sentiment: {sentiment_score:.2f} ({mentions} mentions)"
            if sentiment_score > 0.3:
                interpretation += " (Bullish)"
            elif sentiment_score < -0.3:
                interpretation += " (Bearish)"
            else:
                interpretation += " (Neutral)"

            return {
                'normalized_score': float(normalized),
                'raw_value': float(sentiment_score),
                'interpretation': interpretation,
                'metadata': {
                    'mentions': mentions,
                    'bullish_ratio': summary.get('bullish_ratio'),
                    'velocity': summary.get('velocity'),
                    'timestamp': summary.get('calculated_at')
                }
            }

        except Exception as e:
            logger.debug(f"Error calculating Reddit sentiment score for {ticker}: {e}")
            return {'normalized_score': None, 'raw_value': None}

    def _calculate_confidence(self, available: int, total: int) -> str:
        """
        Calculate confidence level based on factor availability

        Args:
            available: Number of available factors
            total: Total number of factors

        Returns:
            Confidence level: 'high', 'medium', or 'low'
        """
        availability_pct = (available / total) * 100

        if availability_pct >= 75:
            return 'high'
        elif availability_pct >= 50:
            return 'medium'
        else:
            return 'low'

    def _assess_data_freshness(self, factor_scores: Dict) -> str:
        """
        Assess overall data freshness

        Returns:
            Freshness level: 'current', 'recent', or 'stale'
        """
        now = datetime.utcnow()
        freshness_scores = []

        for factor_data in factor_scores.values():
            timestamp_str = factor_data.get('metadata', {}).get('timestamp')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    age_hours = (now - timestamp).total_seconds() / 3600

                    if age_hours < 24:
                        freshness_scores.append(2)  # Current
                    elif age_hours < 72:
                        freshness_scores.append(1)  # Recent
                    else:
                        freshness_scores.append(0)  # Stale
                except (ValueError, TypeError, AttributeError):
                    pass  # Skip invalid timestamps

        if not freshness_scores:
            return 'unknown'

        avg_freshness = sum(freshness_scores) / len(freshness_scores)

        if avg_freshness >= 1.5:
            return 'current'
        elif avg_freshness >= 0.5:
            return 'recent'
        else:
            return 'stale'

    def _get_recommendation(self, score: float) -> str:
        """
        Convert composite score to recommendation

        Args:
            score: Composite score (-100 to +100)

        Returns:
            Recommendation string
        """
        if score > 60:
            return "Strong BUY"
        elif score > 30:
            return "Moderate BUY"
        elif score > -30:
            return "NEUTRAL"
        elif score > -60:
            return "Moderate SELL"
        else:
            return "Strong SELL"

    def _empty_score_response(self, ticker: str) -> Dict[str, Any]:
        """Return empty response when scoring fails"""
        return {
            'ticker': ticker,
            'composite_score': 0.0,
            'recommendation': 'NEUTRAL',
            'confidence': 'low',
            'factor_scores': {},
            'factor_contributions': {},
            'factors_available': 0,
            'factors_total': len(self.FACTOR_WEIGHTS),
            'error': 'Failed to calculate score',
            'calculated_at': datetime.utcnow().isoformat()
        }


# Singleton instance
composite_signal_scorer = CompositeSignalScorer()
