"""
DeFi Strategy Tools for Horizon AI

This module provides tools for DeFi investment advice and strategy recommendations
on Solana-based tokens and platforms.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from sam.core.tools import Tool, ToolSpec
from sam.core.context import RequestContext
from sam.utils.error_messages import handle_error_gracefully

logger = logging.getLogger(__name__)


async def analyze_token_defi_potential(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a token's DeFi potential and provide investment strategy recommendations.
    
    Args:
        token_address: Solana token address to analyze
        analysis_depth: Analysis depth (basic, intermediate, advanced)
        risk_tolerance: User's risk tolerance (conservative, moderate, aggressive)
        investment_horizon: Investment time horizon (short, medium, long)
        amount: Investment amount in SOL (optional)
    
    Returns:
        Dict containing DeFi analysis and strategy recommendations
    """
    try:
        token_address = args.get("token_address", "").strip()
        analysis_depth = args.get("analysis_depth", "intermediate")
        risk_tolerance = args.get("risk_tolerance", "moderate")
        investment_horizon = args.get("investment_horizon", "medium")
        amount = args.get("amount", 0)
        
        if not token_address:
            return {
                "success": False,
                "error": "Token address is required",
                "error_detail": {"code": "missing_token_address", "message": "Please provide a valid Solana token address"}
            }
        
        # Get token metadata and market data
        token_info = await _get_token_metadata(token_address)
        market_data = await _get_token_market_data(token_address)
        defi_metrics = await _get_defi_metrics(token_address)
        
        # Generate DeFi strategy recommendations
        strategy = await _generate_defi_strategy(
            token_info, market_data, defi_metrics, 
            analysis_depth, risk_tolerance, investment_horizon, amount
        )
        
        return {
            "success": True,
            "data": {
                "token_analysis": {
                    "address": token_address,
                    "symbol": token_info.get("symbol", "Unknown"),
                    "name": token_info.get("name", "Unknown"),
                    "market_cap": market_data.get("market_cap"),
                    "price": market_data.get("price"),
                    "volume_24h": market_data.get("volume_24h"),
                    "price_change_24h": market_data.get("price_change_24h")
                },
                "defi_metrics": defi_metrics,
                "strategy_recommendations": strategy,
                "analysis_timestamp": datetime.now().isoformat(),
                "analysis_depth": analysis_depth,
                "risk_tolerance": risk_tolerance,
                "investment_horizon": investment_horizon
            }
        }
        
    except Exception as e:
        logger.error(f"Error analyzing token DeFi potential: {e}")
        return handle_error_gracefully(e, {"context": "token_defi_analysis"})


