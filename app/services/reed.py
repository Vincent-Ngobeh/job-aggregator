import httpx
import base64
from datetime import datetime, date, timedelta
from urllib.parse import quote_plus
from typing import Optional
from app.models import Job, JobSource, SearchParams
from app.config import get_settings


class ReedClient:
    """Client for Reed.co.uk Job Search API"""
    
    BASE_URL = "https://www.reed.co.uk/api/1.0/search"
    
    def __init__(self):
        self.settings = get_settings()
    
    def _get_auth_header(self) -> dict:
        """Reed uses Basic Auth with API key as username, empty password"""
        credentials = base64.b64encode(f"{self.settings.reed_api_key}:".encode()).decode()
        return {"Authorization": f"Basic {credentials}"}
    
    def _generate_careers_url(self, company: str) -> str:
        """Generate Google search URL for company careers page"""
        query = quote_plus(f"{company} careers jobs")
        return f"https://www.google.com/search?q={query}"
    
    def _parse_remote(self, job_data: dict) -> Optional[str]:
        """Determine if job is remote from job data"""
        title = job_data.get("jobTitle", "").lower()
        description = job_data.get("jobDescription", "").lower()
        text = f"{title} {description}"
        
        if "remote" in text and "hybrid" in text:
            return "Hybrid"
        elif "fully remote" in text or "100% remote" in text or "work from home" in text:
            return "Yes"
        elif "remote" in text:
            return "Yes"
        elif "hybrid" in text:
            return "Hybrid"
        elif "on-site" in text or "onsite" in text or "in-office" in text:
            return "No"
        return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse Reed date format"""
        try:
            # Reed format: "05/12/2025"
            return datetime.strptime(date_str, "%d/%m/%Y").date()
        except (ValueError, AttributeError, TypeError):
            return None
    
    async def search(self, params: SearchParams) -> list[Job]:
        """Search Reed for jobs matching parameters"""
        if not self.settings.reed_api_key:
            print("Warning: Reed API key not configured")
            return []
        
        jobs = []
        results_per_page = 100  # Reed allows up to 100
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            skip = 0
            
            while len(jobs) < params.max_results:
                query_params = {
                    "keywords": params.keywords,
                    "locationName": params.location,
                    "resultsToTake": min(results_per_page, params.max_results - len(jobs)),
                    "resultsToSkip": skip,
                }
                
                # Add optional filters
                if params.min_salary:
                    query_params["minimumSalary"] = params.min_salary
                
                try:
                    response = await client.get(
                        self.BASE_URL,
                        params=query_params,
                        headers=self._get_auth_header(),
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    results = data.get("results", [])
                    if not results:
                        break
                    
                    for job_data in results:
                        # Filter by date if specified
                        if params.max_days_old:
                            posted_date = self._parse_date(job_data.get("date"))
                            if posted_date:
                                cutoff = date.today() - timedelta(days=params.max_days_old)
                                if posted_date < cutoff:
                                    continue
                        
                        remote_status = self._parse_remote(job_data)
                        
                        # Skip non-remote jobs if remote_only filter is set
                        if params.remote_only and remote_status not in ("Yes", "Hybrid"):
                            continue
                        
                        company = job_data.get("employerName", "Unknown")
                        
                        job = Job(
                            title=job_data.get("jobTitle", "Unknown"),
                            company=company,
                            salary_min=job_data.get("minimumSalary"),
                            salary_max=job_data.get("maximumSalary"),
                            location=job_data.get("locationName", params.location),
                            remote=remote_status,
                            description=job_data.get("jobDescription", "")[:500],  # Truncate
                            apply_url=job_data.get("jobUrl", ""),
                            source=JobSource.REED,
                            date_posted=self._parse_date(job_data.get("date")),
                            careers_search_url=self._generate_careers_url(company),
                        )
                        jobs.append(job)
                        
                        if len(jobs) >= params.max_results:
                            return jobs
                    
                    # No more results available
                    if len(results) < results_per_page:
                        break
                    
                    skip += results_per_page
                    
                except httpx.HTTPStatusError as e:
                    print(f"Reed API error: {e.response.status_code} - {e.response.text}")
                    break
                except httpx.RequestError as e:
                    print(f"Reed request error: {e}")
                    break
        
        return jobs
