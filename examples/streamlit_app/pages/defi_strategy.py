"""
DeFi Strategy Page for Horizon AI

This page provides DeFi investment advice and strategy recommendations
for Solana-based tokens and platforms.
"""

import sys
from pathlib import Path
import streamlit as st
import asyncio
import json
from datetime import datetime

_PAGES_DIR = Path(__file__).resolve().parent
_APP_DIR = _PAGES_DIR.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))
from ui_shared import inject_css, get_local_context, run_sync  # noqa: E402

# Set page config with logo
try:
    logo_path = Path(__file__).parent.parent.parent / "logo.png"
    if logo_path.exists():
        st.set_page_config(page_title="DeFi Strategy", page_icon=str(logo_path), layout="wide")
    else:
        st.set_page_config(page_title="DeFi Strategy", page_icon="📊", layout="wide")
except Exception:
    st.set_page_config(page_title="DeFi Strategy", page_icon="📊", layout="wide")

inject_css()

# Display Horizon logo
try:
    logo_path = Path(__file__).parent.parent.parent / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=100)
        st.title("DeFi Strategy Center")
    else:
        st.title("📊 DeFi Strategy Center")  # Fallback to emoji
except Exception:
    st.title("📊 DeFi Strategy Center")  # Fallback to emoji

st.markdown("""
**Get AI-powered DeFi investment advice and strategy recommendations for Solana-based tokens and platforms.**
""")

# Initialize session state
if "defi_analysis_results" not in st.session_state:
    st.session_state.defi_analysis_results = {}

# Sidebar for navigation
st.sidebar.title("DeFi Strategy Tools")
strategy_type = st.sidebar.selectbox(
    "Choose Analysis Type",
    ["Token Analysis", "Platform Analysis", "Yield Opportunities", "Portfolio Strategy"]
)

