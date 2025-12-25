"""
Contract analysis API routes.
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional

from app.services.contract_service import analyze_contract, generate_negotiation_email
from app.storage import save_analysis, get_analysis, list_analyses

router = APIRouter()


@router.post("/analyze")
async def analyze_contract_endpoint(
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
    
    # Save to local storage
    analysis_id = save_analysis(analysis)
    
    return {
        "id": analysis_id,
        "analysis": analysis
    }


@router.post("/analyze-text")
async def analyze_text_endpoint(
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
    
    analysis_id = save_analysis(analysis)
    
    return {
        "id": analysis_id,
        "analysis": analysis
    }


@router.get("/{analysis_id}")
async def get_analysis_endpoint(analysis_id: str):
    """Get a saved analysis by ID."""
    analysis = get_analysis(analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    return analysis


@router.get("/")
async def list_analyses_endpoint():
    """List all saved analyses."""
    return list_analyses()


@router.post("/{analysis_id}/generate-email")
async def generate_email_endpoint(analysis_id: str):
    """Generate a negotiation email based on the analysis."""
    analysis = get_analysis(analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    try:
        email = await generate_negotiation_email(analysis)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email generation failed: {str(e)}")
    
    return {"email": email}
