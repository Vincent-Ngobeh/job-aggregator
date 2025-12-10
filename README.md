# Job Aggregator

A FastAPI application that aggregates job listings from Adzuna and Reed APIs, deduplicates results, and exports to CSV.

Built to streamline job searching by combining multiple sources into a single, clean interface.

## Features

- 🔍 **Multi-source search** - Queries Adzuna and Reed simultaneously
- 🔄 **Deduplication** - Removes duplicate listings across sources
- 📊 **CSV export** - Download results for tracking in spreadsheets
- 🌐 **Remote filter** - Filter for remote/hybrid positions
- 💰 **Salary filter** - Set minimum salary requirements
- 📅 **Recency filter** - Only show jobs posted within X days
- 🔗 **Company careers link** - Quick link to search company career pages

## Tech Stack

- **FastAPI** - Modern Python web framework
- **httpx** - Async HTTP client
- **Pydantic** - Data validation
- **Jinja2** - HTML templating

# Job Aggregator

🚀 **Live Demo:** [job-aggregator-bvk1.onrender.com](https://job-aggregator-bvk1.onrender.com)

A FastAPI application that aggregates job listings from Adzuna and Reed APIs

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/Vincent-Ngobeh/job-aggregator.git
cd job-aggregator
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get API keys (free)

- **Adzuna**: Register at [developer.adzuna.com](https://developer.adzuna.com/)
- **Reed**: Register at [reed.co.uk/developers](https://www.reed.co.uk/developers)

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Run locally

```bash
uvicorn app.main:app --reload
```

Visit [http://localhost:8000](http://localhost:8000)

## API Endpoints

| Endpoint       | Method | Description                    |
| -------------- | ------ | ------------------------------ |
| `/`            | GET    | Web interface with search form |
| `/jobs/search` | GET    | JSON API for job search        |
| `/jobs/export` | GET    | Download results as CSV        |
| `/health`      | GET    | Health check endpoint          |

### Search Parameters

| Parameter      | Type    | Default    | Description               |
| -------------- | ------- | ---------- | ------------------------- |
| `keywords`     | string  | _required_ | Job title or skills       |
| `location`     | string  | london     | Location to search        |
| `remote_only`  | boolean | false      | Only remote/hybrid jobs   |
| `min_salary`   | integer | -          | Minimum annual salary     |
| `max_days_old` | integer | -          | Jobs posted within X days |
| `max_results`  | integer | 50         | Max results (1-200)       |

### Example API Request

```bash
curl "http://localhost:8000/jobs/search?keywords=python%20developer&location=london&min_salary=40000&remote_only=true"
```

## Deployment (Render)

### 1. Create `render.yaml`

```yaml
services:
  - type: web
    name: job-aggregator
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: ADZUNA_APP_ID
        sync: false
      - key: ADZUNA_APP_KEY
        sync: false
      - key: REED_API_KEY
        sync: false
```

### 2. Deploy

1. Push to GitHub
2. Connect repo to Render
3. Add environment variables in Render dashboard
4. Deploy

## Project Structure

```
job-aggregator/
├── app/
│   ├── main.py              # FastAPI app + endpoints
│   ├── config.py            # Environment settings
│   ├── models.py            # Pydantic models
│   ├── services/
│   │   ├── adzuna.py        # Adzuna API client
│   │   ├── reed.py          # Reed API client
│   │   └── aggregator.py    # Combine + deduplicate
│   ├── utils/
│   │   └── export.py        # CSV export
│   └── templates/
│       └── index.html       # Web interface
├── .env.example
├── requirements.txt
└── README.md
```

## How Deduplication Works

Jobs are considered duplicates if:

1. Same company (case-insensitive)
2. Similar job title (60%+ word overlap, ignoring filler words like "junior", "senior", etc.)

The first occurrence is kept, preserving source priority (Adzuna → Reed).

## License

MIT

## Author

Vincent Ngobeh - [GitHub](https://github.com/Vincent-Ngobeh) | [LinkedIn](https://www.linkedin.com/in/vincent-ngobeh/)
