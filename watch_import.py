import argparse
import logging
import os
import shutil
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import import_inventory

VALID_EXTENSIONS = {".xlsx", ".xls"}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def ensure_folder(path):
    os.makedirs(path, exist_ok=True)
    return path


class ImportHandler(FileSystemEventHandler):
    def __init__(self, folder, db_path, processed_dir, failed_dir):
        self.folder = folder
        self.db_path = db_path
        self.processed_dir = processed_dir
        self.failed_dir = failed_dir

    def on_created(self, event):
        if event.is_directory:
            return
        self.process(event.src_path)

    def on_moved(self, event):
        if event.is_directory:
            return
        self.process(event.dest_path)

    def process(self, path):
        _, ext = os.path.splitext(path)
        if ext.lower() not in VALID_EXTENSIONS:
            return

        time.sleep(1)
        logging.info("Detected file: %s", path)
        try:
            summary = import_inventory.import_excel(path, db_path=self.db_path, changed_by="watcher")
            logging.info("Imported %s: inserted=%d updated=%d skipped=%d invalid=%d", os.path.basename(path), summary["inserted"], summary["updated"], summary["skipped"], len(summary["invalid_rows"]))
            dest = os.path.join(self.processed_dir, os.path.basename(path))
            shutil.move(path, dest)
            logging.info("Moved processed file to %s", dest)
        except Exception as exc:
            logging.error("Failed to import %s: %s", path, exc)
            dest = os.path.join(self.failed_dir, os.path.basename(path))
            shutil.move(path, dest)
            logging.info("Moved failed file to %s", dest)


def main():
    parser = argparse.ArgumentParser(description="Watch a folder and import new Excel inventory files")
    parser.add_argument("--folder", default="watch_folder", help="Folder to monitor")
    parser.add_argument("--db", default=import_inventory.DB_PATH, help="SQLite database path")
    args = parser.parse_args()

    folder = os.path.abspath(args.folder)
    processed = ensure_folder(os.path.join(folder, "processed"))
    failed = ensure_folder(os.path.join(folder, "failed"))
    ensure_folder(folder)

    event_handler = ImportHandler(folder, args.db, processed, failed)
    observer = Observer()
    observer.schedule(event_handler, folder, recursive=False)
    observer.start()

    logging.info("Watching folder %s for new Excel files", folder)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
