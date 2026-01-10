
from typing import Dict
from ..models import DeploymentConfig, CostEstimate

class CostEstimator:
    """
    Estimates monthly costs for deployment configurations.
    """
    
    def estimate(self, config: DeploymentConfig) -> CostEstimate:
        """
        Provide a rough estimate based on provider and resource sizing.
        """
        if config.provider == "vercel":
            # Vercel Free Tier assumption or Pro ($20)
            return CostEstimate(
                provider=config.provider,
                total_monthly=20.0,
                breakdown={"pro_plan": 20.0},
                currency="USD"
            )
            
        elif config.provider == "render":
             # Render: Web ($7) + Worker ($7) + DB ($7) + Redis ($3)
             return CostEstimate(
                provider=config.provider,
                total_monthly=24.0,
                breakdown={
                    "web_service": 7.0,
                    "worker": 7.0,
                    "postgres_managed": 7.0,
                    "redis_managed": 3.0
                },
                currency="USD"
            )
            
        return CostEstimate(
            provider=config.provider,
            total_monthly=0.0,
            breakdown={}, 
            currency="USD"
        )
