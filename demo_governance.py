#!/usr/bin/env python3
"""
Live Demo: Organizational Intelligence Framework

This script demonstrates the governance orchestrator with rival agents:
- 3 rival planners debating strategies
- 5 rival critics reviewing code
- Full separation of powers
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

# Import the governance orchestrator
from src.agents.governance_orchestrator import GovernanceOrchestrator
from src.agents.base import LLMProvider


async def run_demo():
    """Run a live demonstration of the governance orchestrator."""
    
    print("="*80)
    print("ORGANIZATIONAL INTELLIGENCE FRAMEWORK - LIVE DEMO")
    print("="*80)
    print()
    
    # Initialize LLM provider
    print("[1] Initializing LLM Provider...")
    llm = LLMProvider()
    
    # Initialize governance orchestrator
    print("[2] Initializing Governance Orchestrator...")
    print("    - Legislative Branch: 3 rival planners")
    print("    - Judicial Branch: 5 rival critics")
    print("    - Executive Branch: Controlled execution")
    orchestrator = GovernanceOrchestrator(llm)
    print("    ✓ All branches initialized")
    print()
    
    # Define a test requirement
    requirements = """
    Build a simple REST API for a todo list application with the following features:
    - Create, read, update, and delete todos
    - Each todo has a title, description, and completion status
    - Basic authentication with username/password
    - Store data in SQLite database
    - Use FastAPI framework
    """
    
    print("[3] Test Requirements:")
    print("    " + requirements.replace("\n", "\n    "))
    print()
    
    print("="*80)
    print("STARTING GOVERNANCE PROCESS")
    print("="*80)
    print()
    
    # Track start time
    start_time = datetime.now()
    
    try:
        # Run the governance orchestrator
        print("[LEGISLATIVE PHASE] Gathering proposals from rival planners...")
        print("    → Conservative Planner: Proposing risk-averse strategy...")
        print("    → Innovative Planner: Proposing modern approach...")
        print("    → Pragmatic Planner: Proposing balanced solution...")
        print()
        
        result = await orchestrator.generate_app(
            requirements=requirements,
            context={"framework": "FastAPI", "database": "SQLite"}
        )
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        print("\n" + "="*80)
        print("GOVERNANCE ORCHESTRATOR - RESULTS")
        print("="*80)
        print()
        
        # Display governance metadata
        if "governance" in result.metadata:
            gov_data = result.metadata["governance"]
            
            print("[SESSION INFORMATION]")
            print(f"  Session ID: {gov_data.get('session_id', 'N/A')}")
            print(f"  Review ID: {gov_data.get('review_id', 'N/A')}")
            print(f"  Iterations: {gov_data.get('iterations', 'N/A')}")
            print(f"  Execution Time: {execution_time:.2f}s")
            print()
            
            print("[PLANNERS CONSULTED]")
            planners = gov_data.get('planners_consulted', [])
            for planner in planners:
                print(f"  ✓ {planner.capitalize()} Planner")
            print()
            
            print("[CRITICS CONSULTED]")
            critics = gov_data.get('critics_consulted', [])
            for critic in critics:
                print(f"  ✓ {critic.capitalize()} Critic")
            print()
            
            print("[CONSENSUS]")
            consensus = gov_data.get('consensus_score', 0)
            print(f"  Score: {consensus:.1%}")
            print(f"  Status: {'High' if consensus >= 0.7 else 'Moderate' if consensus >= 0.5 else 'Low'} consensus")
            print()
            
            # Show synthesis contributions
            if 'synthesis_contributions' in gov_data:
                print("[SYNTHESIS CONTRIBUTIONS]")
                contributions = gov_data['synthesis_contributions']
                for planner, items in contributions.items():
                    print(f"  {planner.capitalize()}:")
                    for item in items[:3]:  # Show first 3
                        print(f"    - {item}")
                print()
        
        # Display statistics
        print("[ORCHESTRATOR STATISTICS]")
        stats = orchestrator.get_stats()
        print(f"  Plans Proposed: {stats['plans_proposed']}")
        print(f"  Plans Synthesized: {stats['plans_synthesized']}")
        print(f"  Reviews Conducted: {stats['reviews_conducted']}")
        print(f"  Vetoes Issued: {stats['vetoes_issued']}")
        print(f"  Revisions Requested: {stats['revisions_requested']}")
        print(f"  Executions Completed: {stats['executions_completed']}")
        print()
        
        # Display generated files
        print("[GENERATED FILES]")
        for file in result.files:
            print(f"  ✓ {file.filename} ({len(file.content)} bytes)")
        print()
        
        # Save results
        output_dir = Path("governance_demo_results")
        output_dir.mkdir(exist_ok=True)
        
        # Save debate log if available
        if gov_data.get('session_id'):
            debate_log = await orchestrator.get_debate_log(gov_data['session_id'])
            if debate_log:
                with open(output_dir / "debate_log.json", "w") as f:
                    json.dump(debate_log, f, indent=2)
                print("[SAVED] Debate log → governance_demo_results/debate_log.json")
        
        # Save review details if available
        if gov_data.get('review_id'):
            review_details = await orchestrator.get_review_details(gov_data['review_id'])
            if review_details:
                with open(output_dir / "judicial_review.json", "w") as f:
                    json.dump(review_details, f, indent=2)
                print("[SAVED] Judicial review → governance_demo_results/judicial_review.json")
        
        # Save generated code
        for file in result.files:
            file_path = output_dir / file.filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w") as f:
                f.write(file.content)
        print(f"[SAVED] Generated code → governance_demo_results/")
        
        # Save full metadata
        with open(output_dir / "metadata.json", "w") as f:
            json.dump(result.metadata, f, indent=2, default=str)
        print("[SAVED] Full metadata → governance_demo_results/metadata.json")
        print()
        
        print("="*80)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*80)
        print()
        print("The Organizational Intelligence framework successfully:")
        print("  1. Coordinated 3 rival planners with different philosophies")
        print("  2. Synthesized their proposals into an optimal plan")
        print("  3. Executed the plan with oversight")
        print("  4. Reviewed the code through 5 specialized critics")
        print("  5. Built consensus through constructive rivalry")
        print()
        print("Check the 'governance_demo_results' directory for detailed logs.")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nStarting Organizational Intelligence Demo...\n")
    success = asyncio.run(run_demo())
    exit(0 if success else 1)
