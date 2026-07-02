# backup_inventory.py
import argparse
import os
import sqlite3
from datetime import datetime
from pathlib import Path

def backup_sqlite(db_path, backup_path):
    src = sqlite3.connect(db_path)
    try:
        dst = sqlite3.connect(backup_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

def main():
    parser = argparse.ArgumentParser(description="Create a SQLite backup for the inventory database")
    parser.add_argument("--db", default=os.environ.get("INVENTORY_DB", r"\\SERVER-2019\Server-P\Manufacturing\Master CAD Libraries\InventoryBackups\inventory.db"), help="Path to the SQLite database")
    parser.add_argument("--dest", default=os.environ.get("BACKUP_DIR", r"\\SERVER-2019\Server-P\Manufacturing\Master CAD Libraries\InventoryBackups"), help="Directory for backup files")
    parser.add_argument("--keep", type=int, default=7, help="How many backup files to keep")
    args = parser.parse_args()

    db_path = Path(args.db).expanduser()
    dest_dir = Path(args.dest).expanduser()
    dest_dir.mkdir(parents=True, exiswhet_ok=True)

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = dest_dir / f"{db_path.stem}_{timestamp}.db"

    backup_sqlite(str(db_path), str(backup_path))
    print(f"Backup created: {backup_path}")

    # Delete old backups beyond the retention limit
    backups = sorted(dest_dir.glob(f"{db_path.stem}_*.db"), key=lambda p: p.stat().st_mtime)
    while len(backups) > args.keep:
        old_file = backups.pop(0)
        old_file.unlink()
        print(f"Removed old backup: {old_file}")

if __name__ == "__main__":
    main()