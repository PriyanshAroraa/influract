"""
Contract analysis API routes.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
import uuid
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.services.contract_service import analyze_contract, generate_negotiation_email

router = APIRouter()

# Rate limiter for this router - 10 requests per hour per IP
limiter = Limiter(key_func=get_remote_address)

# In-memory storage for serverless (temporary, clears on cold start)
_temp_storage: dict = {}


@router.post("/analyze")
@limiter.limit("10/hour")
async def analyze_contract_endpoint(
    request: Request,
    file: UploadFile = File(...),
    country: str = Form(default="United States")
):
    """
    Upload and analyze a contract file.
    Supports PDF, DOCX, and TXT files.
    
    Returns analysis with traffic light risk scores and recommendations.
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.txt']
    filename = file.filename or "contract.txt"
    
    if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Read file content
    try:
        file_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    
    # Analyze contract
    try:
        analysis = await analyze_contract(file_bytes, filename, country)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    # Store in memory temporarily
    analysis_id = str(uuid.uuid4())
    analysis["id"] = analysis_id
    _temp_storage[analysis_id] = analysis
    
    return {
        "id": analysis_id,
        "analysis": analysis
    }


@router.post("/analyze-text")
@limiter.limit("10/hour")
async def analyze_text_endpoint(
    request: Request,
    text: str = Form(...),
    country: str = Form(default="United States")
):
    """
    Analyze contract text directly (copy/paste).
    """
    if len(text.strip()) < 50:
        raise HTTPException(
            status_code=400, 
            detail="Please provide more contract text (at least 50 characters)"
        )
    
    try:
        analysis = await analyze_contract(
            text.encode('utf-8'), 
            "pasted_contract.txt", 
            country
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    # Store in memory temporarily
    analysis_id = str(uuid.uuid4())
    analysis["id"] = analysis_id
    _temp_storage[analysis_id] = analysis
    
    return {
        "id": analysis_id,
        "analysis": analysis
    }


@router.get("/{analysis_id}")
async def get_analysis_endpoint(analysis_id: str):
    """Get a saved analysis by ID."""
    analysis = _temp_storage.get(analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found or expired")
    
    return analysis


@router.post("/{analysis_id}/generate-email")
async def generate_email_endpoint(analysis_id: str):
    """Generate a negotiation email based on the analysis."""
    analysis = _temp_storage.get(analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found or expired")
    
    try:
        email = await generate_negotiation_email(analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email generation failed: {str(e)}")
    
    return {"email": email}
