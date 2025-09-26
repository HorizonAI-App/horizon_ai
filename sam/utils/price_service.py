"""Price service for USD conversions (Jupiter first, DexScreener fallback or selectable)."""

import asyncio
import logging
import os
import time
from typing import Any, Dict, Mapping, Optional, Sequence
from dataclasses import dataclass

from .http_client import get_session

logger = logging.getLogger(__name__)


@dataclass
class PriceData:
    """Price information with caching metadata."""

    price_usd: float
    timestamp: float
    source: str = "jupiter"

    def is_stale(self, ttl_seconds: int = 30) -> bool:
        """Check if price data is stale."""
        return time.time() - self.timestamp > ttl_seconds

    @property
    def age_seconds(self) -> float:
        """Get age of price data in seconds."""
        return time.time() - self.timestamp


class PriceService:
    """Service for fetching and caching cryptocurrency prices."""

    def __init__(self, cache_ttl: int = 30):
        self.cache_ttl = cache_ttl  # Cache for 30 seconds
        self._price_cache: Dict[str, PriceData] = {}
        self._lock = asyncio.Lock()
        self._last_error_at: float = 0.0
        self._last_estimate_log_at: float = 0.0

        # Common token mint addresses for quick reference
        self.COMMON_TOKENS: Dict[str, str] = {
            "SOL": "So11111111111111111111111111111111111111112",
            "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
            "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
            "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "WIF": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
        }

    async def get_sol_price_usd(self) -> float:
        """Get current SOL price in USD.

        Provider order is controlled via env var SAM_PRICE_PROVIDER:
        - "coingecko" (default): CoinGecko only (most reliable)
        - "jupiter": Jupiter only
        - "dexscreener": DexScreener only
        - "auto": try CoinGecko, then Jupiter, then DexScreener
        """
        provider = (os.getenv("SAM_PRICE_PROVIDER") or "coingecko").lower()
        try:
            async with self._lock:
                # Check cache first
                cached_sol = self._price_cache.get("SOL")
                if cached_sol and not cached_sol.is_stale(self.cache_ttl):
                    logger.debug(
                        f"Using cached SOL price: ${cached_sol.price_usd} (age: {cached_sol.age_seconds:.1f}s)"
                    )
                    return cached_sol.price_usd

                async def _from_jupiter() -> Optional[float]:
                    try:
                        session = await get_session()
                        # Try the newer Jupiter API endpoint
                        url = "https://price.jup.ag/v4/price"
                        params = {
                            "ids": "So11111111111111111111111111111111111111112"
                        }  # SOL mint address
                        async with session.get(url, params=params) as response:
                            if response.status != 200:
                                logger.warning(f"Jupiter API v4 returned status {response.status}")
                                return None
                            raw_data = await response.json()
                            data = _as_mapping(raw_data)
                            if not data:
                                logger.warning("Jupiter API v4 returned empty data")
                                return None
                            prices = _as_mapping(data.get("data"))
                            if not prices:
                                logger.warning("Jupiter API v4 returned no price data")
                                return None
                            sol_mint = "So11111111111111111111111111111111111111112"
                            sol_entry = _as_mapping(prices.get(sol_mint))
                            if not sol_entry:
                                logger.warning("Jupiter API v4 returned no SOL entry")
                                return None
                            price = sol_entry.get("price")
                            try:
                                result = float(price) if price is not None else None
                                if result:
                                    logger.info(f"Successfully fetched SOL price from Jupiter v4: ${result}")
                                return result
                            except (TypeError, ValueError):
                                logger.warning(f"Jupiter API v4 returned invalid price: {price}")
                                return None
                    except Exception as e:
                        logger.warning(f"Jupiter API v4 request failed: {e}")
                        return None

                async def _from_coingecko() -> Optional[float]:
                    try:
                        session = await get_session()
                        url = "https://api.coingecko.com/api/v3/simple/price"
                        params = {
                            "ids": "solana",
                            "vs_currencies": "usd"
                        }
                        async with session.get(url, params=params) as response:
                            if response.status != 200:
                                logger.warning(f"CoinGecko API returned status {response.status}")
                                return None
                            raw_data = await response.json()
                            data = _as_mapping(raw_data)
                            if not data:
                                logger.warning("CoinGecko API returned empty data")
                                return None
                            sol_data = _as_mapping(data.get("solana"))
                            if not sol_data:
                                logger.warning("CoinGecko API returned no SOL data")
                                return None
                            price = sol_data.get("usd")
                            try:
                                result = float(price) if price is not None else None
                                if result:
                                    logger.info(f"Successfully fetched SOL price from CoinGecko: ${result}")
                                return result
                            except (TypeError, ValueError):
                                logger.warning(f"CoinGecko API returned invalid price: {price}")
                                return None
                    except Exception as e:
                        logger.warning(f"CoinGecko API request failed: {e}")
                        return None

                async def _from_dexscreener() -> Optional[float]:
                    try:
                        session = await get_session()
                        # SOL mint
                        mint = "So11111111111111111111111111111111111111112"
                        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
                        async with session.get(url) as response:
                            if response.status != 200:
                                logger.warning(f"DexScreener API returned status {response.status}")
                                return None
                            raw_data = await response.json()
                            data = _as_mapping(raw_data)
                            pairs = _as_sequence(data.get("pairs")) if data else []
                            best: Optional[float] = None
                            best_liq = -1.0
                            for pair in pairs:
                                mapping_pair = _as_mapping(pair)
                                if not mapping_pair:
                                    continue
                                liquidity = _as_mapping(mapping_pair.get("liquidity"))
                                usd_liquidity = liquidity.get("usd") if liquidity else None
                                price_usd = mapping_pair.get("priceUsd")
                                try:
                                    liq_value = float(usd_liquidity) if usd_liquidity is not None else 0.0
                                except (TypeError, ValueError):
                                    liq_value = 0.0
                                if price_usd is None:
                                    continue
                                if liq_value > best_liq:
                                    try:
                                        best = float(price_usd)
                                        best_liq = liq_value
                                    except (TypeError, ValueError):
                                        continue
                            if best is not None:
                                logger.info(f"Successfully fetched SOL price from DexScreener: ${best}")
                                return best
                            logger.warning("DexScreener API returned no valid price data")
                            return None
                    except Exception as e:
                        logger.warning(f"DexScreener API request failed: {e}")
                        return None

                async def _cache_and_return(price: float, source: str) -> float:
                    self._price_cache["SOL"] = PriceData(
                        price_usd=price, timestamp=time.time(), source=source
                    )
                    logger.debug(f"Fetched SOL price from {source}: ${price}")
                    return price

                # Provider selection
                if provider == "coingecko":
                    cg = await _from_coingecko()
                    if cg is not None:
                        return await _cache_and_return(cg, "coingecko")
                    return await self._get_fallback_sol_price()
                elif provider == "jupiter":
                    j = await _from_jupiter()
                    if j is not None:
                        return await _cache_and_return(j, "jupiter")
                    return await self._get_fallback_sol_price()
                elif provider == "dexscreener":
                    d = await _from_dexscreener()
                    if d is not None:
                        return await _cache_and_return(d, "dexscreener")
                    return await self._get_fallback_sol_price()
                else:  # auto
                    cg = await _from_coingecko()
                    if cg is not None:
                        return await _cache_and_return(cg, "coingecko")
                    j = await _from_jupiter()
                    if j is not None:
                        return await _cache_and_return(j, "jupiter")
                    d = await _from_dexscreener()
                    if d is not None:
                        return await _cache_and_return(d, "dexscreener")
                    return await self._get_fallback_sol_price()

        except Exception as e:
            # Reduce log noise by rate-limiting network error logs
            now = time.time()
            if now - self._last_error_at > 120:
                logger.error(f"Error fetching SOL price: {e}")
                self._last_error_at = now
            else:
                logger.debug(f"Price fetch error suppressed (recent): {e}")
            return await self._get_fallback_sol_price()

    async def _get_fallback_sol_price(self) -> float:
        """Fallback to cached price or estimated price."""
        # Try to use stale cached price
        cached_sol = self._price_cache.get("SOL")
        if cached_sol:
            logger.info(
                f"Using stale cached SOL price: ${cached_sol.price_usd} (age: {cached_sol.age_seconds:.1f}s)"
            )
            return cached_sol.price_usd

        # Last resort: use a reasonable estimate (configurable)
        try:
            estimated_price = float(os.getenv("SAM_SOL_ESTIMATE", "196.55"))
        except Exception:
            estimated_price = 196.55  # fallback default - updated to current market price
        now = time.time()
        if now - self._last_estimate_log_at > 60:
            logger.warning(f"Using estimated SOL price: ${estimated_price}")
            self._last_estimate_log_at = now
        else:
            logger.debug(f"Using estimated SOL price: ${estimated_price}")
        return estimated_price

    async def sol_to_usd(self, sol_amount: float) -> float:
        """Convert SOL amount to USD."""
        sol_price = await self.get_sol_price_usd()
        return sol_amount * sol_price

    async def format_sol_with_usd(self, sol_amount: float) -> str:
        """Format SOL amount with USD equivalent."""
        if sol_amount == 0:
            return "0 SOL ($0.00)"

        try:
            usd_value = await self.sol_to_usd(sol_amount)

            # Smart formatting based on amounts
            if sol_amount >= 1:
                sol_str = f"{sol_amount:.3f}"
            elif sol_amount >= 0.001:
                sol_str = f"{sol_amount:.4f}"
            else:
                sol_str = f"{sol_amount:.6f}"

            if usd_value >= 1:
                usd_str = f"${usd_value:.2f}"
            elif usd_value >= 0.01:
                usd_str = f"${usd_value:.3f}"
            else:
                usd_str = f"${usd_value:.4f}"

            return f"{sol_str} SOL ({usd_str})"

        except Exception as e:
            logger.error(f"Error formatting SOL with USD: {e}")
            return f"{sol_amount:.4f} SOL"

    async def format_portfolio_value(
        self,
        sol_balance: float,
        tokens: Optional[Sequence[Mapping[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Format complete portfolio with USD values."""
        try:
            sol_usd = await self.sol_to_usd(sol_balance)

            # For now, we'll just show SOL value
            # In the future, we could add token USD values too
            total_usd = sol_usd

            return {
                "sol_balance": sol_balance,
                "sol_usd": sol_usd,
                "total_usd": total_usd,
                "formatted_sol": await self.format_sol_with_usd(sol_balance),
                "formatted_total": f"${total_usd:.2f}",
                "sol_price": await self.get_sol_price_usd(),
            }

        except Exception as e:
            logger.error(f"Error formatting portfolio: {e}")
            return {
                "sol_balance": sol_balance,
                "sol_usd": 0.0,
                "total_usd": 0.0,
                "formatted_sol": f"{sol_balance:.4f} SOL",
                "formatted_total": "$0.00",
                "sol_price": 0.0,
            }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for debugging."""
        stats: Dict[str, Any] = {
            "cached_tokens": len(self._price_cache),
            "cache_ttl": self.cache_ttl,
            "tokens": {},
        }

        for token, price_data in self._price_cache.items():
            stats["tokens"][token] = {
                "price_usd": price_data.price_usd,
                "age_seconds": price_data.age_seconds,
                "is_stale": price_data.is_stale(self.cache_ttl),
                "source": price_data.source,
            }

        return stats

    async def clear_cache(self) -> None:
        """Clear all cached prices."""
        async with self._lock:
            self._price_cache.clear()
            logger.info("Price cache cleared")


# Global price service instance
_global_price_service: Optional[PriceService] = None
_price_service_lock = asyncio.Lock()


async def get_price_service() -> PriceService:
    """Get global price service instance."""
    global _global_price_service

    if _global_price_service is None:
        async with _price_service_lock:
            if _global_price_service is None:
                _global_price_service = PriceService()

    return _global_price_service


async def cleanup_price_service() -> None:
    """Cleanup global price service."""
    global _global_price_service
    if _global_price_service:
        await _global_price_service.clear_cache()
        _global_price_service = None


# Convenience functions
async def get_sol_price() -> float:
    """Get current SOL price in USD."""
    service = await get_price_service()
    return await service.get_sol_price_usd()


async def format_sol_usd(sol_amount: float) -> str:
    """Format SOL amount with USD value."""
    service = await get_price_service()
    return await service.format_sol_with_usd(sol_amount)


async def sol_to_usd(sol_amount: float) -> float:
    """Convert SOL to USD."""
    service = await get_price_service()
    return await service.sol_to_usd(sol_amount)


def _as_mapping(value: Any) -> Optional[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        return value
    return None


def _as_sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return []
