"""
Contract Analysis Service using Gemini 2.5 Flash.
Extracts text from contracts and analyzes clauses for creator risks.
"""
import io
import re
import json
from typing import Dict, Any
import google.generativeai as genai
from docx import Document

from app.config import get_settings

settings = get_settings()

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pypdf (pure Python, serverless compatible)."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX using python-docx."""
    try:
        doc = Document(io.BytesIO(file_bytes))
        text = "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise ValueError(f"Failed to extract text from DOCX: {str(e)}")
    
    return text


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from uploaded file based on extension."""
    filename_lower = filename.lower()
    
    if filename_lower.endswith('.pdf'):
        return extract_text_from_pdf(file_bytes)
    elif filename_lower.endswith('.docx'):
        return extract_text_from_docx(file_bytes)
    elif filename_lower.endswith('.txt'):
        return file_bytes.decode('utf-8', errors='ignore')
    else:
        # Try as plain text
        return file_bytes.decode('utf-8', errors='ignore')


ANALYSIS_PROMPT = """You are a contract analysis expert helping content creators understand influencer/brand collaboration contracts. 

FIRST: Determine if this document is actually a contract, deal, agreement, or business proposal. A contract/deal should contain things like:
- Legal terms, obligations, or agreements between parties
- Payment terms, deliverables, timelines
- Rights, licenses, exclusivity clauses
- Signatures or signature blocks
- Business collaboration terms

If this document is NOT a contract, deal, agreement, or business proposal (for example: a random article, homework, recipe, resume, memes, lyrics, personal notes, etc.), respond with this exact JSON:
{{
  "not_a_contract": true,
  "document_type": "<what type of document this appears to be>"
}}

If it IS a contract/deal, analyze it and identify risky clauses. For each clause found, determine:
1. The clause type (exclusivity, usage_rights, ip_ownership, payment_terms, revisions, termination, auto_renewal, deliverables)
2. Risk level: "green" (safe/standard), "yellow" (vague/negotiable), or "red" (high-risk)
3. Plain English explanation (talk like you're explaining to a friend, not a lawyer)
4. What to push back on (if yellow or red)
5. Suggested alternative wording (if yellow or red)

IMPORTANT: Focus on these high-risk areas commonly found in creator contracts:
- Exclusivity: How long? How broad? Does it block similar brand work?
- Usage Rights: Can they use your content in paid ads? For how long? Forever?
- IP Ownership: Are you transferring ownership or just licensing?
- Payment Terms: When do you get paid? Based on approval? Net 30? Net 60?
- Revisions: Unlimited revisions = unpaid work. Look for limits.
- Termination: Is there a kill fee? What if they cancel?
- Auto-Renewal: Does it auto-renew? How do you opt out?
- Deliverables: Are they specific or vague?

Country context for legal nuances: {country}

CONTRACT TEXT:
{contract_text}

Respond in this exact JSON format:
{{
  "summary": {{
    "total_clauses": <number>,
    "green_count": <number>,
    "yellow_count": <number>,
    "red_count": <number>,
    "biggest_risk": "<brief description of the single biggest long-term risk>"
  }},
  "clauses": [
    {{
      "type": "<clause type>",
      "risk_level": "green|yellow|red",
      "original_text": "<relevant text from contract>",
      "explanation": "<plain English explanation>",
      "push_back": "<what to ask/push back on, or null if green>",
      "suggested_alternative": "<suggested wording, or null if green>"
    }}
  ],
  "next_steps": [
    "<ranked action item 1>",
    "<ranked action item 2>",
    "<ranked action item 3>"
  ]
}}

Only return valid JSON, no markdown formatting or code blocks."""


async def analyze_contract(
    file_bytes: bytes, 
    filename: str, 
    country: str = "United States"
) -> Dict[str, Any]:
    """
    Analyze a contract using Gemini 2.5 Flash.
    Returns structured analysis with risk scores and recommendations.
    """
    # Extract text from file
    contract_text = extract_text(file_bytes, filename)
    
    if not contract_text or len(contract_text.strip()) < 50:
        raise ValueError("Could not extract enough text from the contract. Please try a different file format.")
    
    # Prepare the prompt
    prompt = ANALYSIS_PROMPT.format(
        country=country,
        contract_text=contract_text[:15000]  # Limit to avoid token limits
    )
    
    # Call Gemini
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    
    # Parse response
    response_text = response.text.strip()
    
    # Clean up response if wrapped in markdown code blocks
    if response_text.startswith("```"):
        response_text = re.sub(r'^```json?\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
    
    try:
        analysis = json.loads(response_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Gemini response: {str(e)}")
    
    # Check if this is not a contract - return funny prank response
    if analysis.get("not_a_contract"):
        doc_type = analysis.get("document_type", "random document")
        funny_messages = [
            f"Nice try! 🎭 You uploaded a {doc_type}... try pranking me next time. Pls give me an actual contract, bestie!",
            f"Uhh... this looks like a {doc_type}? I'm a contract analyzer, not a fortune teller! 🔮 Send me a real deal!",
            f"Lmao you really thought I wouldn't notice this is just a {doc_type}? 😂 Give me a contract or go home!",
            f"Bruh. This is a {doc_type}. I analyze CONTRACTS. You know, the legal stuff? Try again! 📜",
            f"Error 404: Contract not found. Found: {doc_type}. Try pranking me next time! 🤡"
        ]
        import random
        return {
            "not_a_contract": True,
            "prank_detected": True,
            "document_type": doc_type,
            "message": random.choice(funny_messages),
            "filename": filename,
            "suggestion": "Upload a real contract, deal, or agreement and I'll help you spot the red flags! 🚩"
        }
    
    # Add metadata
    analysis["filename"] = filename
    analysis["country"] = country
    analysis["contract_text_preview"] = contract_text[:500] + "..." if len(contract_text) > 500 else contract_text
    
    return analysis


NEGOTIATION_EMAIL_PROMPT = """You are helping a content creator write a professional but friendly email to negotiate contract terms with a brand.

Based on this contract analysis, write a concise negotiation email that:
1. Thanks them for the opportunity
2. Addresses the top concerns (red flags first, then yellow)
3. Proposes specific alternatives for each concern
4. Keeps a collaborative, not adversarial tone
5. Is ready to copy/paste and send

Analysis:
{analysis_json}

Write ONLY the email body (no subject line). Keep it under 200 words. Be professional but warm."""


async def generate_negotiation_email(analysis: Dict[str, Any]) -> str:
    """Generate a negotiation email based on contract analysis."""
    # Filter to only include concerning clauses
    concerning_clauses = [
        c for c in analysis.get("clauses", [])
        if c.get("risk_level") in ["yellow", "red"]
    ]
    
    if not concerning_clauses:
        return "Great news! This contract looks pretty standard and doesn't have major red flags. You may not need to negotiate, but always feel free to ask clarifying questions!"
    
    # Prepare analysis summary for prompt
    analysis_for_prompt = {
        "summary": analysis.get("summary", {}),
        "concerning_clauses": concerning_clauses[:5],  # Top 5 concerns
        "next_steps": analysis.get("next_steps", [])
    }
    
    prompt = NEGOTIATION_EMAIL_PROMPT.format(
        analysis_json=json.dumps(analysis_for_prompt, indent=2)
    )
    
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content(prompt)
    
    return response.text.strip()
