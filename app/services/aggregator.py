import asyncio
from app.models import Job, SearchParams, SearchResponse
from app.services.adzuna import AdzunaClient
from app.services.reed import ReedClient


class JobAggregator:
    """Aggregates jobs from multiple sources and removes duplicates"""
    
    def __init__(self):
        self.adzuna = AdzunaClient()
        self.reed = ReedClient()
    
    def _deduplicate(self, jobs: list[Job]) -> list[Job]:
        """
        Remove duplicate jobs based on company + similar title.
        Keeps the first occurrence (preserves source priority).
        """
        seen = {}
        unique_jobs = []
        
        for job in jobs:
            # Create a normalized key for comparison
            company_key = job.company.lower().strip()
            
            # Check if we've seen a similar job from this company
            is_duplicate = False
            for existing_key, existing_job in seen.items():
                if existing_key == company_key and job._similar_title(existing_job.title):
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                seen[company_key] = job
                unique_jobs.append(job)
        
        return unique_jobs
    
    def _sort_jobs(self, jobs: list[Job]) -> list[Job]:
        """Sort jobs by date posted (newest first), then by salary (highest first)"""
        def sort_key(job: Job):
            # Date: newer is better (use a very old date for None)
            date_score = job.date_posted.toordinal() if job.date_posted else 0
            
            # Salary: higher is better (use 0 for None)
            salary_score = job.salary_max or job.salary_min or 0
            
            return (-date_score, -salary_score)  # Negative for descending
        
        return sorted(jobs, key=sort_key)
    
    async def search(self, params: SearchParams) -> SearchResponse:
        """
        Search all sources concurrently, combine results, and deduplicate.
        """
        # Query both APIs concurrently
        adzuna_task = asyncio.create_task(self.adzuna.search(params))
        reed_task = asyncio.create_task(self.reed.search(params))
        
        # Wait for both to complete
        adzuna_jobs, reed_jobs = await asyncio.gather(
            adzuna_task,
            reed_task,
            return_exceptions=True,
        )
        
        # Handle any exceptions
        if isinstance(adzuna_jobs, Exception):
            print(f"Adzuna search failed: {adzuna_jobs}")
            adzuna_jobs = []
        if isinstance(reed_jobs, Exception):
            print(f"Reed search failed: {reed_jobs}")
            reed_jobs = []
        
        # Track which sources returned results
        sources_queried = []
        if adzuna_jobs:
            sources_queried.append("Adzuna")
        if reed_jobs:
            sources_queried.append("Reed")
        
        # Combine all jobs (Adzuna first as it often has better data)
        all_jobs = adzuna_jobs + reed_jobs
        
        # Deduplicate
        unique_jobs = self._deduplicate(all_jobs)
        
        # Sort by date and salary
        sorted_jobs = self._sort_jobs(unique_jobs)
        
        # Limit to max_results
        final_jobs = sorted_jobs[:params.max_results]
        
        return SearchResponse(
            total_results=len(final_jobs),
            jobs=final_jobs,
            sources_queried=sources_queried,
        )
