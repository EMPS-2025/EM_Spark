#presenters/ai_insights.py

"""
AI-powered insights generation using OpenAI API.
Optimized for minimal token usage.
"""
from typing import List, Dict, Any, Optional
from openai import OpenAI
import json

class AIInsightsGenerator:
    """Generate market insights using OpenAI with token optimization."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize AI insights generator.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.model = model

    def generate_insights(
        self,
        market_data: Dict[str, Dict[str, Any]],
        derivative_data: List[Dict],
        comparison_data: Optional[Dict] = None,
        max_insights: int = 4
    ) -> List[str]:
        """
        Generate market insights using OpenAI.

        Args:
            market_data: Current market data (DAM, GDAM, RTM)
            derivative_data: Futures market data
            comparison_data: YoY comparison data (optional)
            max_insights: Maximum number of insights

        Returns:
            List of insight strings
        """
        if not self.client:
            return self._fallback_insights(market_data, derivative_data, comparison_data)

        try:
            # Prepare compact data summary (minimize tokens)
            summary = self._prepare_data_summary(market_data, derivative_data, comparison_data)

            # Enhanced prompt for actual insights
            system_prompt = f"""You are an expert Indian energy market analyst. Generate EXACTLY {max_insights} actionable market insights.

Requirements:
- Each insight must be 12-20 words
- Focus on: price trends, arbitrage opportunities, demand patterns, volatility, forward guidance
- Use Indian energy market terminology
- Be specific with numbers and percentages
- Provide trading/hedging recommendations where applicable

DO NOT just summarize data. Provide forward-looking analysis."""

            user_prompt = f"""Market Data Summary:
{json.dumps(summary, indent=2)}

Generate {max_insights} strategic insights as a JSON object with key "insights" containing an array of strings.