async def analyze_defi_platform(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a DeFi platform and provide strategy recommendations.
    
    Args:
        platform_name: Name of the DeFi platform (e.g., "Raydium", "Orca", "Jupiter")
        platform_type: Type of platform (DEX, Lending, Yield Farming, etc.)
        analysis_focus: What to focus on (liquidity, yields, risks, opportunities)
    
    Returns:
        Dict containing platform analysis and strategy recommendations
    """
    try:
        platform_name = args.get("platform_name", "").strip()
        platform_type = args.get("platform_type", "DEX")
        analysis_focus = args.get("analysis_focus", "yields")
        
        if not platform_name:
            return {
                "success": False,
                "error": "Platform name is required",
                "error_detail": {"code": "missing_platform_name", "message": "Please provide a DeFi platform name"}
            }
        
        # Get platform data and metrics
        platform_data = await _get_platform_data(platform_name, platform_type)
        platform_metrics = await _get_platform_metrics(platform_name)
        opportunities = await _find_platform_opportunities(platform_name, analysis_focus)
        
        # Generate platform strategy
        strategy = await _generate_platform_strategy(
            platform_data, platform_metrics, opportunities, analysis_focus
        )
        
        return {
            "success": True,
            "data": {
                "platform_analysis": {
                    "name": platform_name,
                    "type": platform_type,
                    "total_value_locked": platform_metrics.get("tvl"),
                    "daily_volume": platform_metrics.get("daily_volume"),
                    "active_users": platform_metrics.get("active_users"),
                    "fees_24h": platform_metrics.get("fees_24h")
                },
                "opportunities": opportunities,
                "strategy_recommendations": strategy,
                "analysis_timestamp": datetime.now().isoformat(),
                "analysis_focus": analysis_focus
            }
        }
        
    except Exception as e:
        logger.error(f"Error analyzing DeFi platform: {e}")
        return handle_error_gracefully(e, {"context": "defi_platform_analysis"})


async def get_defi_yield_opportunities(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find the best DeFi yield opportunities on Solana.
    
    Args:
        min_apy: Minimum APY threshold (optional)
        max_risk: Maximum risk level (low, medium, high)
        token_preference: Preferred tokens (optional)
        platform_preference: Preferred platforms (optional)
        amount: Investment amount in SOL
    
    Returns:
        Dict containing yield opportunities and recommendations
    """
    try:
        min_apy = args.get("min_apy", 0)
        max_risk = args.get("max_risk", "medium")
        token_preference = args.get("token_preference", [])
        platform_preference = args.get("platform_preference", [])
        amount = args.get("amount", 0)
        
        # Get yield opportunities from various platforms
        yield_opportunities = await _scan_yield_opportunities(
            min_apy, max_risk, token_preference, platform_preference
        )
        
        # Rank opportunities by risk-adjusted returns
        ranked_opportunities = await _rank_yield_opportunities(
            yield_opportunities, amount, max_risk
        )
        
        # Generate yield strategy recommendations
        strategy = await _generate_yield_strategy(ranked_opportunities, amount, max_risk)
        
        return {
            "success": True,
            "data": {
                "yield_opportunities": ranked_opportunities,
                "strategy_recommendations": strategy,
                "search_criteria": {
                    "min_apy": min_apy,
                    "max_risk": max_risk,
                    "token_preference": token_preference,
                    "platform_preference": platform_preference,
                    "amount": amount
                },
                "analysis_timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error finding yield opportunities: {e}")
        return handle_error_gracefully(e, {"context": "yield_opportunities"})


async def create_defi_portfolio_strategy(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a comprehensive DeFi portfolio strategy.
    
    Args:
        total_amount: Total investment amount in SOL
        risk_tolerance: Risk tolerance (conservative, moderate, aggressive)
        investment_horizon: Investment time horizon (short, medium, long)
        goals: Investment goals (yield, growth, diversification, etc.)
        constraints: Any constraints (platform preferences, token exclusions, etc.)
    
    Returns:
        Dict containing portfolio strategy and allocation recommendations
    """
    try:
        total_amount = args.get("total_amount", 0)
        risk_tolerance = args.get("risk_tolerance", "moderate")
        investment_horizon = args.get("investment_horizon", "medium")
        goals = args.get("goals", ["yield", "growth"])
        constraints = args.get("constraints", {})
        
        if total_amount <= 0:
            return {
                "success": False,
                "error": "Total investment amount must be greater than 0",
                "error_detail": {"code": "invalid_amount", "message": "Please provide a valid investment amount"}
            }
        
        # Analyze current market conditions
        market_conditions = await _analyze_market_conditions()
        
        # Get available opportunities
        opportunities = await _get_portfolio_opportunities(goals, constraints)
        
        # Create portfolio allocation
        portfolio_allocation = await _create_portfolio_allocation(
            total_amount, risk_tolerance, investment_horizon, 
            goals, opportunities, market_conditions
        )
        
        # Generate risk management strategy
        risk_management = await _generate_risk_management_strategy(
            portfolio_allocation, risk_tolerance
        )
        
        return {
            "success": True,
            "data": {
                "portfolio_strategy": {
                    "total_amount": total_amount,
                    "risk_tolerance": risk_tolerance,
                    "investment_horizon": investment_horizon,
                    "goals": goals,
                    "allocation": portfolio_allocation
                },
                "risk_management": risk_management,
                "market_conditions": market_conditions,
                "rebalancing_schedule": await _create_rebalancing_schedule(investment_horizon),
                "analysis_timestamp": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating portfolio strategy: {e}")
        return handle_error_gracefully(e, {"context": "portfolio_strategy"})


# Helper functions for data gathering and analysis

async def _get_token_metadata(token_address: str) -> Dict[str, Any]:
    """Get token metadata from various sources."""
    # This would integrate with token metadata APIs
    # For now, return mock data structure
    return {
        "symbol": "TOKEN",
        "name": "Token Name",
        "decimals": 9,
        "supply": 1000000000,
        "description": "Token description"
    }


async def _get_token_market_data(token_address: str) -> Dict[str, Any]:
    """Get token market data."""
    # This would integrate with market data APIs
    return {
        "price": 0.001,
        "market_cap": 1000000,
        "volume_24h": 50000,
        "price_change_24h": 5.2,
        "liquidity": 250000
    }


async def _get_defi_metrics(token_address: str) -> Dict[str, Any]:
    """Get DeFi-specific metrics for the token."""
    return {
        "liquidity_pools": 15,
        "trading_volume_24h": 45000,
        "price_impact": 0.5,
        "slippage": 0.2,
        "yield_opportunities": 8
    }


async def _generate_defi_strategy(token_info: Dict, market_data: Dict, 
                                defi_metrics: Dict, analysis_depth: str,
                                risk_tolerance: str, investment_horizon: str,
                                amount: float) -> Dict[str, Any]:
    """Generate DeFi strategy recommendations."""
    
    strategies = []
    
    # Based on risk tolerance and investment horizon
    if risk_tolerance == "conservative":
        strategies.extend([
            {
                "type": "liquidity_provision",
                "platform": "Raydium",
                "description": "Provide liquidity to stable pairs for consistent yield",
                "expected_apy": 8.5,
                "risk_level": "low",
                "allocation_percentage": 60
            },
            {
                "type": "lending",
                "platform": "Solend",
                "description": "Lend tokens for stable returns",
                "expected_apy": 6.2,
                "risk_level": "low",
                "allocation_percentage": 40
            }
        ])
    elif risk_tolerance == "moderate":
        strategies.extend([
            {
                "type": "yield_farming",
                "platform": "Orca",
                "description": "Farm yield with moderate risk tokens",
                "expected_apy": 15.8,
                "risk_level": "medium",
                "allocation_percentage": 50
            },
            {
                "type": "liquidity_provision",
                "platform": "Raydium",
                "description": "Provide liquidity to trending pairs",
                "expected_apy": 12.3,
                "risk_level": "medium",
                "allocation_percentage": 30
            },
            {
                "type": "staking",
                "platform": "Marinade",
                "description": "Stake SOL for validator rewards",
                "expected_apy": 7.1,
                "risk_level": "low",
                "allocation_percentage": 20
            }
        ])
    else:  # aggressive
        strategies.extend([
            {
                "type": "yield_farming",
                "platform": "Multiple",
                "description": "High-risk, high-reward farming strategies",
                "expected_apy": 35.2,
                "risk_level": "high",
                "allocation_percentage": 70
            },
            {
                "type": "leveraged_positions",
                "platform": "Mango",
                "description": "Leveraged trading positions",
                "expected_apy": 45.0,
                "risk_level": "very_high",
                "allocation_percentage": 30
            }
        ])
    
    return {
        "recommended_strategies": strategies,
        "total_expected_apy": sum(s["expected_apy"] * s["allocation_percentage"] / 100 for s in strategies),
        "risk_assessment": _assess_portfolio_risk(strategies),
        "diversification_score": _calculate_diversification_score(strategies),
        "liquidity_requirements": _calculate_liquidity_requirements(strategies, amount)
    }


async def _get_platform_data(platform_name: str, platform_type: str) -> Dict[str, Any]:
    """Get platform-specific data."""
    return {
        "name": platform_name,
        "type": platform_type,
        "launch_date": "2021-01-01",
        "description": f"{platform_name} is a {platform_type} platform on Solana"
    }


async def _get_platform_metrics(platform_name: str) -> Dict[str, Any]:
    """Get platform metrics."""
    return {
        "tvl": 50000000,
        "daily_volume": 10000000,
        "active_users": 5000,
        "fees_24h": 50000,
        "protocol_revenue": 25000
    }


async def _find_platform_opportunities(platform_name: str, analysis_focus: str) -> List[Dict[str, Any]]:
    """Find opportunities on the platform."""
    opportunities = []
    
    if analysis_focus == "yields":
        opportunities.extend([
            {
                "type": "liquidity_pool",
                "pair": "SOL/USDC",
                "apy": 12.5,
                "risk": "medium",
                "liquidity": 5000000
            },
            {
                "type": "yield_farm",
                "token": "RAY",
                "apy": 18.7,
                "risk": "high",
                "liquidity": 2000000
            }
        ])
    
    return opportunities


async def _generate_platform_strategy(platform_data: Dict, platform_metrics: Dict,
                                    opportunities: List[Dict], analysis_focus: str) -> Dict[str, Any]:
    """Generate platform-specific strategy."""
    return {
        "platform_assessment": {
            "overall_score": 8.5,
            "strengths": ["High TVL", "Active community", "Good yields"],
            "weaknesses": ["High competition", "Complex UI"],
            "recommendation": "Strong platform for DeFi activities"
        },
        "opportunity_analysis": opportunities,
        "strategy_recommendations": [
            "Start with low-risk pools to understand the platform",
            "Diversify across multiple opportunities",
            "Monitor yields regularly and rebalance as needed"
        ]
    }


async def _scan_yield_opportunities(min_apy: float, max_risk: str, 
                                  token_preference: List[str], 
                                  platform_preference: List[str]) -> List[Dict[str, Any]]:
    """Scan for yield opportunities across platforms."""
    # This would integrate with multiple DeFi platforms
    opportunities = [
        {
            "platform": "Raydium",
            "type": "liquidity_pool",
            "pair": "SOL/USDC",
            "apy": 12.5,
            "risk_level": "medium",
            "min_amount": 1.0,
            "liquidity": 5000000,
            "fees": 0.25
        },
        {
            "platform": "Orca",
            "type": "yield_farm",
            "token": "ORCA",
            "apy": 18.7,
            "risk_level": "high",
            "min_amount": 0.5,
            "liquidity": 2000000,
            "fees": 0.3
        },
        {
            "platform": "Jupiter",
            "type": "liquidity_provision",
            "pair": "RAY/SOL",
            "apy": 15.2,
            "risk_level": "medium",
            "min_amount": 2.0,
            "liquidity": 3000000,
            "fees": 0.25
        }
    ]
    
    # Filter by criteria
    filtered_opportunities = []
    for opp in opportunities:
        if opp["apy"] >= min_apy:
            if max_risk == "low" and opp["risk_level"] == "low":
                filtered_opportunities.append(opp)
            elif max_risk == "medium" and opp["risk_level"] in ["low", "medium"]:
                filtered_opportunities.append(opp)
            elif max_risk == "high":
                filtered_opportunities.append(opp)
    
    return filtered_opportunities


async def _rank_yield_opportunities(opportunities: List[Dict], amount: float, max_risk: str) -> List[Dict[str, Any]]:
    """Rank yield opportunities by risk-adjusted returns."""
    # Calculate risk-adjusted scores
    for opp in opportunities:
        risk_multiplier = {"low": 1.0, "medium": 0.8, "high": 0.6}.get(opp["risk_level"], 0.4)
        opp["risk_adjusted_score"] = opp["apy"] * risk_multiplier
        opp["suitable_for_amount"] = amount >= opp.get("min_amount", 0)
    
    # Sort by risk-adjusted score
    return sorted(opportunities, key=lambda x: x["risk_adjusted_score"], reverse=True)


async def _generate_yield_strategy(opportunities: List[Dict], amount: float, max_risk: str) -> Dict[str, Any]:
    """Generate yield strategy recommendations."""
    suitable_opportunities = [opp for opp in opportunities if opp["suitable_for_amount"]]
    
    if not suitable_opportunities:
        return {
            "recommendation": "Increase investment amount or adjust risk tolerance",
            "alternative_strategies": ["Stake SOL", "Provide liquidity to stable pairs"]
        }
    
    # Create allocation strategy
    total_score = sum(opp["risk_adjusted_score"] for opp in suitable_opportunities[:3])
    allocation = []
    
    for opp in suitable_opportunities[:3]:
        percentage = (opp["risk_adjusted_score"] / total_score) * 100
        allocation.append({
            "opportunity": opp,
            "allocation_percentage": round(percentage, 1),
            "allocation_amount": round(amount * percentage / 100, 2)
        })
    
    return {
        "recommended_allocation": allocation,
        "expected_portfolio_apy": sum(
            opp["opportunity"]["apy"] * opp["allocation_percentage"] / 100 
            for opp in allocation
        ),
        "risk_diversification": "Well-diversified across platforms and risk levels",
        "rebalancing_frequency": "Weekly monitoring, monthly rebalancing"
    }


async def _analyze_market_conditions() -> Dict[str, Any]:
    """Analyze current market conditions."""
    return {
        "market_sentiment": "bullish",
        "volatility_index": 0.65,
        "liquidity_conditions": "high",
        "yield_environment": "favorable",
        "risk_factors": ["Regulatory uncertainty", "High gas fees"]
    }


async def _get_portfolio_opportunities(goals: List[str], constraints: Dict) -> List[Dict[str, Any]]:
    """Get available portfolio opportunities."""
    opportunities = []
    
    if "yield" in goals:
        opportunities.extend([
            {"type": "liquidity_provision", "expected_return": 12.5, "risk": "medium"},
            {"type": "yield_farming", "expected_return": 18.7, "risk": "high"},
            {"type": "lending", "expected_return": 8.2, "risk": "low"}
        ])
    
    if "growth" in goals:
        opportunities.extend([
            {"type": "token_holdings", "expected_return": 25.0, "risk": "high"},
            {"type": "leveraged_positions", "expected_return": 35.0, "risk": "very_high"}
        ])
    
    return opportunities


async def _create_portfolio_allocation(total_amount: float, risk_tolerance: str,
                                     investment_horizon: str, goals: List[str],
                                     opportunities: List[Dict], 
                                     market_conditions: Dict) -> Dict[str, Any]:
    """Create portfolio allocation strategy."""
    
    # Base allocation based on risk tolerance
    if risk_tolerance == "conservative":
        base_allocation = {
            "stable_yield": 60,
            "moderate_growth": 30,
            "cash_reserve": 10
        }
    elif risk_tolerance == "moderate":
        base_allocation = {
            "stable_yield": 40,
            "moderate_growth": 45,
            "aggressive_growth": 10,
            "cash_reserve": 5
        }
    else:  # aggressive
        base_allocation = {
            "stable_yield": 20,
            "moderate_growth": 30,
            "aggressive_growth": 40,
            "cash_reserve": 10
        }
    
    # Adjust based on market conditions
    if market_conditions["market_sentiment"] == "bearish":
        base_allocation["cash_reserve"] += 10
        base_allocation["stable_yield"] += 5
    
    return {
        "allocation_percentages": base_allocation,
        "allocation_amounts": {
            category: round(total_amount * percentage / 100, 2)
            for category, percentage in base_allocation.items()
        },
        "recommended_platforms": _get_recommended_platforms(risk_tolerance),
        "diversification_rules": _get_diversification_rules(risk_tolerance)
    }


async def _generate_risk_management_strategy(portfolio_allocation: Dict, risk_tolerance: str) -> Dict[str, Any]:
    """Generate risk management strategy."""
    return {
        "stop_loss_levels": {
            "conservative": 5,
            "moderate": 10,
            "aggressive": 15
        }.get(risk_tolerance, 10),
        "position_sizing": "Never risk more than 5% of portfolio on single position",
        "diversification_minimum": "Minimum 5 different positions",
        "rebalancing_triggers": [
            "Monthly calendar rebalancing",
            "5% deviation from target allocation",
            "Significant market events"
        ],
        "risk_monitoring": "Daily position monitoring, weekly risk assessment"
    }


async def _create_rebalancing_schedule(investment_horizon: str) -> Dict[str, Any]:
    """Create rebalancing schedule."""
    schedules = {
        "short": {"frequency": "weekly", "triggers": ["5% deviation", "market events"]},
        "medium": {"frequency": "monthly", "triggers": ["10% deviation", "quarterly review"]},
        "long": {"frequency": "quarterly", "triggers": ["15% deviation", "annual review"]}
    }
    
    return schedules.get(investment_horizon, schedules["medium"])


def _assess_portfolio_risk(strategies: List[Dict]) -> Dict[str, Any]:
    """Assess overall portfolio risk."""
    total_risk = sum(
        {"low": 1, "medium": 2, "high": 3, "very_high": 4}.get(s["risk_level"], 2)
        for s in strategies
    ) / len(strategies)
    
    return {
        "overall_risk_score": round(total_risk, 1),
        "risk_level": "low" if total_risk < 1.5 else "medium" if total_risk < 2.5 else "high",
        "risk_factors": ["Market volatility", "Liquidity risk", "Smart contract risk"]
    }


def _calculate_diversification_score(strategies: List[Dict]) -> float:
    """Calculate portfolio diversification score."""
    platforms = set(s["platform"] for s in strategies)
    types = set(s["type"] for s in strategies)
    
    # Simple diversification score based on unique platforms and types
    return min(10.0, len(platforms) * 2 + len(types) * 1.5)


def _calculate_liquidity_requirements(strategies: List[Dict], amount: float) -> Dict[str, Any]:
    """Calculate liquidity requirements."""
    total_liquidity_needed = sum(
        amount * s["allocation_percentage"] / 100
        for s in strategies
    )
    
    return {
        "total_liquidity_needed": round(total_liquidity_needed, 2),
        "liquidity_buffer": round(total_liquidity_needed * 0.1, 2),
        "recommended_reserve": round(total_liquidity_needed * 0.05, 2)
    }


def _get_recommended_platforms(risk_tolerance: str) -> List[str]:
    """Get recommended platforms based on risk tolerance."""
    platforms = {
        "conservative": ["Solend", "Marinade", "Raydium (stable pairs)"],
        "moderate": ["Raydium", "Orca", "Jupiter", "Solend"],
        "aggressive": ["Raydium", "Orca", "Jupiter", "Mango", "Serum"]
    }
    
    return platforms.get(risk_tolerance, platforms["moderate"])


def _get_diversification_rules(risk_tolerance: str) -> List[str]:
    """Get diversification rules based on risk tolerance."""
    rules = {
        "conservative": [
            "Maximum 30% in any single platform",
            "Focus on established, audited protocols",
            "Maintain 20% cash reserve"
        ],
        "moderate": [
            "Maximum 25% in any single platform",
            "Diversify across 3-5 different platforms",
            "Balance yield and growth opportunities"
        ],
        "aggressive": [
            "Maximum 20% in any single platform",
            "Diversify across 5+ platforms and strategies",
            "Include both established and emerging protocols"
        ]
    }
    
    return rules.get(risk_tolerance, rules["moderate"])


# Tool registration
def register(registry, agent=None):
    """Register DeFi strategy tools with the agent."""
    
    # Token DeFi Analysis Tool
    registry.register(Tool(
        spec=ToolSpec(
            name="analyze_token_defi_potential",
            description="Analyze a token's DeFi potential and provide investment strategy recommendations",
            input_schema={
                "type": "object",
                "properties": {
                    "token_address": {
                        "type": "string",
                        "description": "Solana token address to analyze"
                    },
                    "analysis_depth": {
                        "type": "string",
                        "enum": ["basic", "intermediate", "advanced"],
                        "description": "Depth of analysis to perform",
                        "default": "intermediate"
                    },
                    "risk_tolerance": {
                        "type": "string",
                        "enum": ["conservative", "moderate", "aggressive"],
                        "description": "User's risk tolerance level",
                        "default": "moderate"
                    },
                    "investment_horizon": {
                        "type": "string",
                        "enum": ["short", "medium", "long"],
                        "description": "Investment time horizon",
                        "default": "medium"
                    },
                    "amount": {
                        "type": "number",
                        "description": "Investment amount in SOL (optional)",
                        "default": 0
                    }
                },
                "required": ["token_address"]
            },
            namespace="defi_strategy",
            version="1.0.0"
        ),
        handler=analyze_token_defi_potential
    ))
    
    # DeFi Platform Analysis Tool
    registry.register(Tool(
        spec=ToolSpec(
            name="analyze_defi_platform",
            description="Analyze a DeFi platform and provide strategy recommendations",
            input_schema={
                "type": "object",
                "properties": {
                    "platform_name": {
                        "type": "string",
                        "description": "Name of the DeFi platform (e.g., Raydium, Orca, Jupiter)"
                    },
                    "platform_type": {
                        "type": "string",
                        "description": "Type of platform (DEX, Lending, Yield Farming, etc.)",
                        "default": "DEX"
                    },
                    "analysis_focus": {
                        "type": "string",
                        "enum": ["liquidity", "yields", "risks", "opportunities"],
                        "description": "What to focus the analysis on",
                        "default": "yields"
                    }
                },
                "required": ["platform_name"]
            },
            namespace="defi_strategy",
            version="1.0.0"
        ),
        handler=analyze_defi_platform
    ))
    
    # Yield Opportunities Tool
    registry.register(Tool(
        spec=ToolSpec(
            name="get_defi_yield_opportunities",
            description="Find the best DeFi yield opportunities on Solana",
            input_schema={
                "type": "object",
                "properties": {
                    "min_apy": {
                        "type": "number",
                        "description": "Minimum APY threshold",
                        "default": 0
                    },
                    "max_risk": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Maximum acceptable risk level",
                        "default": "medium"
                    },
                    "token_preference": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Preferred tokens (optional)",
                        "default": []
                    },
                    "platform_preference": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Preferred platforms (optional)",
                        "default": []
                    },
                    "amount": {
                        "type": "number",
                        "description": "Investment amount in SOL",
                        "default": 0
                    }
                }
            },
            namespace="defi_strategy",
            version="1.0.0"
        ),
        handler=get_defi_yield_opportunities
    ))
    
    # Portfolio Strategy Tool
    registry.register(Tool(
        spec=ToolSpec(
            name="create_defi_portfolio_strategy",
            description="Create a comprehensive DeFi portfolio strategy",
            input_schema={
                "type": "object",
                "properties": {
                    "total_amount": {
                        "type": "number",
                        "description": "Total investment amount in SOL"
                    },
                    "risk_tolerance": {
                        "type": "string",
                        "enum": ["conservative", "moderate", "aggressive"],
                        "description": "Risk tolerance level",
                        "default": "moderate"
                    },
                    "investment_horizon": {
                        "type": "string",
                        "enum": ["short", "medium", "long"],
                        "description": "Investment time horizon",
                        "default": "medium"
                    },
                    "goals": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Investment goals (yield, growth, diversification, etc.)",
                        "default": ["yield", "growth"]
                    },
                    "constraints": {
                        "type": "object",
                        "description": "Any constraints (platform preferences, token exclusions, etc.)",
                        "default": {}
                    }
                },
                "required": ["total_amount"]
            },
            namespace="defi_strategy",
            version="1.0.0"
        ),
        handler=create_defi_portfolio_strategy
    ))
