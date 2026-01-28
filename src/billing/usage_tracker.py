"""Usage tracking and plan-based rate limiting for app generation."""
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio


@dataclass
class PlanLimits:
    """Defines limits for each subscription plan."""
    generations_per_month: int
    generations_per_day: int
    max_concurrent: int = 1


# Plan configurations
PLAN_LIMITS: Dict[str, PlanLimits] = {
    "free": PlanLimits(generations_per_month=1, generations_per_day=1, max_concurrent=1),
    "starter": PlanLimits(generations_per_month=3, generations_per_day=2, max_concurrent=1),
    "pro": PlanLimits(generations_per_month=10, generations_per_day=5, max_concurrent=2),
    "business": PlanLimits(generations_per_month=999999, generations_per_day=50, max_concurrent=5),
}

# One-time purchase allowances
ONE_TIME_GENERATIONS = {
    "single_app": 1,
    "app_deploy": 1,
    "full_launch": 1,
}


@dataclass
class UserUsage:
    """Tracks usage for a single user."""
    user_id: str
    plan: str = "free"
    generations_this_month: int = 0
    generations_today: int = 0
    month_reset: datetime = field(default_factory=lambda: datetime.now().replace(day=1))
    day_reset: datetime = field(default_factory=datetime.now)
    one_time_credits: int = 0
    active_generations: int = 0


class UsageTracker:
    """Tracks and enforces usage limits per user."""
    
    def __init__(self):
        self._usage: Dict[str, UserUsage] = {}
        self._locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    
    def _get_or_create_usage(self, user_id: str, plan: str = "free") -> UserUsage:
        """Get or create usage record for user."""
        if user_id not in self._usage:
            self._usage[user_id] = UserUsage(user_id=user_id, plan=plan)
        return self._usage[user_id]
    
    def _reset_if_needed(self, usage: UserUsage) -> None:
        """Reset counters if time period has passed."""
        now = datetime.now()
        
        # Reset monthly counter
        if now.month != usage.month_reset.month or now.year != usage.month_reset.year:
            usage.generations_this_month = 0
            usage.month_reset = now.replace(day=1)
        
        # Reset daily counter
        if now.date() != usage.day_reset.date():
            usage.generations_today = 0
            usage.day_reset = now
    
    async def check_can_generate(self, user_id: str, plan: str = "free") -> tuple[bool, str]:
        """Check if user can generate an app.
        
        Returns:
            (can_generate, reason) tuple
        """
        async with self._locks[user_id]:
            usage = self._get_or_create_usage(user_id, plan)
            usage.plan = plan  # Update plan in case it changed
            self._reset_if_needed(usage)
            
            limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
            
            # Check concurrent limit
            if usage.active_generations >= limits.max_concurrent:
                return False, f"Maximum concurrent generations ({limits.max_concurrent}) reached. Please wait for current generation to complete."
            
            # Check if user has one-time credits
            if usage.one_time_credits > 0:
                return True, "Using one-time credit"
            
            # Check monthly limit
            if usage.generations_this_month >= limits.generations_per_month:
                return False, f"Monthly generation limit ({limits.generations_per_month}) reached. Upgrade your plan or wait until next month."
            
            # Check daily limit
            if usage.generations_today >= limits.generations_per_day:
                return False, f"Daily generation limit ({limits.generations_per_day}) reached. Try again tomorrow."
            
            return True, "OK"
    
    async def start_generation(self, user_id: str, plan: str = "free") -> bool:
        """Mark start of generation, increment counters.
        
        Returns:
            True if generation started, False if limit exceeded
        """
        can_generate, reason = await self.check_can_generate(user_id, plan)
        if not can_generate:
            return False
        
        async with self._locks[user_id]:
            usage = self._get_or_create_usage(user_id, plan)
            
            # Use one-time credit if available
            if usage.one_time_credits > 0:
                usage.one_time_credits -= 1
            else:
                usage.generations_this_month += 1
                usage.generations_today += 1
            
            usage.active_generations += 1
            return True
    
    async def end_generation(self, user_id: str) -> None:
        """Mark end of generation."""
        async with self._locks[user_id]:
            if user_id in self._usage:
                self._usage[user_id].active_generations = max(0, self._usage[user_id].active_generations - 1)
    
    async def add_one_time_credits(self, user_id: str, credits: int = 1) -> None:
        """Add one-time generation credits to user."""
        async with self._locks[user_id]:
            usage = self._get_or_create_usage(user_id)
            usage.one_time_credits += credits
    
    async def get_usage_stats(self, user_id: str, plan: str = "free") -> Dict:
        """Get current usage statistics for user."""
        async with self._locks[user_id]:
            usage = self._get_or_create_usage(user_id, plan)
            self._reset_if_needed(usage)
            limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
            
            return {
                "plan": plan,
                "generations_this_month": usage.generations_this_month,
                "generations_today": usage.generations_today,
                "monthly_limit": limits.generations_per_month,
                "daily_limit": limits.generations_per_day,
                "one_time_credits": usage.one_time_credits,
                "active_generations": usage.active_generations,
                "monthly_remaining": max(0, limits.generations_per_month - usage.generations_this_month),
                "daily_remaining": max(0, limits.generations_per_day - usage.generations_today),
            }


# Global usage tracker instance
usage_tracker = UsageTracker()
