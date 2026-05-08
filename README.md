# Daily IT Support Job Hunter (Ireland)

Automated job search agent that scans multiple job sources daily at 5:00 AM Ireland time, filters for new IT Support roles, and emails a prioritized report.

## What it does

- Searches multiple boards (RSS/HTML/ATS sources) for IT Support roles in Ireland
- Filters roles posted within the last 3 days
- Scores matches based on skills, location, entry-level signals, and visa friendliness
- Avoids duplicates using a local SQLite database
- Sends a clean, mobile-friendly email report
- Tracks hiring trends and recurring companies

## Quick start (local)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m job_hunter --dry-run
```

## Configuration

Update `config/job_hunter.yaml` for:

- Search queries, roles, and preferred locations
- Source lists and ATS boards
- Email delivery settings

Environment variables override email settings:

```bash
export EMAIL_TO="akashvikram98@gmail.com"
export EMAIL_FROM="your-sender@domain.com"
export SMTP_HOST="smtp.your-provider.com"
export SMTP_PORT="587"
export SMTP_USER="smtp-user"
export SMTP_PASS="smtp-password"
```

## Scheduled automation

GitHub Actions runs the job hunter daily. The workflow:

- Installs dependencies
- Restores cached `data/` directory (job history)
- Runs `python -m job_hunter`

Add the SMTP secrets in your repository settings so the workflow can send email.

## Data storage

Job history is stored in `data/jobs.db` (SQLite). This file is cached during scheduled runs and ignored by Git.

## Add company career pages

For ATS boards, edit `config/job_hunter.yaml`:

```yaml
sources:
  - name: Company Career Pages (ATS)
    type: ats
    enabled: true
    ats_boards:
      - provider: greenhouse
        company: "company-slug"
```

Supported ATS providers: `greenhouse`, `lever`, `workable`.