# Main content area
if strategy_type == "Token Analysis":
    st.header("🔍 Token DeFi Analysis")
    st.markdown("Analyze any Solana token's DeFi potential and get investment strategy recommendations.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        token_address = st.text_input(
            "Token Address",
            placeholder="Enter Solana token address (e.g., So11111111111111111111111111111111111111112)",
            help="The mint address of the token you want to analyze"
        )
        
        analysis_depth = st.selectbox(
            "Analysis Depth",
            ["basic", "intermediate", "advanced"],
            index=1,
            help="How detailed the analysis should be"
        )
    
    with col2:
        risk_tolerance = st.selectbox(
            "Risk Tolerance",
            ["conservative", "moderate", "aggressive"],
            index=1,
            help="Your risk tolerance level"
        )
        
        investment_horizon = st.selectbox(
            "Investment Horizon",
            ["short", "medium", "long"],
            index=1,
            help="How long you plan to hold the investment"
        )
        
        amount = st.number_input(
            "Investment Amount (SOL)",
            min_value=0.0,
            value=10.0,
            step=0.1,
            help="Amount you plan to invest (optional)"
        )
    
    if st.button("Analyze Token", type="primary"):
        if not token_address:
            st.error("Please enter a token address")
        else:
            with st.spinner("Analyzing token DeFi potential..."):
                try:
                    # Call the DeFi strategy tool
                    from sam.web.session import get_agent
                    
                    async def analyze_token():
                        agent = await get_agent(get_local_context())
                        result = await agent.execute_tool(
                            "analyze_token_defi_potential",
                            {
                                "token_address": token_address,
                                "analysis_depth": analysis_depth,
                                "risk_tolerance": risk_tolerance,
                                "investment_horizon": investment_horizon,
                                "amount": amount
                            }
                        )
                        return result
                    
                    result = run_sync(analyze_token())
                    
                    if result.get("success"):
                        st.session_state.defi_analysis_results["token"] = result["data"]
                        st.success("Analysis completed!")
                    else:
                        st.error(f"Analysis failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
    
    # Display results
    if "token" in st.session_state.defi_analysis_results:
        data = st.session_state.defi_analysis_results["token"]
        
        st.subheader("📈 Analysis Results")
        
        # Token Information
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Symbol", data["token_analysis"]["symbol"])
        with col2:
            st.metric("Price", f"${data['token_analysis']['price']:.6f}" if data['token_analysis']['price'] else "N/A")
        with col3:
            st.metric("Market Cap", f"${data['token_analysis']['market_cap']:,.0f}" if data['token_analysis']['market_cap'] else "N/A")
        with col4:
            change = data['token_analysis']['price_change_24h']
            if change is not None:
                st.metric("24h Change", f"{change:+.2f}%", delta=f"{change:+.2f}%")
            else:
                st.metric("24h Change", "N/A")
        
        # DeFi Metrics
        st.subheader("🔧 DeFi Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Liquidity Pools", data["defi_metrics"]["liquidity_pools"])
        with col2:
            st.metric("Trading Volume 24h", f"${data['defi_metrics']['trading_volume_24h']:,.0f}")
        with col3:
            st.metric("Yield Opportunities", data["defi_metrics"]["yield_opportunities"])
        
        # Strategy Recommendations
        st.subheader("💡 Strategy Recommendations")
        strategies = data["strategy_recommendations"]["recommended_strategies"]
        
        for i, strategy in enumerate(strategies, 1):
            with st.expander(f"Strategy {i}: {strategy['type'].replace('_', ' ').title()}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**Platform:** {strategy['platform']}")
                    st.write(f"**Description:** {strategy['description']}")
                    st.write(f"**Risk Level:** {strategy['risk_level'].title()}")
                with col2:
                    st.metric("Expected APY", f"{strategy['expected_apy']:.1f}%")
                    st.metric("Allocation", f"{strategy['allocation_percentage']:.0f}%")
        
        # Portfolio Summary
        st.subheader("📊 Portfolio Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Expected APY", f"{data['strategy_recommendations']['total_expected_apy']:.1f}%")
        with col2:
            st.metric("Risk Level", data['strategy_recommendations']['risk_assessment']['risk_level'].title())
        with col3:
            st.metric("Diversification Score", f"{data['strategy_recommendations']['diversification_score']:.1f}/10")

elif strategy_type == "Platform Analysis":
    st.header("🏛️ DeFi Platform Analysis")
    st.markdown("Analyze DeFi platforms and discover opportunities for yield farming and liquidity provision.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        platform_name = st.text_input(
            "Platform Name",
            placeholder="e.g., Raydium, Orca, Jupiter, Solend",
            help="Name of the DeFi platform to analyze"
        )
        
        platform_type = st.selectbox(
            "Platform Type",
            ["DEX", "Lending", "Yield Farming", "Derivatives", "Staking"],
            help="Type of DeFi platform"
        )
    
    with col2:
        analysis_focus = st.selectbox(
            "Analysis Focus",
            ["liquidity", "yields", "risks", "opportunities"],
            help="What to focus the analysis on"
        )
    
    if st.button("Analyze Platform", type="primary"):
        if not platform_name:
            st.error("Please enter a platform name")
        else:
            with st.spinner("Analyzing DeFi platform..."):
                try:
                    from sam.web.session import get_agent
                    
                    async def analyze_platform():
                        agent = await get_agent(get_local_context())
                        result = await agent.execute_tool(
                            "analyze_defi_platform",
                            {
                                "platform_name": platform_name,
                                "platform_type": platform_type,
                                "analysis_focus": analysis_focus
                            }
                        )
                        return result
                    
                    result = run_sync(analyze_platform())
                    
                    if result.get("success"):
                        st.session_state.defi_analysis_results["platform"] = result["data"]
                        st.success("Platform analysis completed!")
                    else:
                        st.error(f"Analysis failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
    
    # Display results
    if "platform" in st.session_state.defi_analysis_results:
        data = st.session_state.defi_analysis_results["platform"]
        
        st.subheader("📊 Platform Analysis Results")
        
        # Platform Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Value Locked", f"${data['platform_analysis']['total_value_locked']:,.0f}")
        with col2:
            st.metric("Daily Volume", f"${data['platform_analysis']['daily_volume']:,.0f}")
        with col3:
            st.metric("Active Users", f"{data['platform_analysis']['active_users']:,}")
        with col4:
            st.metric("Fees 24h", f"${data['platform_analysis']['fees_24h']:,.0f}")
        
        # Platform Assessment
        st.subheader("🎯 Platform Assessment")
        assessment = data["strategy_recommendations"]["platform_assessment"]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Overall Score", f"{assessment['overall_score']}/10")
            st.write("**Strengths:**")
            for strength in assessment["strengths"]:
                st.write(f"✅ {strength}")
        with col2:
            st.write("**Weaknesses:**")
            for weakness in assessment["weaknesses"]:
                st.write(f"⚠️ {weakness}")
        
        st.write(f"**Recommendation:** {assessment['recommendation']}")
        
        # Opportunities
        if data["opportunities"]:
            st.subheader("🚀 Opportunities")
            for opp in data["opportunities"]:
                with st.expander(f"{opp['type'].replace('_', ' ').title()}: {opp.get('pair', opp.get('token', 'N/A'))}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("APY", f"{opp['apy']:.1f}%")
                    with col2:
                        st.metric("Risk", opp["risk"].title())
                    with col3:
                        st.metric("Liquidity", f"${opp['liquidity']:,.0f}")
        
        # Strategy Recommendations
        st.subheader("💡 Strategy Recommendations")
        for i, rec in enumerate(data["strategy_recommendations"]["strategy_recommendations"], 1):
            st.write(f"{i}. {rec}")

elif strategy_type == "Yield Opportunities":
    st.header("💰 Yield Opportunities")
    st.markdown("Discover the best DeFi yield opportunities across Solana platforms.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        min_apy = st.number_input(
            "Minimum APY (%)",
            min_value=0.0,
            value=5.0,
            step=0.1,
            help="Minimum APY threshold"
        )
        
        max_risk = st.selectbox(
            "Maximum Risk Level",
            ["low", "medium", "high"],
            index=1,
            help="Maximum acceptable risk level"
        )
        
        amount = st.number_input(
            "Investment Amount (SOL)",
            min_value=0.0,
            value=10.0,
            step=0.1,
            help="Amount you plan to invest"
        )
    
    with col2:
        token_preference = st.multiselect(
            "Token Preferences (Optional)",
            ["SOL", "USDC", "USDT", "RAY", "ORCA", "SRM", "MNGO"],
            help="Preferred tokens for yield farming"
        )
        
        platform_preference = st.multiselect(
            "Platform Preferences (Optional)",
            ["Raydium", "Orca", "Jupiter", "Solend", "Mango", "Serum"],
            help="Preferred DeFi platforms"
        )
    
    if st.button("Find Yield Opportunities", type="primary"):
        with st.spinner("Scanning for yield opportunities..."):
            try:
                from sam.web.session import get_agent
                
                async def find_yields():
                    agent = await get_agent(get_local_context())
                    result = await agent.execute_tool(
                        "get_defi_yield_opportunities",
                        {
                            "min_apy": min_apy,
                            "max_risk": max_risk,
                            "token_preference": token_preference,
                            "platform_preference": platform_preference,
                            "amount": amount
                        }
                    )
                    return result
                
                result = run_sync(find_yields())
                
                if result.get("success"):
                    st.session_state.defi_analysis_results["yield"] = result["data"]
                    st.success("Yield opportunities found!")
                else:
                    st.error(f"Search failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"Error during search: {str(e)}")
    
    # Display results
    if "yield" in st.session_state.defi_analysis_results:
        data = st.session_state.defi_analysis_results["yield"]
        
        st.subheader("🎯 Top Yield Opportunities")
        
        # Strategy Summary
        strategy = data["strategy_recommendations"]
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Expected Portfolio APY", f"{strategy['expected_portfolio_apy']:.1f}%")
        with col2:
            st.metric("Risk Diversification", strategy["risk_diversification"])
        with col3:
            st.metric("Rebalancing", strategy["rebalancing_frequency"])
        
        # Yield Opportunities
        opportunities = data["yield_opportunities"]
        for i, opp in enumerate(opportunities, 1):
            with st.expander(f"Opportunity {i}: {opp['platform']} - {opp['pair']}"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("APY", f"{opp['apy']:.1f}%")
                with col2:
                    st.metric("Risk Level", opp["risk_level"].title())
                with col3:
                    st.metric("Min Amount", f"{opp['min_amount']} SOL")
                with col4:
                    st.metric("Liquidity", f"${opp['liquidity']:,.0f}")
                
                st.write(f"**Type:** {opp['type'].replace('_', ' ').title()}")
                st.write(f"**Fees:** {opp['fees']}%")
        
        # Recommended Allocation
        if "recommended_allocation" in strategy:
            st.subheader("📊 Recommended Allocation")
            for allocation in strategy["recommended_allocation"]:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.write(f"**{allocation['opportunity']['platform']} - {allocation['opportunity']['pair']}**")
                with col2:
                    st.metric("Allocation", f"{allocation['allocation_percentage']:.1f}%")
                with col3:
                    st.metric("Amount", f"{allocation['allocation_amount']:.2f} SOL")

elif strategy_type == "Portfolio Strategy":
    st.header("🎯 Portfolio Strategy")
    st.markdown("Create a comprehensive DeFi portfolio strategy tailored to your investment goals.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        total_amount = st.number_input(
            "Total Investment Amount (SOL)",
            min_value=1.0,
            value=100.0,
            step=1.0,
            help="Total amount you want to invest"
        )
        
        risk_tolerance = st.selectbox(
            "Risk Tolerance",
            ["conservative", "moderate", "aggressive"],
            index=1,
            help="Your risk tolerance level"
        )
        
        investment_horizon = st.selectbox(
            "Investment Horizon",
            ["short", "medium", "long"],
            index=1,
            help="How long you plan to hold investments"
        )
    
    with col2:
        goals = st.multiselect(
            "Investment Goals",
            ["yield", "growth", "diversification", "capital_preservation"],
            default=["yield", "growth"],
            help="What you want to achieve with your investments"
        )
        
        # Constraints (simplified for UI)
        st.write("**Constraints (Optional)**")
        exclude_tokens = st.multiselect(
            "Exclude Tokens",
            ["SOL", "USDC", "USDT", "RAY", "ORCA", "SRM", "MNGO"],
            help="Tokens you don't want to invest in"
        )
        
        platform_preference = st.multiselect(
            "Platform Preferences",
            ["Raydium", "Orca", "Jupiter", "Solend", "Mango", "Serum"],
            help="Preferred platforms (leave empty for all platforms)"
        )
    
    constraints = {
        "exclude_tokens": exclude_tokens,
        "platform_preference": platform_preference
    }
    
    if st.button("Create Portfolio Strategy", type="primary"):
        if not goals:
            st.error("Please select at least one investment goal")
        else:
            with st.spinner("Creating portfolio strategy..."):
                try:
                    from sam.web.session import get_agent
                    
                    async def create_strategy():
                        agent = await get_agent(get_local_context())
                        result = await agent.execute_tool(
                            "create_defi_portfolio_strategy",
                            {
                                "total_amount": total_amount,
                                "risk_tolerance": risk_tolerance,
                                "investment_horizon": investment_horizon,
                                "goals": goals,
                                "constraints": constraints
                            }
                        )
                        return result
                    
                    result = run_sync(create_strategy())
                    
                    if result.get("success"):
                        st.session_state.defi_analysis_results["portfolio"] = result["data"]
                        st.success("Portfolio strategy created!")
                    else:
                        st.error(f"Strategy creation failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"Error during strategy creation: {str(e)}")
    
    # Display results
    if "portfolio" in st.session_state.defi_analysis_results:
        data = st.session_state.defi_analysis_results["portfolio"]
        
        st.subheader("📊 Portfolio Strategy")
        
        # Portfolio Overview
        strategy = data["portfolio_strategy"]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Amount", f"{strategy['total_amount']:.1f} SOL")
        with col2:
            st.metric("Risk Tolerance", strategy["risk_tolerance"].title())
        with col3:
            st.metric("Investment Horizon", strategy["investment_horizon"].title())
        with col4:
            st.metric("Goals", ", ".join(strategy["goals"]).title())
        
        # Allocation Breakdown
        st.subheader("💰 Portfolio Allocation")
        allocation = strategy["allocation"]
        
        col1, col2 = st.columns(2)
        with col1:
            st.write("**Allocation Percentages:**")
            for category, percentage in allocation["allocation_percentages"].items():
                st.write(f"• {category.replace('_', ' ').title()}: {percentage}%")
        
        with col2:
            st.write("**Allocation Amounts:**")
            for category, amount in allocation["allocation_amounts"].items():
                st.write(f"• {category.replace('_', ' ').title()}: {amount:.2f} SOL")
        
        # Recommended Platforms
        st.subheader("🏛️ Recommended Platforms")
        platforms = allocation["recommended_platforms"]
        for platform in platforms:
            st.write(f"• {platform}")
        
        # Diversification Rules
        st.subheader("📋 Diversification Rules")
        rules = allocation["diversification_rules"]
        for rule in rules:
            st.write(f"• {rule}")
        
        # Risk Management
        st.subheader("🛡️ Risk Management")
        risk_mgmt = data["risk_management"]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Stop Loss Level", f"{risk_mgmt['stop_loss_levels']}%")
            st.write(f"**Position Sizing:** {risk_mgmt['position_sizing']}")
        with col2:
            st.write(f"**Diversification Minimum:** {risk_mgmt['diversification_minimum']}")
            st.write(f"**Risk Monitoring:** {risk_mgmt['risk_monitoring']}")
        
        # Rebalancing Triggers
        st.write("**Rebalancing Triggers:**")
        for trigger in risk_mgmt["rebalancing_triggers"]:
            st.write(f"• {trigger}")
        
        # Market Conditions
        st.subheader("🌍 Market Conditions")
        market = data["market_conditions"]
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Market Sentiment", market["market_sentiment"].title())
        with col2:
            st.metric("Volatility Index", f"{market['volatility_index']:.2f}")
        with col3:
            st.metric("Liquidity Conditions", market["liquidity_conditions"].title())
        with col4:
            st.metric("Yield Environment", market["yield_environment"].title())
        
        # Rebalancing Schedule
        st.subheader("📅 Rebalancing Schedule")
        schedule = data["rebalancing_schedule"]
        st.write(f"**Frequency:** {schedule['frequency']}")
        st.write("**Triggers:**")
        for trigger in schedule["triggers"]:
            st.write(f"• {trigger}")

# Footer
st.markdown("---")
st.markdown("""
**Disclaimer:** This is for educational and informational purposes only. 
DeFi investments carry significant risks including smart contract risks, 
impermanent loss, and market volatility. Always do your own research 
and consider consulting with a financial advisor before making investment decisions.
""")
