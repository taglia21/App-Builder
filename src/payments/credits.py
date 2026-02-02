"""
Credit Management System

Tracks usage credits for app generation and other metered features.
"""

from dataclasses import dataclass
from datetime import timezone, datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CreditType(str, Enum):
    """Types of credits."""
    APP_GENERATION = "app_generation"
    DEPLOYMENT = "deployment"
    AI_ENHANCEMENT = "ai_enhancement"
    BUSINESS_FORMATION = "business_formation"
    DOMAIN_REGISTRATION = "domain_registration"


class TransactionType(str, Enum):
    """Credit transaction types."""
    PURCHASE = "purchase"
    SUBSCRIPTION_GRANT = "subscription_grant"
    USAGE = "usage"
    REFUND = "refund"
    BONUS = "bonus"
    EXPIRATION = "expiration"
    ADJUSTMENT = "adjustment"


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough credits."""
    
    def __init__(self, required: int, available: int, credit_type: CreditType):
        self.required = required
        self.available = available
        self.credit_type = credit_type
        super().__init__(
            f"Insufficient credits: required {required} {credit_type.value}, "
            f"available {available}"
        )


@dataclass
class CreditTransaction:
    """Record of a credit transaction."""
    id: str
    user_id: str
    credit_type: CreditType
    transaction_type: TransactionType
    amount: int  # Positive for additions, negative for usage
    balance_after: int
    description: str
    created_at: datetime
    metadata: Dict[str, Any]
    
    # Optional reference to related entities
    subscription_id: Optional[str] = None
    project_id: Optional[str] = None
    invoice_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "credit_type": self.credit_type.value,
            "transaction_type": self.transaction_type.value,
            "amount": self.amount,
            "balance_after": self.balance_after,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "subscription_id": self.subscription_id,
            "project_id": self.project_id,
            "invoice_id": self.invoice_id,
        }


@dataclass
class CreditBalance:
    """User's credit balance for a specific type."""
    user_id: str
    credit_type: CreditType
    balance: int
    reserved: int  # Credits reserved for in-progress operations
    expires_at: Optional[datetime]
    last_updated: datetime
    
    @property
    def available(self) -> int:
        """Get available (non-reserved) credits."""
        return max(0, self.balance - self.reserved)
    
    @property
    def is_expired(self) -> bool:
        """Check if credits have expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "credit_type": self.credit_type.value,
            "balance": self.balance,
            "reserved": self.reserved,
            "available": self.available,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
            "last_updated": self.last_updated.isoformat(),
        }


# Credit costs for various operations
CREDIT_COSTS: Dict[str, int] = {
    "app_generation_basic": 1,
    "app_generation_pro": 2,
    "app_generation_enterprise": 3,
    "deployment_vercel": 0,  # Free with subscription
    "deployment_render": 0,
    "deployment_aws": 1,
    "ai_enhancement_basic": 1,
    "ai_enhancement_advanced": 3,
    "llc_formation": 10,
    "ein_application": 5,
    "domain_registration": 2,
}


class CreditManager:
    """
    Manages user credits for metered features.
    
    This is a reference implementation - in production, you'd persist
    balances and transactions to your database.
    """
    
    def __init__(self):
        """Initialize credit manager."""
        # In-memory storage for demo purposes
        # In production, use database
        self._balances: Dict[str, Dict[CreditType, CreditBalance]] = {}
        self._transactions: List[CreditTransaction] = []
        self._transaction_counter = 0
    
    def get_balance(
        self,
        user_id: str,
        credit_type: CreditType,
    ) -> CreditBalance:
        """
        Get user's credit balance for a specific type.
        
        Args:
            user_id: User ID
            credit_type: Type of credit
            
        Returns:
            CreditBalance object
        """
        if user_id not in self._balances:
            self._balances[user_id] = {}
        
        if credit_type not in self._balances[user_id]:
            # Create default balance
            self._balances[user_id][credit_type] = CreditBalance(
                user_id=user_id,
                credit_type=credit_type,
                balance=0,
                reserved=0,
                expires_at=None,
                last_updated=datetime.now(timezone.utc),
            )
        
        return self._balances[user_id][credit_type]
    
    def get_all_balances(self, user_id: str) -> Dict[CreditType, CreditBalance]:
        """
        Get all credit balances for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of credit type to balance
        """
        if user_id not in self._balances:
            return {}
        return self._balances[user_id].copy()
    
    def add_credits(
        self,
        user_id: str,
        credit_type: CreditType,
        amount: int,
        transaction_type: TransactionType,
        description: str,
        expires_in_days: Optional[int] = None,
        subscription_id: Optional[str] = None,
        invoice_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CreditTransaction:
        """
        Add credits to a user's balance.
        
        Args:
            user_id: User ID
            credit_type: Type of credit
            amount: Number of credits to add
            transaction_type: Type of transaction
            description: Human-readable description
            expires_in_days: Days until credits expire
            subscription_id: Related subscription
            invoice_id: Related invoice
            metadata: Additional metadata
            
        Returns:
            CreditTransaction record
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        balance = self.get_balance(user_id, credit_type)
        
        # Update balance
        balance.balance += amount
        balance.last_updated = datetime.now(timezone.utc)
        
        if expires_in_days:
            balance.expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        # Create transaction record
        self._transaction_counter += 1
        transaction = CreditTransaction(
            id=f"txn_{self._transaction_counter:08d}",
            user_id=user_id,
            credit_type=credit_type,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=balance.balance,
            description=description,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
            subscription_id=subscription_id,
            invoice_id=invoice_id,
        )
        
        self._transactions.append(transaction)
        
        logger.info(
            f"Added {amount} {credit_type.value} credits to user {user_id}, "
            f"new balance: {balance.balance}"
        )
        
        return transaction
    
    def use_credits(
        self,
        user_id: str,
        credit_type: CreditType,
        amount: int,
        description: str,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CreditTransaction:
        """
        Use credits from a user's balance.
        
        Args:
            user_id: User ID
            credit_type: Type of credit
            amount: Number of credits to use
            description: What the credits are used for
            project_id: Related project
            metadata: Additional metadata
            
        Returns:
            CreditTransaction record
            
        Raises:
            InsufficientCreditsError: If not enough credits
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        balance = self.get_balance(user_id, credit_type)
        
        # Check for expired credits
        if balance.is_expired:
            balance.balance = 0
            balance.expires_at = None
        
        # Check available balance
        if balance.available < amount:
            raise InsufficientCreditsError(
                required=amount,
                available=balance.available,
                credit_type=credit_type,
            )
        
        # Update balance
        balance.balance -= amount
        balance.last_updated = datetime.now(timezone.utc)
        
        # Create transaction record
        self._transaction_counter += 1
        transaction = CreditTransaction(
            id=f"txn_{self._transaction_counter:08d}",
            user_id=user_id,
            credit_type=credit_type,
            transaction_type=TransactionType.USAGE,
            amount=-amount,
            balance_after=balance.balance,
            description=description,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
            project_id=project_id,
        )
        
        self._transactions.append(transaction)
        
        logger.info(
            f"Used {amount} {credit_type.value} credits from user {user_id}, "
            f"remaining: {balance.balance}"
        )
        
        return transaction
    
    def reserve_credits(
        self,
        user_id: str,
        credit_type: CreditType,
        amount: int,
    ) -> bool:
        """
        Reserve credits for an in-progress operation.
        
        Args:
            user_id: User ID
            credit_type: Type of credit
            amount: Number of credits to reserve
            
        Returns:
            True if reservation successful
            
        Raises:
            InsufficientCreditsError: If not enough credits
        """
        balance = self.get_balance(user_id, credit_type)
        
        if balance.available < amount:
            raise InsufficientCreditsError(
                required=amount,
                available=balance.available,
                credit_type=credit_type,
            )
        
        balance.reserved += amount
        balance.last_updated = datetime.now(timezone.utc)
        
        logger.debug(
            f"Reserved {amount} {credit_type.value} credits for user {user_id}"
        )
        
        return True
    
    def release_reservation(
        self,
        user_id: str,
        credit_type: CreditType,
        amount: int,
    ) -> None:
        """
        Release a credit reservation without using.
        
        Args:
            user_id: User ID
            credit_type: Type of credit
            amount: Number of credits to release
        """
        balance = self.get_balance(user_id, credit_type)
        balance.reserved = max(0, balance.reserved - amount)
        balance.last_updated = datetime.now(timezone.utc)
        
        logger.debug(
            f"Released {amount} {credit_type.value} credit reservation for user {user_id}"
        )
    
    def commit_reservation(
        self,
        user_id: str,
        credit_type: CreditType,
        amount: int,
        description: str,
        project_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CreditTransaction:
        """
        Commit a reservation - actually use the reserved credits.
        
        Args:
            user_id: User ID
            credit_type: Type of credit
            amount: Number of credits to commit
            description: What the credits are used for
            project_id: Related project
            metadata: Additional metadata
            
        Returns:
            CreditTransaction record
        """
        balance = self.get_balance(user_id, credit_type)
        
        # Release from reserved
        balance.reserved = max(0, balance.reserved - amount)
        
        # Use from balance
        balance.balance -= amount
        balance.last_updated = datetime.now(timezone.utc)
        
        # Create transaction record
        self._transaction_counter += 1
        transaction = CreditTransaction(
            id=f"txn_{self._transaction_counter:08d}",
            user_id=user_id,
            credit_type=credit_type,
            transaction_type=TransactionType.USAGE,
            amount=-amount,
            balance_after=balance.balance,
            description=description,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
            project_id=project_id,
        )
        
        self._transactions.append(transaction)
        
        logger.info(
            f"Committed {amount} {credit_type.value} credits from user {user_id}"
        )
        
        return transaction
    
    def refund_credits(
        self,
        user_id: str,
        credit_type: CreditType,
        amount: int,
        description: str,
        original_transaction_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> CreditTransaction:
        """
        Refund credits to a user.
        
        Args:
            user_id: User ID
            credit_type: Type of credit
            amount: Number of credits to refund
            description: Reason for refund
            original_transaction_id: ID of original transaction
            metadata: Additional metadata
            
        Returns:
            CreditTransaction record
        """
        balance = self.get_balance(user_id, credit_type)
        
        # Add credits back
        balance.balance += amount
        balance.last_updated = datetime.now(timezone.utc)
        
        # Create transaction record
        self._transaction_counter += 1
        
        meta = metadata or {}
        if original_transaction_id:
            meta["original_transaction_id"] = original_transaction_id
        
        transaction = CreditTransaction(
            id=f"txn_{self._transaction_counter:08d}",
            user_id=user_id,
            credit_type=credit_type,
            transaction_type=TransactionType.REFUND,
            amount=amount,
            balance_after=balance.balance,
            description=description,
            created_at=datetime.now(timezone.utc),
            metadata=meta,
        )
        
        self._transactions.append(transaction)
        
        logger.info(
            f"Refunded {amount} {credit_type.value} credits to user {user_id}"
        )
        
        return transaction
    
    def get_transactions(
        self,
        user_id: str,
        credit_type: Optional[CreditType] = None,
        transaction_type: Optional[TransactionType] = None,
        limit: int = 50,
    ) -> List[CreditTransaction]:
        """
        Get transaction history for a user.
        
        Args:
            user_id: User ID
            credit_type: Filter by credit type
            transaction_type: Filter by transaction type
            limit: Maximum number of results
            
        Returns:
            List of transactions (newest first)
        """
        transactions = [t for t in self._transactions if t.user_id == user_id]
        
        if credit_type:
            transactions = [t for t in transactions if t.credit_type == credit_type]
        
        if transaction_type:
            transactions = [t for t in transactions if t.transaction_type == transaction_type]
        
        # Sort by created_at descending
        transactions.sort(key=lambda t: t.created_at, reverse=True)
        
        return transactions[:limit]
    
    def grant_subscription_credits(
        self,
        user_id: str,
        tier: str,
        subscription_id: Optional[str] = None,
    ) -> List[CreditTransaction]:
        """
        Grant monthly credits based on subscription tier.
        
        Args:
            user_id: User ID
            tier: Subscription tier (free, pro, enterprise)
            subscription_id: Stripe subscription ID
            
        Returns:
            List of credit transactions
        """
        # Define credits per tier
        tier_credits = {
            "free": {CreditType.APP_GENERATION: 1},
            "pro": {CreditType.APP_GENERATION: 5, CreditType.DEPLOYMENT: 5},
            "enterprise": {CreditType.APP_GENERATION: -1, CreditType.DEPLOYMENT: -1},  # Unlimited
        }
        
        credits = tier_credits.get(tier, tier_credits["free"])
        transactions = []
        
        for credit_type, amount in credits.items():
            if amount == -1:
                # Unlimited - set a high number
                amount = 1000
            
            if amount > 0:
                txn = self.add_credits(
                    user_id=user_id,
                    credit_type=credit_type,
                    amount=amount,
                    transaction_type=TransactionType.SUBSCRIPTION_GRANT,
                    description=f"Monthly {tier.title()} subscription credit grant",
                    expires_in_days=30,
                    subscription_id=subscription_id,
                )
                transactions.append(txn)
        
        return transactions
    
    def check_and_use(
        self,
        user_id: str,
        operation: str,
        project_id: Optional[str] = None,
    ) -> CreditTransaction:
        """
        Check if user has enough credits and use them.
        
        Args:
            user_id: User ID
            operation: Operation key (e.g., "app_generation_basic")
            project_id: Related project
            
        Returns:
            CreditTransaction record
            
        Raises:
            InsufficientCreditsError: If not enough credits
            ValueError: If operation not recognized
        """
        if operation not in CREDIT_COSTS:
            raise ValueError(f"Unknown operation: {operation}")
        
        cost = CREDIT_COSTS[operation]
        
        if cost == 0:
            # Free operation, no credits needed
            self._transaction_counter += 1
            return CreditTransaction(
                id=f"txn_{self._transaction_counter:08d}",
                user_id=user_id,
                credit_type=CreditType.APP_GENERATION,
                transaction_type=TransactionType.USAGE,
                amount=0,
                balance_after=self.get_balance(user_id, CreditType.APP_GENERATION).balance,
                description=f"Free operation: {operation}",
                created_at=datetime.now(timezone.utc),
                metadata={"operation": operation},
                project_id=project_id,
            )
        
        # Determine credit type from operation
        credit_type = CreditType.APP_GENERATION
        if "deployment" in operation:
            credit_type = CreditType.DEPLOYMENT
        elif "ai_enhancement" in operation:
            credit_type = CreditType.AI_ENHANCEMENT
        elif "llc" in operation or "ein" in operation:
            credit_type = CreditType.BUSINESS_FORMATION
        elif "domain" in operation:
            credit_type = CreditType.DOMAIN_REGISTRATION
        
        return self.use_credits(
            user_id=user_id,
            credit_type=credit_type,
            amount=cost,
            description=f"Used for: {operation}",
            project_id=project_id,
            metadata={"operation": operation},
        )
