#!/bin/bash
# Run daily scrape, export data for site, build, and push to GitHub.
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

# Build the React site with new data
cd site
npm run build >> "$LOG_FILE" 2>&1
cd ..

echo "=== Build finished at $(date) ===" >> "$LOG_FILE"

# Commit and push
git add site/public/data/latest.json site/public/data/products.json
if git diff --cached --quiet; then
    echo "No data changes to commit" >> "$LOG_FILE"
else
    git commit -m "data: daily price update $(date +%Y-%m-%d)" >> "$LOG_FILE" 2>&1
    git push origin main >> "$LOG_FILE" 2>&1
    echo "=== Pushed to GitHub at $(date) ===" >> "$LOG_FILE"

    # Notify search engines about new content
    sleep 60  # Wait for GitHub Pages to deploy
    curl -s -X POST "https://api.indexnow.org/indexnow" \
      -H "Content-Type: application/json" \
      -d '{"host":"matmoms.se","key":"b08af54ab21b2b92e8c4452202f6ea3e","keyLocation":"https://matmoms.se/b08af54ab21b2b92e8c4452202f6ea3e.txt","urlList":["https://matmoms.se/"]}' >> "$LOG_FILE" 2>&1
    echo "=== IndexNow pinged at $(date) ===" >> "$LOG_FILE"
fi
