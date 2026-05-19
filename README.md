# Inventory SQLite Migration System

A simple SQLite-backed inventory system with Excel import, CLI management, a Flask web UI, and watch-folder automation.

## Features
- SQLite inventory table with internal integer `id` and unique `part_number`
- Flexible Excel import using `pandas` + `openpyxl`
- UPSERT behavior by `part_number`
- CLI commands for import, export, show, list, and bulk updates
- Flask UI for browsing, searching, editing, importing, and exporting
- Watch-folder automation for auto-importing new Excel files
- Audit trail in a `changes` table for create/update/delete events
- Backup guidance for SQLite databases

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create the SQLite schema:

```bash
python -c "import sqlite3, os; conn=sqlite3.connect('inventory.db'); conn.executescript(open('create_schema.sql').read()); conn.close()"
```

3. Run the application:

```bash
python app.py
```

The Flask UI will be available at `http://127.0.0.1:5000`.

## CLI Usage

Import from Excel:

```bash
python manage.py import inventory.xlsx
```

List all items:

```bash
python manage.py list
```

List low-stock items:

```bash
python manage.py list --low-stock
```

Show a single item:

```bash
python manage.py show PART-123
```

Export results:

```bash
python manage.py export inventory.csv --format csv
python manage.py export inventory.xlsx --format xlsx
```

Bulk update via Excel:

```bash
python manage.py bulk-update --file bulk_changes.xlsx
```

## Watch-folder Automation

Start the watcher to monitor a folder and import new Excel files automatically:

```bash
python watch_import.py --folder watch_folder
```

Processed files are moved to `watch_folder/processed`; failed imports are moved to `watch_folder/failed`.

## SQLite Backup Guidance

### Manual backup

Create a timestamped copy of the database using Python:

```bash
python - <<'PY'
import shutil
from datetime import datetime
shutil.copy('inventory.db', f'inventory_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
PY
```

### Windows Task Scheduler example

- Action: `python C:\path\to\manage.py` or a small backup script
- Trigger: daily or hourly as needed
- Backup script example:

```python
import shutil
from datetime import datetime
shutil.copy('inventory.db', f'inventory_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
```

### systemd timer example

Create `backup_inventory.service`:

```ini
[Unit]
Description=Backup inventory SQLite database

[Service]
Type=oneshot
WorkingDirectory=/path/to/repo
ExecStart=/usr/bin/python3 -c "import shutil; from datetime import datetime; shutil.copy('inventory.db', f'inventory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db')"
```

Create `backup_inventory.timer`:

```ini
[Unit]
Description=Run inventory backup every day

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable with:

```bash
sudo systemctl enable --now backup_inventory.timer
```

## Testing

Run unit tests:

```bash
python -m unittest discover -s tests
```

## Sample fixture generation

A helper script is included to generate a sample Excel fixture in `tests/fixtures`:

```bash
python generate_sample_fixture.py
```

## Notes

- `sqlite3` is builtin to Python and does not need installation
- The system is designed for a single internal user and does not include authentication
- Excel headers are auto-mapped using common variations for part number, description, location, quantity, min quantity, customer, and last modify date
