"""
LLM Council - Multi-model idea generation with peer review
Inspired by Andrej Karpathy's llm-council project
"""

import os
import asyncio
import aiohttp
from typing import List, Dict, Any
from dataclasses import dataclass
import json

@dataclass
class CouncilMember:
    model_id: str
    name: str
    
@dataclass 
class CouncilResponse:
    member: str
    response: str
    scores: Dict[str, float] = None

class LLMCouncil:
    """
    Implements a council of LLMs that:
    1. All generate responses independently
    2. Review and rank each other's responses
    3. Chairman synthesizes final answer
    """
    
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    # Council members - using cost-effective models
    DEFAULT_COUNCIL = [
        CouncilMember("google/gemini-2.0-flash-exp:free", "Gemini"),
        CouncilMember("anthropic/claude-3.5-sonnet", "Claude"),
        CouncilMember("openai/gpt-4o-mini", "GPT-4o"),
        CouncilMember("meta-llama/llama-3.3-70b-instruct", "Llama"),
    ]
    
    # Chairman model
    CHAIRMAN_MODEL = "google/gemini-2.0-flash-exp:free"
    
    def __init__(self, api_key: str = None, council: List[CouncilMember] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY required")
        self.council = council or self.DEFAULT_COUNCIL
        
    async def _call_model(self, model_id: str, messages: List[Dict], session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Make async call to OpenRouter with improved error handling"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ai-startup-generator.app",
            "X-Title": "AI Startup Generator"
        }
        
        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.7
        }
        
        try:
            async with session.post(self.OPENROUTER_URL, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return {"success": True, "content": content}
                else:
                    error_text = await resp.text()
                    try:
                        error_json = json.loads(error_text)
                        # OpenRouter usually returns {"error": {"message": "..."}}
                        error_msg = error_json.get("error", {}).get("message", error_text)
                        # Check for specific codes
                        code = error_json.get("error", {}).get("code")
                        if code == 402: error_msg = "Insufficient Credits (Payment Required)"
                        elif code == 429: error_msg = "Rate Limit Exceeded"
                    except (json.JSONDecodeError, KeyError) as parse_err:
                        error_msg = f"HTTP {resp.status} (parse error: {parse_err})"
                    
                    return {"success": False, "error": f"{model_id}: {error_msg}"}
        except Exception as e:
            return {"success": False, "error": f"{model_id}: {str(e)}"}
    
    async def stage1_generate(self, prompt: str, pain_points: List[str]) -> Dict[str, Any]:
        """Stage 1: Each council member generates ideas independently"""
        
        system_prompt = """You are a startup idea generator. Given market pain points, generate innovative startup ideas.
        
For each idea, provide:
- Name: A catchy startup name
- Problem: The problem it solves
- Solution: How it solves it
- Revenue Model: How it makes money
- TAM: Target market size estimate

Generate 3-5 high-quality startup ideas based on the pain points provided."""

        user_prompt = f"""Based on these market pain points:

{chr(10).join(f'- {pp}' for pp in pain_points[:15])}

Generate innovative startup ideas that address these problems. Be creative and think about underserved markets."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        responses = []
        errors = []
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._call_model(member.model_id, messages, session) 
                for member in self.council
            ]
            results = await asyncio.gather(*tasks)
            
            for member, result in zip(self.council, results):
                if result["success"]:
                    responses.append(CouncilResponse(member=member.name, response=result["content"]))
                else:
                    errors.append(result["error"])
        
        return {"responses": responses, "errors": errors}
    
    async def stage2_review(self, responses: List[CouncilResponse]) -> List[CouncilResponse]:
        """Stage 2: Each member reviews and scores the other responses"""
        
        if not responses:
            return []
            
        review_prompt_template = """You are evaluating startup ideas from different analysts.

Here are the responses from different analysts (anonymized):

{responses}

For each response (A, B, C, D), rate on a scale of 1-10:
- Innovation: How creative and unique are the ideas?
- Feasibility: How practical and achievable?
- Market Fit: How well do they address real pain points?
- Revenue Potential: How viable is the business model?

Provide your ratings in this exact JSON format:
{{
  "A": {{"innovation": X, "feasibility": X, "market_fit": X, "revenue": X, "total": X}},
  "B": {{"innovation": X, "feasibility": X, "market_fit": X, "revenue": X, "total": X}},
  ...
}}

Be objective. It's okay if another analyst's ideas are better than others."""

        # Format responses anonymously
        labels = ['A', 'B', 'C', 'D', 'E', 'F'][:len(responses)]
        formatted = "\n\n".join([
            f"=== Analyst {labels[i]} ===\n{r.response}" 
            for i, r in enumerate(responses)
        ])
        
        review_prompt = review_prompt_template.format(responses=formatted)
        messages = [{"role": "user", "content": review_prompt}]
        
        all_scores = []
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._call_model(member.model_id, messages, session)
                for member in self.council
            ]
            results = await asyncio.gather(*tasks)
            
            for result in results:
                if result["success"]:
                    try:
                        content = result["content"]
                        # Extract JSON from response
                        start = content.find('{')
                        end = content.rfind('}') + 1
                        if start >= 0 and end > start:
                            scores = json.loads(content[start:end])
                            all_scores.append(scores)
                    except (json.JSONDecodeError, KeyError) as e:
                        pass  # Scores extraction failed, continue with other reviewers
        
        # Aggregate scores and normalize to 0-100 scale
        if all_scores:
            for i, response in enumerate(responses):
                if i >= len(labels): break
                label = labels[i]
                totals = []
                for score_set in all_scores:
                    if label in score_set and 'total' in score_set[label]:
                        # Convert from 40-point scale to 100-point scale
                        normalized_score = (score_set[label]['total'] / 40.0) * 100
                        totals.append(normalized_score)
                if totals:
                    response.scores = {"average": sum(totals) / len(totals)}
        
        return responses
    
    async def stage3_synthesize(self, responses: List[CouncilResponse], num_ideas: int = 10) -> Dict[str, Any]:
        """Stage 3: Chairman synthesizes the best ideas into final output"""
        
        if not responses:
            return {"error": "No ideas generated in Stage 1 to synthesize.", "ideas": []}

        # Sort by scores if available
        scored = [r for r in responses if r.scores]
        if scored:
            scored.sort(key=lambda x: x.scores.get('average', 0), reverse=True)
            responses = scored + [r for r in responses if not r.scores]
        
        chairman_prompt = f"""You are the Chairman of an AI startup idea council. 
        
Multiple analysts have proposed startup ideas. Your job is to:
1. Review all proposals
2. Select the TOP {num_ideas} best ideas across all analysts
3. Synthesize and improve upon them
4. Output a final ranked list

Here are the analyst proposals:

{chr(10).join(f'=== {r.member} (Score: {r.scores.get("average", "N/A") if r.scores else "N/A"}) ===\n{r.response}' for r in responses)}

Create the final list of TOP {num_ideas} startup ideas. 
CRITICAL: You must return a valid JSON object containing a list of ideas.
Format:
{{
    "ideas": [
        {{
            "name": "Startup Name",
            "one_liner": "Short catchy tagline",
            "problem_statement": "Detailed problem description",
            "solution_description": "Detailed solution description",
            "revenue_model": "One of: subscription, usage, transaction, hybrid",
            "target_buyer_persona": {{
                "title": "Target User Title",
                "company_size": "SMB/Enterprise/Startup",
                "industry": "Tech/Retail/etc",
                "pain_intensity": 0.9
            }},
            "tam_estimate": "$XX Billion",
            "pricing_hypothesis": {{
                "tiers": ["Free", "Pro", "Enterprise"],
                "price_range": "$10-$100/mo"
            }},
            "technical_requirements_summary": "Python backend, React frontend..."
        }}
    ]
}}
output ONLY the JSON. No other text."""

        messages = [{"role": "user", "content": chairman_prompt}]
        
        async with aiohttp.ClientSession() as session:
            try:
                result = await self._call_model(self.CHAIRMAN_MODEL, messages, session)
                if result["success"]:
                    # Clean markdown if present
                    clean_res = result["content"].replace('```json', '').replace('```', '').strip()
                    try:
                        data = json.loads(clean_res)
                        return data
                    except json.JSONDecodeError:
                        print(f"Failed to parse Chairman JSON: {clean_res[:100]}...")
                        # Fallback to a single dummy idea text wrapped in structure if parse fails
                        return {
                            "ideas": [
                                {
                                    "name": "Parse Error Backup",
                                    "one_liner": "JSON Parsing failed",
                                    "problem_statement": "The LLM did not return valid JSON.",
                                    "solution_description": clean_res[:500],
                                    "revenue_model": "subscription",
                                    "target_buyer_persona": {
                                        "title": "Developer", "company_size": "Any", "industry": "Tech", "pain_intensity": 0.5
                                    },
                                    "tam_estimate": "Unknown",
                                    "pricing_hypothesis": {"tiers": [], "price_range": "Unknown"},
                                    "technical_requirements_summary": "None"
                                }
                            ]
                        }
                return {"error": result.get("error", "Unknown Chairman Error"), "ideas": []}
            except Exception as e:
                return {"error": str(e), "ideas": []}
    
    async def generate_ideas(self, pain_points: List[str], num_ideas: int = 10, 
                            on_stage_complete=None) -> Dict[str, Any]:
        """
        Full council process:
        1. Generate ideas from all council members
        2. Have them review each other
        3. Chairman synthesizes final list
        """
        result = {
            "stage1_responses": [],
            "stage2_scores": [],
            "final_ideas": "",
            "council_members": [m.name for m in self.council],
            "errors": []
        }
        
        # Stage 1
        if on_stage_complete:
            on_stage_complete("Stage 1: Council members generating ideas...")
        
        s1_result = await self.stage1_generate("", pain_points)
        responses = s1_result["responses"]
        result["errors"].extend(s1_result["errors"])
        
        result["stage1_responses"] = [(r.member, r.response[:500]+"...") for r in responses]
        
        if not responses:
             result["final_ideas"] = {"error": "All council members failed to generate ideas.", "ideas": []}
             return result
        
        # Stage 2
        if on_stage_complete:
            on_stage_complete("Stage 2: Peer review in progress...")
        responses = await self.stage2_review(responses)
        result["stage2_scores"] = [(r.member, r.scores) for r in responses if r.scores]
        
        # Stage 3
        if on_stage_complete:
            on_stage_complete("Stage 3: Chairman synthesizing final ideas...")
        final = await self.stage3_synthesize(responses, num_ideas)
        result["final_ideas"] = final

        
        return result


# Simple test
if __name__ == "__main__":
    async def test():
        council = LLMCouncil()
        pain_points = [
            "Developers waste hours on repetitive code tasks",
            "Small businesses struggle with inventory management",
            "Remote teams have poor async communication",
            "Finding reliable contractors is time-consuming",
            "Personal finance tracking is too complicated"
        ]
        result = await council.generate_ideas(pain_points, num_ideas=5)
        print(result["final_ideas"])
    
    asyncio.run(test())
