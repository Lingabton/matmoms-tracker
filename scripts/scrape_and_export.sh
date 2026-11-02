#!/bin/bash
# Run daily scrape, export data for site, build, and push to GitHub.
# Called by launchd at 06:00 daily.

BASE="/Users/gabriellinton/matmoms-tracker"
cd "$BASE"
source .venv/bin/activate
[ -f "$BASE/.env" ] && set -a && source "$BASE/.env" && set +a

mkdir -p "$BASE/logs"
LOG="$BASE/logs/scrape-$(date +%Y-%m-%d).log"

# Wait for network (max 5 min)
for i in $(seq 1 30); do
    curl -s --max-time 5 -o /dev/null https://www.willys.se/ && break
    echo "$(date): Waiting for network ($i/30)..." >> "$LOG"
    sleep 10
done

if ! curl -s --max-time 5 -o /dev/null https://www.willys.se/; then
    echo "=== ABORTED at $(date): no network after 5 min ===" >> "$LOG"
    exit 1
fi

echo "=== Scrape started at $(date) ===" >> "$LOG"

# Kill any running scrape to avoid DB lock
pkill -f "matmoms scrape" 2>/dev/null
sleep 2

# Run scrape
matmoms scrape --headless -v >> "$LOG" 2>&1 || echo "Scrape had errors" >> "$LOG"
echo "=== Scrape finished at $(date) ===" >> "$LOG"

# Export data
python "$BASE/scripts/export_site_data.py" >> "$LOG" 2>&1
echo "=== Export finished at $(date) ===" >> "$LOG"

# Build React site
cd "$BASE/site"
npm run build >> "$LOG" 2>&1
cd "$BASE"
echo "=== Build finished at $(date) ===" >> "$LOG"

# Commit and push
git add site/public/data/latest.json site/public/data/products.json site/public/data/catalog.json site/public/sitemap.xml
if git diff --cached --quiet; then
    echo "No data changes to commit" >> "$LOG"
else
    git commit -m "data: daily price update $(date +%Y-%m-%d)" >> "$LOG" 2>&1
    git push origin main >> "$LOG" 2>&1
    echo "=== Pushed to GitHub at $(date) ===" >> "$LOG"

    # Monthly snapshot release (1st of each month)
    if [ "$(date +%d)" = "01" ]; then
        echo "=== Monthly snapshot export ===" >> "$LOG"
        bash "$BASE/scripts/export_monthly_snapshot.sh" >> "$LOG" 2>&1 \
            && echo "=== Monthly snapshot released at $(date) ===" >> "$LOG" \
            || echo "=== Monthly snapshot FAILED at $(date) ===" >> "$LOG"
    fi

    sleep 60
    INDEXNOW_KEY="${INDEXNOW_KEY:-b08af54ab21b2b92e8c4452202f6ea3e}"
    curl -s -X POST "https://api.indexnow.org/indexnow" \
      -H "Content-Type: application/json" \
      -d "{\"host\":\"matmoms.se\",\"key\":\"${INDEXNOW_KEY}\",\"keyLocation\":\"https://matmoms.se/${INDEXNOW_KEY}.txt\",\"urlList\":[\"https://matmoms.se/\"]}" >> "$LOG" 2>&1
    echo "=== IndexNow pinged at $(date) ===" >> "$LOG"
fi
