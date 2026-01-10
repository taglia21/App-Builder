"""
Quality Assurance Engine.
Runs post-generation checks and formatting on the codebase.
"""

import os
import subprocess
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class QAReport(BaseModel):
    """Report on Quality Assurance execution."""
    backend_formatted: bool = False
    frontend_formatted: bool = False
    issues: List[str] = Field(default_factory=list)

class QualityAssuranceEngine:
    """
    Ensures generated code meets quality standards.
    Runs formatters (Black, Isort, Prettier) and static analysis.
    """
    
    def __init__(self):
        self.black_path = shutil.which("black")
        self.isort_path = shutil.which("isort")
        # We assume npx is available in path if node is installed
        self.npx_path = shutil.which("npx") or "npx" 

    def run_checks(self, codebase_path: str) -> QAReport:
        """
        Run all QA checks on the generated codebase.
        
        Args:
            codebase_path: Absolute path to the generated project root.
            
        Returns:
            QAReport with status of checks.
        """
        path = Path(codebase_path)
        if not path.exists():
            logger.error(f"Codebase path does not exist: {path}")
            return QAReport(issues=["Codebase path not found"])
            
        logger.info(f"Starting Quality Assurance on: {path}")
        report = QAReport()
        
        # 1. Backend Formatting
        backend_path = path / "backend"
        if backend_path.exists():
            report.backend_formatted = self._format_backend(backend_path)
        else:
            logger.warning("No backend directory found to format.")
            
        # 2. Frontend Formatting
        frontend_path = path / "frontend"
        if frontend_path.exists():
            report.frontend_formatted = self._format_frontend(frontend_path)
        else:
            logger.warning("No frontend directory found to format.")
            
        return report

    def _format_backend(self, backend_path: Path) -> bool:
        """Run Black and Isort on backend code."""
        success = True
        
        # Run isort
        if self.isort_path:
            try:
                subprocess.run(
                    [self.isort_path, ".", "--profile", "black"], 
                    cwd=str(backend_path), 
                    check=True, 
                    capture_output=True
                )
                logger.info("✓ Backend: Imports sorted (isort)")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Isort failed: {e}")
                success = False
            except Exception as e:
                logger.warning(f"Error running isort: {e}")
                success = False
        else:
            logger.warning("isort not found in path")

        # Run black
        if self.black_path:
            try:
                subprocess.run(
                    [self.black_path, "."], 
                    cwd=str(backend_path), 
                    check=True, 
                    capture_output=True,
                    timeout=60  # Prevent hanging
                )
                logger.info("✓ Backend: Code formatted (black)")
            except subprocess.TimeoutExpired:
                logger.warning("Black formatting timed out")
                success = False
            except subprocess.CalledProcessError as e:
                logger.warning(f"Black failed: {e}")
                success = False
            except Exception as e:
                logger.warning(f"Error running black: {e}")
                success = False
        else:
             logger.warning("black not found in path")
             
        return success

    def _format_frontend(self, frontend_path: Path) -> bool:
        """Run Prettier on frontend code."""
        # Check if npx works (simple check)
        try:
            # We use shell=True on Windows for npx sometimes, but try without first
            subprocess.run(["npx", "--version"], capture_output=True, shell=True)
        except Exception:
            logger.warning("npx not available, skipping frontend formatting")
            return False

        try:
            # Running prettier via npx
            # "npx prettier --write ."
            logger.info("Running Prettier on frontend (this may take a moment)...")
            
            # Set CI=true to prevent interactive prompts
            env = os.environ.copy()
            env["CI"] = "true"
            
            subprocess.run(
                ["npx", "--yes", "prettier", "--write", "."], 
                cwd=str(frontend_path), 
                check=True, 
                shell=True, # Often needed for npx on Windows
                capture_output=True,
                timeout=120, # Prettier can be slow on first run
                env=env
            )
            logger.info("✓ Frontend: Code formatted (prettier)")
            return True
        except subprocess.TimeoutExpired:
            logger.warning("Prettier formatting timed out")
            return False
        except subprocess.CalledProcessError as e:
            logger.warning(f"Prettier failed: {e}")
            return False
        except Exception as e:
            logger.warning(f"Error running prettier: {e}")
            return False
