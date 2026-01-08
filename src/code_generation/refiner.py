"""Conversational Code Refiner Engine."""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.llm.client import get_llm_client

logger = logging.getLogger(__name__)

class CodeRefiner:
    """Refines code based on natural language instructions."""
    
    def __init__(self):
        self.client = get_llm_client("auto")
    
    def refine(self, project_path: str, instruction: str) -> Dict[str, Any]:
        """Apply changes to project based on instruction."""
        project_dir = Path(project_path)
        
        if not project_dir.exists():
            return {"success": False, "error": "Project not found"}
            
        # 1. Map the project
        file_map = self._map_project(project_dir)
        file_list = "\n".join(file_map.keys())
        
        # 2. Identify target file
        try:
            target_path = self._identify_target(instruction, file_list)
            if not target_path:
                return {"success": False, "error": "Could not identify relevant file"}
                
            full_path = project_dir / target_path
            if not full_path.exists():
                return {"success": False, "error": f"Target file {target_path} not found"}
                
            # 3. Read content
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # 4. Apply changes
            new_content = self._apply_changes(content, instruction, target_path)
            
            # 5. Write back
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(new_content)
                
            return {
                "success": True,
                "file": target_path,
                "message": f"Updated {target_path}"
            }
            
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            return {"success": False, "error": str(e)}

    def _map_project(self, root: Path) -> Dict[str, str]:
        """Map all text files in project."""
        file_map = {}
        for path in root.rglob("*"):
            if path.is_file() and not any(p in str(path) for p in [".git", "__pycache__", "node_modules", ".next", "venv"]):
                try:
                    rel_path = path.relative_to(root)
                    file_map[str(rel_path)] = str(path)
                except Exception:
                    continue
        return file_map

    def _identify_target(self, instruction: str, file_list: str) -> Optional[str]:
        """Ask LLM which file needs modification."""
        prompt = f"""You are a senior software architect.
User Request: "{instruction}"

Project Files:
{file_list}

Identify the SINGLE file that needs to be modified to fulfill this request.
Return ONLY the file path. Do not return JSON. Do not explain.
If no existing file works (needs new file), return "NEW: <filename>".
If multiple files need changes, return the most critical one.
"""
        response = self.client.complete(prompt)
        path = response.content.strip().replace("`", "").strip()
        
        # Simple cleanup
        if path.startswith("'") or path.startswith('"'):
            path = path[1:-1]
            
        return path

    def _apply_changes(self, content: str, instruction: str, filename: str) -> str:
        """Ask LLM to rewrite the file."""
        prompt = f"""You are an expert developer.
Task: Modify '{filename}' based on this request: "{instruction}"

Original Code:
```
{content}
```

Return the COMPLETE, UPDATED code for this file. 
- Do not use diffs or placeholders.
- Maintain existing style and imports.
- Make the requested change safely.
- Return ONLY the code, inside markdown code blocks.
"""
        response = self.client.complete(prompt)
        
        # Extract code from markdown
        content = response.content
        if "```" in content:
            # simple extraction
            parts = content.split("```")
            # usually the code is in the second part (index 1), possibly with a language tag
            code_block = parts[1]
            if "\n" in code_block:
                code_block = code_block.split("\n", 1)[1] # remove language tag
            return code_block.strip()
            
        return content.strip()
