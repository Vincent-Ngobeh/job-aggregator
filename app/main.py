from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Optional
from datetime import datetime
import io

from app.models import SearchParams, SearchResponse
from app.services.aggregator import JobAggregator
from app.utils.export import export_to_csv
from app.config import get_settings


# Initialize FastAPI app
app = FastAPI(
    title="Job Aggregator API",
    description="Aggregates job listings from Adzuna and Reed, deduplicates results, and exports to CSV",
    version="1.0.0",
)

# Initialize services
aggregator = JobAggregator()

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


@app.get("/", response_class=HTMLResponse)
async def home():
    """Serve the search form HTML page"""
    template_path = TEMPLATES_DIR / "index.html"
    return template_path.read_text()


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    settings = get_settings()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "adzuna_configured": bool(settings.adzuna_app_id and settings.adzuna_app_key),
        "reed_configured": bool(settings.reed_api_key),
    }


@app.get("/jobs/search", response_model=SearchResponse)
async def search_jobs(
    keywords: str = Query(..., min_length=1, description="Job title or skills to search for"),
    location: str = Query("london", description="Location to search in"),
    remote_only: bool = Query(False, description="Only show remote/hybrid jobs"),
    min_salary: Optional[int] = Query(None, ge=0, description="Minimum annual salary"),
    max_days_old: Optional[int] = Query(None, ge=1, le=30, description="Jobs posted within X days"),
    max_results: int = Query(50, ge=1, le=200, description="Maximum results to return"),
):
    """
    Search for jobs across Adzuna and Reed.
    
    - **keywords**: Required. Job title, skills, or keywords to search for
    - **location**: Where to search (defaults to London)
    - **remote_only**: If true, only returns remote or hybrid positions
    - **min_salary**: Filter out jobs below this annual salary
    - **max_days_old**: Only return jobs posted within this many days
    - **max_results**: Cap the number of results (max 200)
    
    Returns deduplicated results from both sources, sorted by date and salary.
    """
    params = SearchParams(
        keywords=keywords,
        location=location,
        remote_only=remote_only,
        min_salary=min_salary,
        max_days_old=max_days_old,
        max_results=max_results,
    )
    
    try:
        results = await aggregator.search(params)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/jobs/export")
async def export_jobs(
    keywords: str = Query(..., min_length=1, description="Job title or skills to search for"),
    location: str = Query("london", description="Location to search in"),
    remote_only: bool = Query(False, description="Only show remote/hybrid jobs"),
    min_salary: Optional[int] = Query(None, ge=0, description="Minimum annual salary"),
    max_days_old: Optional[int] = Query(None, ge=1, le=30, description="Jobs posted within X days"),
    max_results: int = Query(50, ge=1, le=200, description="Maximum results to return"),
):
    """
    Search for jobs and export results as a CSV file.
    
    Same parameters as /jobs/search. Returns a downloadable CSV file.
    """
    params = SearchParams(
        keywords=keywords,
        location=location,
        remote_only=remote_only,
        min_salary=min_salary,
        max_days_old=max_days_old,
        max_results=max_results,
    )
    
    try:
        results = await aggregator.search(params)
        csv_content = export_to_csv(results.jobs)
        
        # Generate filename with search params
        safe_keywords = "".join(c if c.isalnum() else "_" for c in keywords)[:30]
        filename = f"jobs_{safe_keywords}_{location}_{datetime.now().strftime('%Y%m%d')}.csv"
        
        return StreamingResponse(
            io.StringIO(csv_content),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
