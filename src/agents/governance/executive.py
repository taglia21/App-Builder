"""
Executive Branch - Execution and implementation authority.

Part of the Organizational Intelligence governance model implementing
the separation of powers:
- Executive: Executes approved plans
- Legislative: Proposes and debates plans  
- Judicial: Reviews and can veto decisions

The Executive branch is responsible for:
1. Executing approved plans from the Legislative
2. Managing the execution state and progress
3. Handling errors and escalating to Judicial when needed
4. Reporting execution status to all branches
"""

from typing import Any, Dict, List, Optional, Callable
import logging
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from ..messages import (
    ExecutionPlan, GeneratedCode, OrchestrationState, TaskStatus
)

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Status of execution."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    VETOED = "vetoed"


@dataclass
class ExecutionContext:
    """Context for execution including state and permissions."""
    plan: ExecutionPlan
    approved_by: str  # Which branch/process approved
    constraints: Dict[str, Any] = field(default_factory=dict)
    veto_callback: Optional[Callable] = None
    status: ExecutionStatus = ExecutionStatus.PENDING
    current_step: int = 0
    execution_log: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass  
class ExecutionResult:
    """Result of plan execution."""
    success: bool
    generated_code: Optional[GeneratedCode]
    execution_log: List[Dict[str, Any]]
    errors: List[str]
    vetoed: bool = False
    veto_reason: Optional[str] = None
    execution_time_seconds: float = 0.0


class ExecutiveBranch:
    """
    The Executive Branch executes approved plans.
    
    Responsibilities:
    - Execute plans that have been approved by Legislative and Judicial
    - Manage execution state and handle failures
    - Respect veto authority from Judicial branch
    - Report progress and issues transparently
    
    The Executive cannot:
    - Execute plans without approval
    - Override Judicial vetoes
    - Modify plans during execution (must request from Legislative)
    """
    
    def __init__(
        self,
        code_writer,
        judicial_callback: Optional[Callable] = None
    ):
        self.code_writer = code_writer
        self.judicial_callback = judicial_callback
        self._active_executions: Dict[str, ExecutionContext] = {}
        self._execution_history: List[ExecutionResult] = []
    
    async def execute_plan(
        self,
        plan: ExecutionPlan,
        requirements: str,
        approval_token: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute an approved plan."""
        logger.info(f"Executive: Beginning execution of plan {plan.plan_id}")
        
        # Create execution context
        exec_context = ExecutionContext(
            plan=plan,
            approved_by=approval_token,
            constraints=context or {},
            veto_callback=self.judicial_callback,
            status=ExecutionStatus.IN_PROGRESS,
            started_at=datetime.now()
        )
        
        self._active_executions[plan.plan_id] = exec_context
        execution_log = []
        errors = []
        generated_code = None
        
        try:
            # Execute each step in order
            for i, step in enumerate(plan.steps):
                exec_context.current_step = i + 1
                
                # Log step start
                step_log = {
                    "step_id": step.step_id,
                    "step_name": step.name,
                    "status": "started",
                    "timestamp": datetime.now().isoformat()
                }
                execution_log.append(step_log)
                
                logger.info(f"Executive: Executing step {i+1}/{len(plan.steps)}: {step.name}")
                
                # Check for veto before each step
                if self.judicial_callback:
                    veto_check = await self._check_for_veto(exec_context, step)
                    if veto_check:
                        exec_context.status = ExecutionStatus.VETOED
                        return ExecutionResult(
                            success=False,
                            generated_code=None,
                            execution_log=execution_log,
                            errors=[],
                            vetoed=True,
                            veto_reason=veto_check
                        )
                
                # Execute the step
                try:
                    step_result = await self._execute_step(step, requirements, context)
                    step_log["status"] = "completed"
                    step_log["result"] = step_result
                    
                    # If this step generates code, capture it
                    if step_result and hasattr(step_result, 'files'):
                        generated_code = step_result
                        
                except Exception as e:
                    step_log["status"] = "failed"
                    step_log["error"] = str(e)
                    errors.append(f"Step {step.name}: {str(e)}")
                    
                    # Decide if we should continue or abort
                    if self._is_critical_failure(step, e):
                        exec_context.status = ExecutionStatus.FAILED
                        logger.error(f"Executive: Critical failure at step {step.name}: {e}")
                        break
            
            # Execution complete
            exec_context.completed_at = datetime.now()
            exec_context.status = ExecutionStatus.COMPLETED if not errors else ExecutionStatus.FAILED
            exec_context.execution_log = execution_log
            
            execution_time = (exec_context.completed_at - exec_context.started_at).total_seconds()
            
            result = ExecutionResult(
                success=len(errors) == 0,
                generated_code=generated_code,
                execution_log=execution_log,
                errors=errors,
                execution_time_seconds=execution_time
            )
            
            self._execution_history.append(result)
            return result
            
        finally:
            # Clean up active execution
            if plan.plan_id in self._active_executions:
                del self._active_executions[plan.plan_id]
    
    async def _execute_step(
        self,
        step,
        requirements: str,
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Execute a single step of the plan."""
        # For code generation steps, use the code writer
        if "code" in step.name.lower() or "implement" in step.name.lower():
            return await self.code_writer.write(requirements, context)
        
        # For other steps, simulate execution
        await asyncio.sleep(0.1)  # Simulate work
        return {"status": "completed", "step": step.name}
    
    async def _check_for_veto(
        self,
        context: ExecutionContext,
        step
    ) -> Optional[str]:
        """Check with Judicial branch for veto."""
        if not self.judicial_callback:
            return None
        
        try:
            veto_result = await self.judicial_callback(
                action="pre_step_check",
                step=step,
                context=context
            )
            if veto_result and veto_result.get("vetoed"):
                return veto_result.get("reason", "Judicial veto")
        except Exception as e:
            logger.warning(f"Executive: Veto check failed: {e}")
        
        return None
    
    def _is_critical_failure(self, step, error: Exception) -> bool:
        """Determine if a failure is critical enough to abort."""
        # Critical steps that should abort execution
        critical_keywords = ["security", "auth", "database", "critical"]
        step_name_lower = step.name.lower()
        
        return any(kw in step_name_lower for kw in critical_keywords)
    
    def get_execution_status(self, plan_id: str) -> Optional[ExecutionContext]:
        """Get the current status of an execution."""
        return self._active_executions.get(plan_id)
    
    def get_execution_history(self) -> List[ExecutionResult]:
        """Get history of all executions."""
        return self._execution_history
    
    async def pause_execution(self, plan_id: str) -> bool:
        """Pause an active execution."""
        if plan_id in self._active_executions:
            self._active_executions[plan_id].status = ExecutionStatus.PAUSED
            logger.info(f"Executive: Paused execution of {plan_id}")
            return True
        return False
    
    async def resume_execution(self, plan_id: str) -> bool:
        """Resume a paused execution."""
        if plan_id in self._active_executions:
            ctx = self._active_executions[plan_id]
            if ctx.status == ExecutionStatus.PAUSED:
                ctx.status = ExecutionStatus.IN_PROGRESS
                logger.info(f"Executive: Resumed execution of {plan_id}")
                return True
        return False