Example format:
{{"insights": ["DAM prices trending 15% above GDAM, suggesting renewable arbitrage opportunity", "RTM volatility indicates grid uncertainty"]}}"""

            # Call OpenAI with enhanced prompt - FIXED PARAMETER
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                #temperature=0.5,
                #max_completion_tokens=300,  # FIXED: Changed from max_tokens
                response_format={"type": "json_object"}
            )

            # Parse response
            content = response.choices[0].message.content
            result = json.loads(content)

            # Extract insights (handle different response formats)
            insights = result.get('insights', result.get('items', []))

            # Ensure we return exactly max_insights
            if isinstance(insights, list) and len(insights) > 0:
                return insights[:max_insights]
            else:
                return self._fallback_insights(market_data, derivative_data, comparison_data)

        except Exception as e:
            print(f"⚠️ AI insights generation failed: {e}")
            return self._fallback_insights(market_data, derivative_data, comparison_data)

    def _prepare_data_summary(
        self,
        market_data: Dict[str, Dict],
        derivative_data: List[Dict],
        comparison_data: Optional[Dict]
    ) -> Dict:
        """
        Prepare compact data summary for AI processing.
        """
        summary = {}

        # Market prices and volumes
        for market, data in market_data.items():
            if data:
                summary[market] = {
                    "price": round(data.get('twap', 0), 3),
                    "volume_gwh": round(data.get('total_volume_gwh', 0), 1)
                }

        # Derivatives
        if derivative_data:
            summary["futures"] = []
            for deriv in derivative_data[:2]:  # Limit to 2 contracts
                contract_month = deriv.get('contract_month')
                # FIX: Convert date to string
                if hasattr(contract_month, 'strftime'):
                    contract_month = contract_month.strftime('%Y-%m')
                summary["futures"].append({
                    "contract": str('contract_month'),
                    "price": round(float(deriv.get('close_price_rs_per_mwh', 0) or 0) / 1000.0, 3)
                })

        # YoY comparison
        if comparison_data:
            summary["yoy"] = {}
            for market in ["DAM", "GDAM"]:
                curr = comparison_data.get('current', {}).get(market, {})
                prev = comparison_data.get('previous', {}).get(market, {})

                curr_price = curr.get('twap', 0)
                prev_price = prev.get('twap', 0)

                if prev_price > 0:
                    change_pct = round(((curr_price - prev_price) / prev_price) * 100, 1)
                    summary["yoy"][market] = {
                        "price_change_pct": change_pct,
                        "volume_change_pct": round(
                            ((curr.get('total_volume_gwh', 0) - prev.get('total_volume_gwh', 0)) / 
                             prev.get('total_volume_gwh', 1)) * 100, 1
                        ) if prev.get('total_volume_gwh', 0) > 0 else 0
                    }

        return summary

    def _fallback_insights(
        self, 
        market_data: Dict[str, Dict],
        derivative_data: List[Dict] = None,
        comparison_data: Dict = None
    ) -> List[str]:
        """
        Generate rule-based insights when AI is unavailable - ENHANCED VERSION.
        """
        insights = []

        # Price comparison insights
        dam = market_data.get('DAM', {})
        gdam = market_data.get('GDAM', {})
        rtm = market_data.get('RTM', {})

        if dam and gdam:
            dam_price = dam.get('twap', 0)
            gdam_price = gdam.get('twap', 0)
            if dam_price > 0 and gdam_price > 0:
                diff_pct = ((dam_price - gdam_price) / gdam_price) * 100
                if abs(diff_pct) > 3:
                    direction = "premium" if diff_pct > 0 else "discount"
                    opportunity = "renewable arbitrage" if diff_pct < 0 else "conventional power preference"
                    insights.append(f"DAM trading at {abs(diff_pct):.1f}% {direction} to GDAM, indicating {opportunity} opportunity")

        # Volume trends
        if comparison_data:
            for market in ['DAM', 'GDAM']:
                curr = comparison_data.get('current', {}).get(market, {})
                prev = comparison_data.get('previous', {}).get(market, {})
                curr_vol = curr.get('total_volume_gwh', 0)
                prev_vol = prev.get('total_volume_gwh', 0)
                if prev_vol > 0:
                    vol_change = ((curr_vol - prev_vol) / prev_vol) * 100
                    if abs(vol_change) > 10:
                        trend = "surge" if vol_change > 0 else "decline"
                        insights.append(f"{market} volume shows {abs(vol_change):.1f}% YoY {trend}, signaling shifting market dynamics")

        # Derivative market insights
        if derivative_data and len(derivative_data) > 0:
            spot_dam = dam.get('twap', 0) if dam else 0
            futures_price = 0
            try:
                futures_price = float(derivative_data[0].get('close_price_rs_per_mwh', 0) or 0) / 1000.0
            except:
                pass

            if spot_dam > 0 and futures_price > 0:
                forward_premium = ((futures_price - spot_dam) / spot_dam) * 100
                if abs(forward_premium) > 2:
                    direction = "contango" if forward_premium > 0 else "backwardation"
                    insights.append(f"Futures trading in {direction} with {abs(forward_premium):.1f}% spread to spot, indicating forward price expectations")

        # RTM volatility
        if rtm:
            rtm_price = rtm.get('twap', 0)
            if dam:
                dam_price = dam.get('twap', 0)
                if dam_price > 0:
                    rtm_deviation = ((rtm_price - dam_price) / dam_price) * 100
                    if abs(rtm_deviation) > 5:
                        insights.append(f"RTM showing {abs(rtm_deviation):.1f}% deviation from DAM, suggesting heightened intraday volatility")

        # Ensure minimum insights
        if len(insights) < 2:
            if dam:
                insights.append(f"DAM clearing at ₹{dam.get('twap', 0):.2f}/kWh with {dam.get('total_volume_gwh', 0):.1f} GWh traded volume")
            if gdam:
                insights.append(f"Green energy market active at ₹{gdam.get('twap', 0):.2f}/kWh, reflecting renewable capacity participation")

        return insights[:4]


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTION (Used by app.py)
# ═══════════════════════════════════════════════════════════

def generate_ai_insights(
    api_key: str,
    market_data: Dict[str, Dict],
    derivative_data: List[Dict] = None,
    comparison_data: Dict = None,
    model: str = "gpt-4o-mini",
    max_insights: int = 4
) -> List[str]:
    """
    Convenience function to generate insights.

    Args:
        api_key: OpenAI API key
        market_data: Dictionary with DAM, GDAM, RTM data
        derivative_data: List of derivative contracts
        comparison_data: YoY comparison data
        model: OpenAI model to use
        max_insights: Number of insights to generate

    Returns:
        List of insight strings
    """
    generator = AIInsightsGenerator(api_key=api_key, model=model)
    return generator.generate_insights(
        market_data=market_data,
        derivative_data=derivative_data or [],
        comparison_data=comparison_data,
        max_insights=max_insights
    )