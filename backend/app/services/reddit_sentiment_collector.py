"""Reddit sentiment collector service for tracking retail investor sentiment"""

import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from collections import defaultdict, Counter
import re
from loguru import logger

from app.core.config import settings


class RedditSentimentCollector:
    """Collect and analyze sentiment from Reddit communities"""

    # Subreddits to monitor
    SUBREDDITS = {
        'wallstreetbets': {'members': '9M+', 'description': 'Retail trading hub'},
        'Silverbugs': {'members': '100K+', 'description': 'Silver stacking community'},
        'Gold': {'members': '50K+', 'description': 'Gold investing community'},
        'investing': {'members': '2M+', 'description': 'General investing'}
    }

    # Tickers to track
    TICKERS = ['AGQ', 'UGL', 'SLV', 'GLD', 'PSLV']

    # Keywords to track
    KEYWORDS = {
        'tickers': ['AGQ', 'UGL', 'SLV', 'GLD', 'PSLV'],
        'terms': ['silver', 'gold', 'platinum', 'precious metals', 'stacking']
    }

    # Sentiment keywords
    BULLISH_KEYWORDS = [
        'buy', 'buying', 'moon', 'squeeze', 'bullish', 'long', 'undervalued',
        'rocket', 'calls', 'accumulating', 'hodl', 'diamond hands', 'btfd',
        'breakout', 'rally', 'pump', 'to the moon', 'lfg', 'yolo'
    ]

    BEARISH_KEYWORDS = [
        'sell', 'selling', 'dump', 'dumping', 'bearish', 'short', 'overvalued',
        'crash', 'puts', 'distributing', 'exit', 'paper hands', 'rug pull',
        'breakdown', 'tank', 'fade', 'dead cat', 'bubble'
    ]

    # Reddit OAuth URL
    OAUTH_BASE_URL = "https://oauth.reddit.com"
    AUTH_URL = "https://www.reddit.com/api/v1/access_token"

    def __init__(self):
        """Initialize Reddit sentiment collector"""
        self.client_id = getattr(settings, 'REDDIT_CLIENT_ID', '')
        self.client_secret = getattr(settings, 'REDDIT_CLIENT_SECRET', '')
        self.user_agent = 'Commodity-ETF-Tracker/1.0'

        self.http_client = httpx.AsyncClient(
            headers={'User-Agent': self.user_agent},
            timeout=30.0,
            follow_redirects=True
        )

        self.access_token = None
        self.token_expires_at = None

        # Historical mention counts for velocity calculations
        self.mention_history: Dict[str, List[Tuple[datetime, int]]] = defaultdict(list)

        if not self.client_id or not self.client_secret:
            logger.warning(
                "REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET not configured. "
                "Reddit sentiment collection will not work."
            )

    async def _get_access_token(self) -> Optional[str]:
        """
        Get Reddit OAuth access token

        Returns:
            Access token string or None if authentication fails
        """
        if not self.client_id or not self.client_secret:
            logger.error("Reddit credentials not configured")
            return None

        # Check if current token is still valid
        if self.access_token and self.token_expires_at:
            if datetime.now(timezone.utc) < self.token_expires_at:
                return self.access_token

        try:
            logger.info("Requesting new Reddit access token")

            auth = httpx.BasicAuth(self.client_id, self.client_secret)

            response = await self.http_client.post(
                self.AUTH_URL,
                auth=auth,
                data={'grant_type': 'client_credentials'},
                headers={'User-Agent': self.user_agent}
            )
            response.raise_for_status()

            data = response.json()
            self.access_token = data.get('access_token')
            expires_in = data.get('expires_in', 3600)

            # Set expiration with 5-minute buffer
            self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 300)

            logger.success("Successfully obtained Reddit access token")
            return self.access_token

        except httpx.HTTPError as e:
            logger.error(f"HTTP error getting Reddit access token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting Reddit access token: {e}")
            return None

    async def fetch_subreddit_posts(
        self,
        subreddit: str,
        limit: int = 100,
        time_filter: str = 'day'
    ) -> List[Dict]:
        """
        Fetch recent posts from a subreddit

        Args:
            subreddit: Subreddit name (without r/)
            limit: Maximum number of posts to fetch (default 100)
            time_filter: Time filter - 'hour', 'day', 'week', 'month', 'year', 'all'

        Returns:
            List of post dictionaries with metadata
        """
        token = await self._get_access_token()
        if not token:
            logger.error("Cannot fetch posts without access token")
            return []

        try:
            logger.info(f"Fetching up to {limit} posts from r/{subreddit}")

            headers = {
                'Authorization': f'Bearer {token}',
                'User-Agent': self.user_agent
            }

            params = {
                'limit': min(limit, 100),  # Reddit API max is 100 per request
                't': time_filter
            }

            url = f"{self.OAUTH_BASE_URL}/r/{subreddit}/hot"

            response = await self.http_client.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()

            posts = []
            for child in data.get('data', {}).get('children', []):
                post_data = child.get('data', {})

                posts.append({
                    'id': post_data.get('id'),
                    'title': post_data.get('title', ''),
                    'selftext': post_data.get('selftext', ''),
                    'author': post_data.get('author', '[deleted]'),
                    'created_utc': post_data.get('created_utc', 0),
                    'score': post_data.get('score', 0),
                    'upvote_ratio': post_data.get('upvote_ratio', 0),
                    'num_comments': post_data.get('num_comments', 0),
                    'url': post_data.get('url', ''),
                    'permalink': f"https://reddit.com{post_data.get('permalink', '')}",
                    'subreddit': subreddit
                })

            logger.success(f"Fetched {len(posts)} posts from r/{subreddit}")
            return posts

        except httpx.HTTPError as e:
            logger.error(f"HTTP error fetching posts from r/{subreddit}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit}: {e}")
            return []

    async def search_keyword_mentions(
        self,
        keyword: str,
        subreddits: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Search for keyword mentions across subreddits

        Args:
            keyword: Keyword to search for
            subreddits: List of subreddit names (uses default if None)
            limit: Maximum results per subreddit

        Returns:
            List of posts mentioning the keyword
        """
        if subreddits is None:
            subreddits = list(self.SUBREDDITS.keys())

        token = await self._get_access_token()
        if not token:
            logger.error("Cannot search without access token")
            return []

        all_mentions = []

        for subreddit in subreddits:
            try:
                logger.info(f"Searching for '{keyword}' in r/{subreddit}")

                headers = {
                    'Authorization': f'Bearer {token}',
                    'User-Agent': self.user_agent
                }

                params = {
                    'q': keyword,
                    'limit': min(limit, 100),
                    'restrict_sr': 'on',
                    'sort': 'new',
                    't': 'day'
                }

                url = f"{self.OAUTH_BASE_URL}/r/{subreddit}/search"

                response = await self.http_client.get(url, headers=headers, params=params)
                response.raise_for_status()

                data = response.json()

                for child in data.get('data', {}).get('children', []):
                    post_data = child.get('data', {})

                    all_mentions.append({
                        'id': post_data.get('id'),
                        'title': post_data.get('title', ''),
                        'selftext': post_data.get('selftext', ''),
                        'author': post_data.get('author', '[deleted]'),
                        'created_utc': post_data.get('created_utc', 0),
                        'score': post_data.get('score', 0),
                        'upvote_ratio': post_data.get('upvote_ratio', 0),
                        'num_comments': post_data.get('num_comments', 0),
                        'permalink': f"https://reddit.com{post_data.get('permalink', '')}",
                        'subreddit': subreddit,
                        'keyword': keyword
                    })

                # Be polite to Reddit API
                await asyncio.sleep(1)

            except httpx.HTTPError as e:
                logger.error(f"HTTP error searching r/{subreddit} for '{keyword}': {e}")
                continue
            except Exception as e:
                logger.error(f"Error searching r/{subreddit} for '{keyword}': {e}")
                continue

        logger.success(f"Found {len(all_mentions)} mentions of '{keyword}' across {len(subreddits)} subreddits")
        return all_mentions

    def calculate_sentiment_score(self, text: str) -> float:
        """
        Calculate simple sentiment score using keyword matching

        Args:
            text: Text to analyze (title + body)

        Returns:
            Sentiment score from -1 (very bearish) to +1 (very bullish)
        """
        if not text:
            return 0.0

        text_lower = text.lower()

        # Count bullish and bearish keywords
        bullish_count = sum(1 for keyword in self.BULLISH_KEYWORDS if keyword in text_lower)
        bearish_count = sum(1 for keyword in self.BEARISH_KEYWORDS if keyword in text_lower)

        total_keywords = bullish_count + bearish_count

        if total_keywords == 0:
            return 0.0

        # Calculate normalized score
        sentiment = (bullish_count - bearish_count) / total_keywords

        return round(sentiment, 3)

    async def get_mention_velocity(
        self,
        keyword: str,
        hours: int = 24
    ) -> Dict[str, float]:
        """
        Calculate mention velocity (mentions per hour/day)

        Args:
            keyword: Keyword to track
            hours: Hours to look back (default 24)

        Returns:
            Dictionary with velocity metrics
        """
        mentions = await self.search_keyword_mentions(keyword)

        if not mentions:
            return {
                'keyword': keyword,
                'mentions_total': 0,
                'mentions_per_hour': 0.0,
                'mentions_per_day': 0.0,
                'time_period_hours': hours
            }

        # Count mentions in time buckets
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=hours)

        recent_mentions = [
            m for m in mentions
            if datetime.fromtimestamp(m['created_utc'], tz=timezone.utc) >= cutoff_time
        ]

        total_mentions = len(recent_mentions)
        mentions_per_hour = total_mentions / hours if hours > 0 else 0
        mentions_per_day = mentions_per_hour * 24

        # Store in history for trend analysis
        self.mention_history[keyword].append((now, total_mentions))

        # Keep only last 7 days of history
        week_ago = now - timedelta(days=7)
        self.mention_history[keyword] = [
            (ts, count) for ts, count in self.mention_history[keyword]
            if ts >= week_ago
        ]

        return {
            'keyword': keyword,
            'mentions_total': total_mentions,
            'mentions_per_hour': round(mentions_per_hour, 2),
            'mentions_per_day': round(mentions_per_day, 2),
            'time_period_hours': hours
        }

    async def detect_unusual_activity(
        self,
        keyword: str,
        threshold_multiplier: float = 3.0
    ) -> Dict:
        """
        Detect unusual spike in mentions (>3x normal activity)

        Args:
            keyword: Keyword to check
            threshold_multiplier: Multiplier for normal activity (default 3.0)

        Returns:
            Dictionary with spike detection results
        """
        # Get current velocity
        current_velocity = await self.get_mention_velocity(keyword, hours=1)
        current_rate = current_velocity['mentions_per_hour']

        # Get historical baseline (last 7 days average, excluding current hour)
        history = self.mention_history.get(keyword, [])

        if len(history) < 2:
            logger.warning(f"Insufficient history for {keyword} to detect unusual activity")
            return {
                'keyword': keyword,
                'is_unusual': False,
                'current_rate': current_rate,
                'baseline_rate': 0.0,
                'multiplier': 0.0,
                'threshold': threshold_multiplier,
                'confidence': 'low',
                'note': 'Insufficient historical data'
            }

        # Calculate baseline from history (excluding most recent)
        historical_rates = [count / 24 for _, count in history[:-1]]  # Convert to hourly rate
        baseline_rate = sum(historical_rates) / len(historical_rates) if historical_rates else 0

        # Calculate multiplier
        multiplier = current_rate / baseline_rate if baseline_rate > 0 else 0

        is_unusual = multiplier >= threshold_multiplier

        # Determine confidence based on history length
        confidence = 'high' if len(history) >= 14 else 'medium' if len(history) >= 7 else 'low'

        result = {
            'keyword': keyword,
            'is_unusual': is_unusual,
            'current_rate': round(current_rate, 2),
            'baseline_rate': round(baseline_rate, 2),
            'multiplier': round(multiplier, 2),
            'threshold': threshold_multiplier,
            'confidence': confidence,
            'data_points': len(history)
        }

        if is_unusual:
            logger.warning(
                f"UNUSUAL ACTIVITY DETECTED for '{keyword}': "
                f"{multiplier:.2f}x normal rate ({current_rate:.2f} vs {baseline_rate:.2f} per hour)"
            )

        return result

    async def get_daily_sentiment_summary(
        self,
        commodity: str,
        hours: int = 24
    ) -> Dict:
        """
        Get aggregated daily sentiment summary for a commodity

        Args:
            commodity: Commodity name (e.g., 'silver', 'gold')
            hours: Hours to look back (default 24)

        Returns:
            Comprehensive sentiment summary
        """
        logger.info(f"Generating daily sentiment summary for {commodity}")

        # Get all mentions for the commodity
        mentions = await self.search_keyword_mentions(commodity, limit=100)

        if not mentions:
            return {
                'commodity': commodity,
                'time_period_hours': hours,
                'mentions': 0,
                'sentiment_score': 0.0,
                'velocity': 0.0,
                'bullish_ratio': 0.0,
                'top_posts': [],
                'calculated_at': datetime.utcnow().isoformat()
            }

        # Filter by time period
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=hours)

        recent_mentions = [
            m for m in mentions
            if datetime.fromtimestamp(m['created_utc'], tz=timezone.utc) >= cutoff_time
        ]

        # Calculate sentiment for each post
        sentiments = []
        bullish_count = 0
        neutral_count = 0
        bearish_count = 0

        for mention in recent_mentions:
            text = f"{mention['title']} {mention['selftext']}"
            sentiment = self.calculate_sentiment_score(text)
            sentiments.append(sentiment)

            mention['sentiment'] = sentiment

            if sentiment > 0.2:
                bullish_count += 1
            elif sentiment < -0.2:
                bearish_count += 1
            else:
                neutral_count += 1

        # Calculate aggregates
        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        total_posts = len(recent_mentions)
        bullish_ratio = bullish_count / total_posts if total_posts > 0 else 0.0
        velocity = total_posts / hours if hours > 0 else 0.0

        # Get top posts by score
        top_posts = sorted(recent_mentions, key=lambda x: x['score'], reverse=True)[:10]
        top_posts_summary = [
            {
                'title': post['title'],
                'score': post['score'],
                'comments': post['num_comments'],
                'sentiment': post['sentiment'],
                'permalink': post['permalink'],
                'subreddit': post['subreddit'],
                'created_utc': datetime.fromtimestamp(post['created_utc'], tz=timezone.utc).isoformat()
            }
            for post in top_posts
        ]

        summary = {
            'commodity': commodity,
            'time_period_hours': hours,
            'mentions': total_posts,
            'sentiment_score': round(avg_sentiment, 3),
            'velocity': round(velocity, 2),
            'bullish_ratio': round(bullish_ratio, 3),
            'sentiment_distribution': {
                'bullish': bullish_count,
                'neutral': neutral_count,
                'bearish': bearish_count
            },
            'top_posts': top_posts_summary,
            'subreddits_covered': list(set(m['subreddit'] for m in recent_mentions)),
            'calculated_at': datetime.utcnow().isoformat()
        }

        logger.success(
            f"Generated sentiment summary for {commodity}: "
            f"{total_posts} mentions, sentiment={avg_sentiment:.3f}, "
            f"bullish_ratio={bullish_ratio:.1%}"
        )

        return summary

    async def get_multi_ticker_sentiment(
        self,
        tickers: Optional[List[str]] = None,
        hours: int = 24
    ) -> Dict:
        """
        Get sentiment for multiple tickers

        Args:
            tickers: List of ticker symbols (uses default if None)
            hours: Hours to look back

        Returns:
            Dictionary mapping tickers to sentiment summaries
        """
        if tickers is None:
            tickers = self.TICKERS

        logger.info(f"Fetching sentiment for {len(tickers)} tickers")

        results = {}

        for ticker in tickers:
            try:
                summary = await self.get_daily_sentiment_summary(ticker, hours=hours)
                results[ticker] = summary

                # Be polite to Reddit API
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error getting sentiment for {ticker}: {e}")
                results[ticker] = {
                    'error': str(e),
                    'mentions': 0,
                    'sentiment_score': 0.0
                }

        return {
            'tickers': results,
            'time_period_hours': hours,
            'calculated_at': datetime.utcnow().isoformat()
        }

    async def close(self):
        """Close the HTTP client"""
        await self.http_client.aclose()
        logger.debug("Reddit sentiment collector HTTP client closed")


# Singleton instance
reddit_sentiment_collector = RedditSentimentCollector()
