import httpx
from datetime import datetime, date
from urllib.parse import quote_plus
from typing import Optional
from app.models import Job, JobSource, SearchParams
from app.config import get_settings


class AdzunaClient:
    """Client for Adzuna Job Search API"""
    
    BASE_URL = "https://api.adzuna.com/v1/api/jobs/gb/search"
    
    def __init__(self):
        self.settings = get_settings()
        
    def _generate_careers_url(self, company: str) -> str:
        """Generate Google search URL for company careers page"""
        query = quote_plus(f"{company} careers jobs")
        return f"https://www.google.com/search?q={query}"
    
    def _parse_remote(self, job_data: dict) -> Optional[str]:
        """Determine if job is remote from description/title"""
        title = job_data.get("title", "").lower()
        description = job_data.get("description", "").lower()
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
        """Parse Adzuna date format"""
        try:
            # Adzuna format: "2025-12-05T10:30:00Z"
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        except (ValueError, AttributeError):
            return None
    
    async def search(self, params: SearchParams) -> list[Job]:
        """Search Adzuna for jobs matching parameters"""
        if not self.settings.adzuna_app_id or not self.settings.adzuna_app_key:
            print("Warning: Adzuna API credentials not configured")
            return []
        
        jobs = []
        results_per_page = 50
        pages_needed = (params.max_results + results_per_page - 1) // results_per_page
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for page in range(1, pages_needed + 1):
                query_params = {
                    "app_id": self.settings.adzuna_app_id,
                    "app_key": self.settings.adzuna_app_key,
                    "results_per_page": min(results_per_page, params.max_results - len(jobs)),
                    "what": params.keywords,
                    "where": params.location,
                    "content-type": "application/json",
                }
                
                # Add optional filters
                if params.min_salary:
                    query_params["salary_min"] = params.min_salary
                
                if params.max_days_old:
                    query_params["max_days_old"] = params.max_days_old
                
                try:
                    url = f"{self.BASE_URL}/{page}"
                    response = await client.get(url, params=query_params)
                    response.raise_for_status()
                    data = response.json()
                    
                    for job_data in data.get("results", []):
                        remote_status = self._parse_remote(job_data)
                        
                        # Skip non-remote jobs if remote_only filter is set
                        if params.remote_only and remote_status not in ("Yes", "Hybrid"):
                            continue
                        
                        company = job_data.get("company", {}).get("display_name", "Unknown")
                        
                        job = Job(
                            title=job_data.get("title", "Unknown"),
                            company=company,
                            salary_min=job_data.get("salary_min"),
                            salary_max=job_data.get("salary_max"),
                            location=job_data.get("location", {}).get("display_name", params.location),
                            remote=remote_status,
                            description=job_data.get("description", "")[:500],  # Truncate
                            apply_url=job_data.get("redirect_url", ""),
                            source=JobSource.ADZUNA,
                            date_posted=self._parse_date(job_data.get("created", "")),
                            careers_search_url=self._generate_careers_url(company),
                        )
                        jobs.append(job)
                        
                        if len(jobs) >= params.max_results:
                            return jobs
                    
                    # No more results available
                    if len(data.get("results", [])) < results_per_page:
                        break
                        
                except httpx.HTTPStatusError as e:
                    print(f"Adzuna API error: {e.response.status_code} - {e.response.text}")
                    break
                except httpx.RequestError as e:
                    print(f"Adzuna request error: {e}")
                    break
        
        return jobs
