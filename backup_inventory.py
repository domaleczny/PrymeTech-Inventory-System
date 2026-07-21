import os
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

DB_PATH = r"C:\InventoryApp\inventory.db"
EXPORT_DIR = r"P:\Manufacturing\Jobs\Inventory\Backups"

KEEP_LAST = 5

os.makedirs(EXPORT_DIR, exist_ok=True)

def export_excel():
    conn = sqlite3.connect(DB_PATH)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(EXPORT_DIR, f"backup_{timestamp}.xlsx")

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        pd.read_sql_query("SELECT * FROM inventory", conn).to_excel(writer, sheet_name="inventory", index=False)
        pd.read_sql_query("SELECT * FROM probe_inventory", conn).to_excel(writer, sheet_name="probe_inventory", index=False)

    conn.close()
    return file_path

def cleanup_old_files():
    files = sorted(
        Path(EXPORT_DIR).glob("backup_*.xlsx"),
        key=lambda p: p.stat().st_mtime
    )

    while len(files) > KEEP_LAST:
        old_file = files.pop(0)
        try:
            old_file.unlink()
            print(f"Deleted old backup: {old_file}")
        except Exception as e:
            print(f"Could not delete {old_file}: {e}")

def main():
    file_created = export_excel()
    print(f"Created backup: {file_created}")

    cleanup_old_files()

if __name__ == "__main__":
    main()