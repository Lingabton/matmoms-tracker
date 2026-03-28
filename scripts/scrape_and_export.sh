#!/bin/bash
# Run daily scrape, export data for site, and push to GitHub.
# Called by launchd at 06:00 daily.

set -e

cd /Users/gabriellinton/matmoms-tracker
source .venv/bin/activate

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/scrape-$(date +%Y-%m-%d).log"

echo "=== Scrape started at $(date) ===" >> "$LOG_FILE"

# Run scrape
matmoms scrape --headless -v >> "$LOG_FILE" 2>&1

echo "=== Scrape finished at $(date) ===" >> "$LOG_FILE"

# Export data for the site
python scripts/export_site_data.py >> "$LOG_FILE" 2>&1

echo "=== Export finished at $(date) ===" >> "$LOG_FILE"

# Commit and push the updated data
git add site/public/data/latest.json
if git diff --cached --quiet; then
    echo "No data changes to commit" >> "$LOG_FILE"
else
    git commit -m "data: daily price update $(date +%Y-%m-%d)" >> "$LOG_FILE" 2>&1
    git push origin main >> "$LOG_FILE" 2>&1
    echo "=== Pushed to GitHub at $(date) ===" >> "$LOG_FILE"
fi
