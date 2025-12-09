from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from enum import Enum


class JobSource(str, Enum):
    ADZUNA = "Adzuna"
    REED = "Reed"


class Job(BaseModel):
    """Unified job model for all sources"""
    title: str
    company: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    location: str
    remote: Optional[str] = None  # "Yes", "No", "Hybrid", or None if unknown
    description: str
    apply_url: str
    source: JobSource
    date_posted: Optional[date] = None
    careers_search_url: Optional[str] = None  # Google search link for company careers
    
    def __hash__(self):
        # For deduplication
        return hash((self.company.lower(), self.title.lower()))
    
    def __eq__(self, other):
        if not isinstance(other, Job):
            return False
        return (
            self.company.lower() == other.company.lower() and
            self._similar_title(other.title)
        )
    
    def _similar_title(self, other_title: str) -> bool:
        """Check if job titles are similar enough to be considered duplicates"""
        self_words = set(self.title.lower().split())
        other_words = set(other_title.lower().split())
        
        # Remove common filler words
        filler = {"a", "an", "the", "and", "or", "-", "/", "junior", "senior", "jr", "sr"}
        self_words -= filler
        other_words -= filler
        
        if not self_words or not other_words:
            return self.title.lower() == other_title.lower()
        
        # Calculate Jaccard similarity
        intersection = len(self_words & other_words)
        union = len(self_words | other_words)
        similarity = intersection / union if union > 0 else 0
        
        return similarity >= 0.6  # 60% word overlap = same job


class SearchParams(BaseModel):
    """Search parameters from user input"""
    keywords: str = Field(..., min_length=1, description="Job title or skills to search for")
    location: str = Field(default="london", description="Location to search in")
    remote_only: bool = Field(default=False, description="Only show remote jobs")
    min_salary: Optional[int] = Field(default=None, ge=0, description="Minimum annual salary")
    max_days_old: Optional[int] = Field(default=None, ge=1, le=30, description="Jobs posted within X days")
    max_results: int = Field(default=50, ge=1, le=200, description="Maximum results to return")


class SearchResponse(BaseModel):
    """API response for job search"""
    total_results: int
    jobs: list[Job]
    sources_queried: list[str]
