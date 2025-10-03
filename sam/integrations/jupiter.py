from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, cast

import aiohttp
from pydantic import BaseModel, Field, field_validator

from ..core.tools import Tool, ToolSpec
from ..integrations.smart_trader import SolanaTools
from ..utils.http_client import get_session

logger = logging.getLogger(__name__)


@dataclass
class PriceInfo:
    price_usd: float
    symbol: str
    name: str
    decimals: int


RoutePlan = List[Dict[str, Any]]
QuoteResponse = Dict[str, Any]


class JupiterTools:
    def __init__(self, solana_tools: Optional[SolanaTools] = None) -> None:
        # Jupiter v6 Quote/Swap API base
        self.base_url = "https://lite-api.jup.ag/swap/v1/"
        self.price_url = "https://lite-api.jup.ag/price/v3/"
        self.solana_tools = solana_tools

    async def close(self) -> None:
        """Close method for compatibility - shared client handles cleanup."""
        pass  # Shared HTTP client handles session lifecycle

    async def get_sol_price(self) -> Dict[str, Any]:
        """Get current SOL price in USD."""
        try:
            from sam.utils.price_service import get_price_service
            
            price_service = await get_price_service()
            sol_price = await price_service.get_sol_price_usd()
            
            return {
                "token_mint": "So11111111111111111111111111111111111111112",
                "price_usd": sol_price,
                "symbol": "SOL",
                "name": "Solana",
                "decimals": 9,
                "source": "price_service",
            }
        except Exception as e:
            logger.error(f"Error getting SOL price: {e}")
            return {"error": str(e)}

    async def get_token_price(self, token_mint: str) -> Dict[str, Any]:
        """Get token price from multiple sources with fallbacks."""
        try:
            session = await get_session()

            # Try Jupiter v4 first
            try:
                params = {"ids": token_mint}
                async with session.get("https://price.jup.ag/v4/price", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        price_section = _get_mapping(data, "data")
                        token_data = _get_mapping(price_section or {}, token_mint)

                        if token_data:
                            price = float(token_data.get("price", 0) or 0)
                            if price > 0:
                                logger.info(f"Got price for {token_mint} from Jupiter v4: ${price}")
                                return {
                                    "token_mint": token_mint,
                                    "price_usd": price,
                                    "symbol": str(token_data.get("symbol", "Unknown")),
                                    "name": str(token_data.get("name", "Unknown")),
                                    "decimals": int(token_data.get("decimals", 0) or 0),
                                    "source": "jupiter_v4",
                                }
            except Exception as e:
                logger.warning(f"Jupiter v4 failed for {token_mint}: {e}")

            # Try Jupiter v3 as fallback
            try:
                params = {"ids": token_mint}
                async with session.get(f"{self.price_url}/price", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        price_section = _get_mapping(data, "data")
                        token_data = _get_mapping(price_section or {}, token_mint)

                        if token_data:
                            price = float(token_data.get("price", 0) or 0)
                            if price > 0:
                                logger.info(f"Got price for {token_mint} from Jupiter v3: ${price}")
                                return {
                                    "token_mint": token_mint,
                                    "price_usd": price,
                                    "symbol": str(token_data.get("symbol", "Unknown")),
                                    "name": str(token_data.get("name", "Unknown")),
                                    "decimals": int(token_data.get("decimals", 0) or 0),
                                    "source": "jupiter_v3",
                                }
            except Exception as e:
                logger.warning(f"Jupiter v3 failed for {token_mint}: {e}")

            # Try DexScreener as fallback
            try:
                url = f"https://api.dexscreener.com/latest/dex/tokens/{token_mint}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        pairs = _get_sequence(data, "pairs")
                        
                        best_price = None
                        best_liquidity = -1
                        best_symbol = "Unknown"
                        
                        for pair in pairs:
                            if isinstance(pair, dict):
                                price_usd = pair.get("priceUsd")
                                liquidity = pair.get("liquidity", {})
                                usd_liquidity = liquidity.get("usd", 0) if isinstance(liquidity, dict) else 0
                                symbol = pair.get("baseToken", {}).get("symbol", "Unknown") if isinstance(pair.get("baseToken"), dict) else "Unknown"
                                
                                try:
                                    price = float(price_usd) if price_usd else 0
                                    liq = float(usd_liquidity) if usd_liquidity else 0
                                    
                                    if price > 0 and liq > best_liquidity:
                                        best_price = price
                                        best_liquidity = liq
                                        best_symbol = symbol
                                except (ValueError, TypeError):
                                    continue
                        
                        if best_price:
                            logger.info(f"Got price for {token_mint} from DexScreener: ${best_price}")
                            return {
                                "token_mint": token_mint,
                                "price_usd": best_price,
                                "symbol": best_symbol,
                                "name": best_symbol,
                                "decimals": 0,  # DexScreener doesn't provide decimals
                                "source": "dexscreener",
                            }
            except Exception as e:
                logger.warning(f"DexScreener failed for {token_mint}: {e}")

            # All sources failed
            return {"error": f"No price data found for token {token_mint} from any source"}

        except Exception as e:
            logger.error(f"Unexpected error getting token price: {e}")
            return {"error": str(e)}

    async def get_quote(
        self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 50
    ) -> Dict[str, Any]:
        """Get a swap quote from Jupiter."""
        try:
            session = await get_session()

            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(amount),
                "slippageBps": str(slippage_bps),
                "swapMode": "ExactIn",
                "restrictIntermediateTokens": "true",
            }

            # v6 quote endpoint
            async with session.get(f"{self.base_url}/quote", params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Jupiter quote API error {response.status}: {error_text}")

                    # Provide more helpful error messages
                    if response.status == 400:
                        return {
                            "error": f"Invalid quote request: {error_text}",
                            "help": "Check that token mint addresses are valid and amount is positive.",
                        }
                    elif response.status == 404:
                        return {
                            "error": "No route found for this token pair",
                            "help": "This token pair may not have sufficient liquidity or trading restrictions.",
                        }
                    else:
                        return {
                            "error": f"Quote API error {response.status}: {error_text}",
                            "help": "This may be a temporary Jupiter API issue. Try again later.",
                        }

                data = await response.json()

                logger.info(
                    f"Got quote: {amount} {input_mint} -> {data.get('outAmount', 0)} {output_mint}"
                )
                route_plan = data.get("routePlan", [])
                plan: RoutePlan = route_plan if isinstance(route_plan, list) else []

                return {
                    "quote": data,
                    "input_mint": input_mint,
                    "output_mint": output_mint,
                    "input_amount": amount,
                    "output_amount": int(data.get("outAmount", 0) or 0),
                    "price_impact_pct": float(data.get("priceImpactPct", 0) or 0),
                    "route_plan": plan,
                }

        except aiohttp.ClientError as e:
            logger.error(f"Network error getting quote: {e}")
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error getting quote: {e}")
            return {"error": str(e)}

    async def create_swap_transaction(
        self, user_public_key: str, quote_response: QuoteResponse, priority_fee: int = 1000
    ) -> Dict[str, Any]:
        """Create a swap transaction from a quote."""
        try:
            session = await get_session()

            payload = {
                "userPublicKey": user_public_key,
                "quoteResponse": quote_response,
                "dynamicComputeUnitLimit": True,
                "dynamicSlippage": True,
                "prioritizationFeeLamports": {
                    "priorityLevelWithMaxLamports": {
                        "priorityLevel": "medium",
                        "maxLamports": priority_fee,
                    }
                },
            }

            logger.info(f"Creating swap transaction for {user_public_key}")

            # v6 swap endpoint
            async with session.post(f"{self.base_url}/swap", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Jupiter swap API error {response.status}: {error_text}")
                    return {"error": f"Swap API error {response.status}: {error_text}"}

                data = await response.json()

                logger.info("Swap transaction created successfully")

                # Safely extract priority fee with proper error handling
                priority_fee_lamports = 0
                try:
                    priority_fee_instructions = _get_mapping(data, "priorityFeeInstructions")
                    compute_budget_instructions = _get_sequence(
                        priority_fee_instructions or {}, "computeBudgetInstructions"
                    )
                    first_instruction = (
                        compute_budget_instructions[0]
                        if compute_budget_instructions
                        and isinstance(compute_budget_instructions[0], Mapping)
                        else None
                    )
                    if isinstance(first_instruction, Mapping):
                        instruction_data = _get_mapping(first_instruction, "data") or {}
                        micro_lamports = instruction_data.get("microLamports")
                        if isinstance(micro_lamports, (int, float)) and micro_lamports > 0:
                            priority_fee_lamports = int(micro_lamports) // 1000
                except Exception as e:  # pragma: no cover - defensive typing
                    logger.warning(f"Could not extract priority fee: {e}")
                    priority_fee_lamports = 0

                return {
                    "success": True,
                    "transaction": data.get("swapTransaction"),
                    "last_valid_block_height": data.get("lastValidBlockHeight"),
                    "priority_fee_lamports": priority_fee_lamports,
                }

        except aiohttp.ClientError as e:
            logger.error(f"Network error creating swap: {e}")
            return {"error": f"Network error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error creating swap: {e}")
            return {"error": str(e)}

    async def execute_swap(
        self, input_mint: str, output_mint: str, amount: int, slippage_bps: int = 50
    ) -> Dict[str, Any]:
        """Execute a complete swap from quote to transaction."""
        if not self.solana_tools or not getattr(self.solana_tools, "keypair", None):
            return {
                "error": "No Solana wallet configured for swaps",
                "help": "Please set up your Solana wallet using the /wallet command or configure a private key in your environment.",
            }

        try:
            # Get quote
            logger.info(f"Getting quote for {amount} tokens from {input_mint} to {output_mint}")
            quote_result = await self.get_quote(input_mint, output_mint, amount, slippage_bps)
            if "error" in quote_result:
                error_msg = quote_result["error"]
                logger.error(f"Quote failed: {error_msg}")
                return {
                    "error": f"Failed to get swap quote: {error_msg}",
                    "help": "This could indicate: 1) Invalid token mint address, 2) Insufficient liquidity, 3) Network issues",
                }

            # Create swap transaction
            keypair = getattr(self.solana_tools, "keypair", None)
            if keypair is None:
                return {
                    "error": "Solana keypair not available",
                    "help": "Initialize Solana tools with a loaded keypair before executing swaps.",
                }

            user_public_key = str(keypair.pubkey())
            logger.info(f"Creating swap transaction for wallet {user_public_key[:8]}...")
            swap_result = await self.create_swap_transaction(user_public_key, quote_result["quote"])

            if "error" in swap_result:
                error_msg = swap_result["error"]
                logger.error(f"Swap transaction creation failed: {error_msg}")
                return {
                    "error": f"Failed to create swap transaction: {error_msg}",
                    "help": "This could indicate: 1) Invalid quote response, 2) Wallet issues, 3) Network connectivity problems",
                }

            if not swap_result.get("transaction"):
                return {
                    "error": "No transaction data received from Jupiter",
                    "help": "Jupiter API did not return transaction data. This may be a temporary service issue.",
                }

            # Deserialize and sign the transaction
            transaction_data = base64.b64decode(swap_result["transaction"])

            # Parse the transaction
            try:
                # Import solders for transaction handling
                from solders.transaction import VersionedTransaction

                # Deserialize the versioned transaction
                versioned_tx = VersionedTransaction.from_bytes(transaction_data)

                # Create a new signed transaction with the keypair
                signed_tx = VersionedTransaction(versioned_tx.message, [self.solana_tools.keypair])

                # Send the transaction to Solana
                from solana.rpc.types import TxOpts

                # Get the properly initialized client
                client = await getattr(self.solana_tools, "_get_client")()
                tx_hash = await client.send_transaction(
                    signed_tx, opts=TxOpts(skip_preflight=False, max_retries=3)
                )

                logger.info(f"Swap transaction executed successfully: {tx_hash}")

                # After successful transaction, get token decimals and adjust amount
                try:
                    # Get token metadata to find decimal places
                    token_info = await self.get_token_price(output_mint)
                    decimals = token_info.get("decimals", 6)  # Default to 6 if not found
                    
                    # Convert from smallest units to display units
                    raw_amount = quote_result.get("output_amount", 0)
                    display_amount = raw_amount / (10 ** decimals)
                    
                    return {
                        "success": True,
                        "input_mint": input_mint,
                        "output_mint": output_mint,
                        "input_amount": amount,
                        "expected_output_amount": quote_result.get("output_amount", 0),
                        "display_output_amount": display_amount,  # Add this
                        "decimals": decimals,  # Add this
                        "price_impact_pct": quote_result.get("price_impact_pct", 0),
                        "transaction_id": str(tx_hash),
                    }
                except Exception as e:
                    # Fallback to original behavior
                    return {
                        "success": True,
                        "input_mint": input_mint,
                        "output_mint": output_mint,
                        "input_amount": amount,
                        "expected_output_amount": quote_result.get("output_amount", 0),
                        "price_impact_pct": quote_result.get("price_impact_pct", 0),
                        "transaction_id": str(tx_hash),
                    }

            except Exception as sign_error:
                logger.error(f"Failed to execute swap transaction: {sign_error}")
                return {"error": f"Swap failed: {str(sign_error)}"}

        except Exception as e:
            logger.error(f"Swap execution failed: {e}")
            return {"error": str(e)}

    async def get_multiple_token_prices(self, token_mints: List[str]) -> Dict[str, Any]:
        """Get prices for multiple tokens from multiple sources with fallbacks."""
        try:
            session = await get_session()
            result: Dict[str, Any] = {"prices": {}, "missing": []}
            remaining_mints = token_mints.copy()

            # Try Jupiter v4 first
            try:
                params = {"ids": ",".join(remaining_mints)}
                async with session.get("https://price.jup.ag/v4/price", params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        price_section = _get_mapping(data, "data")
                        
                        if price_section:
                            for mint in remaining_mints.copy():
                                token_data = _get_mapping(price_section, mint)
                                if token_data:
                                    price = float(token_data.get("price", 0) or 0)
                                    if price > 0:
                                        result["prices"][mint] = {
                                            "price_usd": price,
                                            "symbol": str(token_data.get("symbol", "Unknown")),
                                            "name": str(token_data.get("name", "Unknown")),
                                            "decimals": int(token_data.get("decimals", 0) or 0),
                                            "source": "jupiter_v4",
                                        }
                                        remaining_mints.remove(mint)
            except Exception as e:
                logger.warning(f"Jupiter v4 failed for multiple tokens: {e}")

            # Try Jupiter v3 for remaining tokens
            if remaining_mints:
                try:
                    params = {"ids": ",".join(remaining_mints)}
                    async with session.get(f"{self.price_url}/price", params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            price_section = _get_mapping(data, "data")
                            
                            if price_section:
                                for mint in remaining_mints.copy():
                                    token_data = _get_mapping(price_section, mint)
                                    if token_data:
                                        price = float(token_data.get("price", 0) or 0)
                                        if price > 0:
                                            result["prices"][mint] = {
                                                "price_usd": price,
                                                "symbol": str(token_data.get("symbol", "Unknown")),
                                                "name": str(token_data.get("name", "Unknown")),
                                                "decimals": int(token_data.get("decimals", 0) or 0),
                                                "source": "jupiter_v3",
                                            }
                                            remaining_mints.remove(mint)
                except Exception as e:
                    logger.warning(f"Jupiter v3 failed for remaining tokens: {e}")

            # Try DexScreener for remaining tokens (one by one)
            for mint in remaining_mints.copy():
                try:
                    url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            pairs = _get_sequence(data, "pairs")
                            
                            best_price = None
                            best_liquidity = -1
                            best_symbol = "Unknown"
                            
                            for pair in pairs:
                                if isinstance(pair, dict):
                                    price_usd = pair.get("priceUsd")
                                    liquidity = pair.get("liquidity", {})
                                    usd_liquidity = liquidity.get("usd", 0) if isinstance(liquidity, dict) else 0
                                    symbol = pair.get("baseToken", {}).get("symbol", "Unknown") if isinstance(pair.get("baseToken"), dict) else "Unknown"
                                    
                                    try:
                                        price = float(price_usd) if price_usd else 0
                                        liq = float(usd_liquidity) if usd_liquidity else 0
                                        
                                        if price > 0 and liq > best_liquidity:
                                            best_price = price
                                            best_liquidity = liq
                                            best_symbol = symbol
                                    except (ValueError, TypeError):
                                        continue
                            
                            if best_price:
                                result["prices"][mint] = {
                                    "price_usd": best_price,
                                    "symbol": best_symbol,
                                    "name": best_symbol,
                                    "decimals": 0,
                                    "source": "dexscreener",
                                }
                                remaining_mints.remove(mint)
                except Exception as e:
                    logger.warning(f"DexScreener failed for {mint}: {e}")

            # Add remaining tokens to missing list
            result["missing"] = remaining_mints

            logger.info(
                f"Got prices for {len(result['prices'])} tokens, {len(result['missing'])} missing"
            )
            return result

        except Exception as e:
            logger.error(f"Unexpected error getting token prices: {e}")
            return {"error": str(e)}


def create_jupiter_tools(jupiter_tools: JupiterTools) -> List[Tool]:
    """Create Jupiter tool instances."""

    class SwapQuoteInput(BaseModel):
        input_mint: str = Field(..., description="Input token mint address")
        output_mint: str = Field(..., description="Output token mint address")
        amount: int = Field(..., gt=0, description="Input amount in token's smallest unit")
        slippage_bps: int = Field(50, ge=1, le=1000, description="Slippage in bps")

        @field_validator("input_mint", "output_mint")
        @classmethod
        def _validate_mint(cls, v: str) -> str:
            if not isinstance(v, str) or len(v) < 32 or len(v) > 44:
                raise ValueError("Invalid token mint address")
            return v

    class JupiterSwapInput(SwapQuoteInput):
        pass

    class TokenPriceInput(BaseModel):
        token_mint: str = Field(..., description="Token mint address to get price for")

        @field_validator("token_mint")
        @classmethod
        def _validate_mint(cls, v: str) -> str:
            if not isinstance(v, str) or len(v) < 32 or len(v) > 44:
                raise ValueError("Invalid token mint address")
            return v

    async def handle_get_swap_quote(args: Dict[str, Any]) -> Dict[str, Any]:
        input_mint = args.get("input_mint", "")
        output_mint = args.get("output_mint", "")
        amount = args.get("amount", 0)
        slippage_bps = args.get("slippage_bps", 50)

        return await jupiter_tools.get_quote(input_mint, output_mint, amount, slippage_bps)

    async def handle_jupiter_swap(args: Dict[str, Any]) -> Dict[str, Any]:
        input_mint = args.get("input_mint", "")
        output_mint = args.get("output_mint", "")
        amount = args.get("amount", 0)
        slippage_bps = args.get("slippage_bps", 50)

        return await jupiter_tools.execute_swap(input_mint, output_mint, amount, slippage_bps)

    async def handle_get_sol_price(args: Dict[str, Any]) -> Dict[str, Any]:
        return await jupiter_tools.get_sol_price()

    async def handle_get_token_price(args: Dict[str, Any]) -> Dict[str, Any]:
        token_mint = args.get("token_mint", "")
        return await jupiter_tools.get_token_price(token_mint)

    tools = [
        Tool(
            spec=ToolSpec(
                name="get_swap_quote",
                description="Get a swap quote from Jupiter for token exchange",
                input_schema={
                    "name": "get_swap_quote",
                    "description": "Get Jupiter swap quote",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "input_mint": {
                                "type": "string",
                                "description": "Input token mint address",
                            },
                            "output_mint": {
                                "type": "string",
                                "description": "Output token mint address",
                            },
                            "amount": {
                                "type": "integer",
                                "description": "Input amount in token's smallest unit",
                            },
                            "slippage_bps": {
                                "type": "integer",
                                "description": "Slippage tolerance in basis points (default: 50 = 0.5%)",
                                "default": 50,
                                "minimum": 1,
                                "maximum": 1000,
                            },
                        },
                        "required": ["input_mint", "output_mint", "amount"],
                    },
                },
            ),
            handler=handle_get_swap_quote,
            input_model=SwapQuoteInput,
        ),
        Tool(
            spec=ToolSpec(
                name="jupiter_swap",
                description="Execute a token swap using Jupiter aggregator",
                input_schema={
                    "name": "jupiter_swap",
                    "description": "Execute Jupiter token swap",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "input_mint": {
                                "type": "string",
                                "description": "Input token mint address",
                            },
                            "output_mint": {
                                "type": "string",
                                "description": "Output token mint address",
                            },
                            "amount": {
                                "type": "integer",
                                "description": "Input amount in token's smallest unit",
                            },
                            "slippage_bps": {
                                "type": "integer",
                                "description": "Slippage tolerance in basis points (default: 50 = 0.5%)",
                                "default": 50,
                                "minimum": 1,
                                "maximum": 1000,
                            },
                        },
                        "required": ["input_mint", "output_mint", "amount"],
                    },
                },
            ),
            handler=handle_jupiter_swap,
            input_model=JupiterSwapInput,
        ),
        Tool(
            spec=ToolSpec(
                name="get_sol_price",
                description="Get current USD price for SOL (Solana native token)",
                input_schema={
                    "name": "get_sol_price",
                    "description": "Get SOL price in USD",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            ),
            handler=handle_get_sol_price,
        ),
        Tool(
            spec=ToolSpec(
                name="get_token_price",
                description="Get current USD price for any Solana token using Jupiter Price API",
                input_schema={
                    "name": "get_token_price",
                    "description": "Get token price in USD",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "token_mint": {
                                "type": "string",
                                "description": "Token mint address to get price for",
                            },
                        },
                        "required": ["token_mint"],
                    },
                },
            ),
            handler=handle_get_token_price,
            input_model=TokenPriceInput,
        ),
    ]

    return tools
def _get_mapping(container: Mapping[str, Any] | Sequence[Any], key: str) -> Optional[Mapping[str, Any]]:
    if isinstance(container, Mapping):
        value = container.get(key)
        if isinstance(value, Mapping):
            return value
    return None


def _get_sequence(container: Mapping[str, Any], key: str) -> Sequence[Any]:
    value = container.get(key)
    if isinstance(value, Sequence):
        return value
    return []
