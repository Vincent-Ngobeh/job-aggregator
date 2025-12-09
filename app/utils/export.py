import csv
import io
from app.models import Job


def export_to_csv(jobs: list[Job]) -> str:
    """Export jobs to CSV format string"""
    output = io.StringIO()
    
    fieldnames = [
        "title",
        "company",
        "salary_min",
        "salary_max",
        "location",
        "remote",
        "description",
        "apply_url",
        "careers_search_url",
        "source",
        "date_posted",
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for job in jobs:
        writer.writerow({
            "title": job.title,
            "company": job.company,
            "salary_min": job.salary_min or "",
            "salary_max": job.salary_max or "",
            "location": job.location,
            "remote": job.remote or "Unknown",
            "description": job.description.replace("\n", " ").replace("\r", " "),
            "apply_url": job.apply_url,
            "careers_search_url": job.careers_search_url or "",
            "source": job.source.value,
            "date_posted": job.date_posted.isoformat() if job.date_posted else "",
        })
    
    return output.getvalue()
