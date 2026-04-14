from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class OpportunityService:
    @staticmethod
    def calculate_score(
        current_price: float,
        previous_price: Optional[float],
        market_avg_price: float,
        is_individual: bool
    ) -> Dict:
        """
        Calculates opportunity score (0-100)
        
        Logic:
        - Price drop vs previous: Up to 40 points
        - Under market average: Up to 40 points
        - Individual owner: 20 points
        """
        score = 0
        reasons = []

        # 1. Price Drop Detection
        if previous_price and current_price < previous_price:
            discount = ((previous_price - current_price) / previous_price) * 100
            if discount >= 5:
                points = min(40, discount * 2) # e.g. 10% drop = 20 points
                score += int(points)
                reasons.append(f"Price dropped by {discount:.1f}%")

        # 2. Market Comparison
        if current_price < market_avg_price:
            infra_value = ((market_avg_price - current_price) / market_avg_price) * 100
            if infra_value >= 10:
                points = min(40, infra_value * 1.5)
                score += int(points)
                reasons.append(f"Infrastructure value: {infra_value:.1f}% below market")

        # 3. Individual Owner (Strong lead for agents)
        if is_individual:
            score += 20
            reasons.append("Listed by individual (Direct contact)")

        return {
            "score": score,
            "reasons": reasons,
            "is_hot": score >= 80,
            "message": "🔥 TOP Opportunity!" if score >= 80 else "Monitoring"
        }
