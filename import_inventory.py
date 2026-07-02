import argparse
import json
import logging
import os
import re
import sqlite3
from datetime import datetime

import pandas as pd

DB_PATH = os.environ.get("INVENTORY_DB", "inventory.db")
SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "create_schema.sql")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

HEADER_SYNONYMS = {
    "part_number": ["part number"],
    "description": ["part description"],
    "location": ["loc"],
    "quantity": ["qty", "qty in stock", "qtyinstock", "in-stock quantity"],
    "min_quantity": ["min bin qty", "minbinqty"],
    "customer": ["supplier"],
    "last_modify_date": ["last modify date"],
    # probe-specific
    "thread_size": ["thread size"],
    "sphere_dk": ["ø sphere (dk)", "sphere (dk)"],
    "length": ["length (l)"],
    "ml_ewl": ["ml / ewl", "ml/ewl"],
    "tip_material": ["tip material"],
    "shaft_material": ["shaft material"],
    "probe_type": ["probe type"],
    "link": ["link to part"],
}

REQUIRED_COLUMNS = ["part_number", "quantity"]
OPTIONAL_COLUMNS = ["description", "location", "min_quantity", "customer", "last_modify_date"]
ALL_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS

PROBE_OPTIONAL_COLUMNS = [
    "thread_size", "sphere_dk", "length", "ml_ewl",
    "tip_material", "shaft_material", "probe_type", "link"
]
PROBE_ALL_COLUMNS = ALL_COLUMNS + PROBE_OPTIONAL_COLUMNS

def normalize_header(value):
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def build_column_map(columns):
    normalized_to_raw = {normalize_header(col): col for col in columns}
    mapping = {}

    for canonical, aliases in HEADER_SYNONYMS.items():
        candidates = [canonical] + aliases
        for alias in candidates:
            normalized_alias = normalize_header(alias)
            if normalized_alias in normalized_to_raw:
                mapping[canonical] = normalized_to_raw[normalized_alias]
                break

    return mapping


def parse_int(value, field_name, required=True, default=0):
    if pd.isna(value) or value == "":
        if required:
            raise ValueError(f"Missing required integer for {field_name}")
        return default

    if isinstance(value, bool):
        raise ValueError(f"Invalid integer for {field_name}: {value}")

    if isinstance(value, (int,)):
        return int(value)

    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"Invalid integer for {field_name}: {value}")

    text = str(value).strip()
    if text == "":
        if required:
            raise ValueError(f"Missing required integer for {field_name}")
        return default

    if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
        return int(text)

    try:
        float_value = float(text)
    except ValueError:
        raise ValueError(f"Invalid integer for {field_name}: {text}")

    if float_value.is_integer():
        return int(float_value)

    raise ValueError(f"Invalid integer for {field_name}: {text}")


def parse_date(value, field_name):
    if pd.isna(value) or value == "":
        return None

    if isinstance(value, datetime):
        return value.strftime("%m-%d-%Y")

    try:
        parsed = pd.to_datetime(value, errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid date for {field_name}: {value}") from exc

    return parsed.strftime("%m-%d-%Y")


def now_date():
    return datetime.now().strftime("%m-%d-%Y")


def get_db_connection(db_path=DB_PATH):
    conn = sqlite3.connect(db_path, isolation_level=None, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_schema(conn)
    return conn


def ensure_schema(conn):
    if not os.path.exists(SCHEMA_FILE):
        return

    with open(SCHEMA_FILE, "r", encoding="utf-8") as fp:
        conn.executescript(fp.read())

    cols = [row[1] for row in conn.execute("PRAGMA table_info(inventory)").fetchall()]

    if "image_path" not in cols:
        conn.execute("ALTER TABLE inventory ADD COLUMN image_path TEXT")


def record_change(conn, part_number, action, diff, changed_by="system"):
    timestamp = now_date()
    conn.execute(
        "INSERT INTO changes (part_number, action, changed_by, timestamp, diff) VALUES (?, ?, ?, ?, ?)",
        (part_number, action, changed_by, timestamp, json.dumps(diff, default=str)),
    )


def fetch_inventory_item(conn, part_number):
    row = conn.execute("SELECT * FROM inventory WHERE part_number = ?", (part_number,)).fetchone()
    if row is None:
        return None
    return dict(row)


def is_record_different(existing, record):
    fields = ["description", "location", "quantity", "min_quantity", "customer"]
    for field in fields:
        if existing.get(field) != record.get(field):
            return True
    return False

def is_probe_record_different(existing, record):
    fields = ["description", "location", "quantity", "min_quantity", "customer"] + PROBE_OPTIONAL_COLUMNS
    for field in fields:
        if existing.get(field) != record.get(field):
            return True
    return False


def upsert_inventory(conn, record, changed_by="importer"):
    existing = fetch_inventory_item(conn, record["part_number"])
    if existing is None:
        conn.execute(
            "INSERT INTO inventory (part_number, description, location, quantity, min_quantity, customer, last_modify_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                record["part_number"],
                record.get("description"),
                record.get("location"),
                record["quantity"],
                record.get("min_quantity", 0),
                record.get("customer"),
                record["last_modify_date"],
            ),
        )
        record_change(conn, record["part_number"], "create", record, changed_by)
        return "inserted"

    if not is_record_different(existing, record):
        return "skipped"

    conn.execute(
        "UPDATE inventory SET description = ?, location = ?, quantity = ?, min_quantity = ?, customer = ?, last_modify_date = ? WHERE part_number = ?",
        (
            record.get("description"),
            record.get("location"),
            record["quantity"],
            record.get("min_quantity", 0),
            record.get("customer"),
            record["last_modify_date"],
            record["part_number"],
        ),
    )
    diff = {field: {"old": existing.get(field), "new": record.get(field)} for field in ["description", "location", "quantity", "min_quantity", "customer"] if existing.get(field) != record.get(field)}
    record_change(conn, record["part_number"], "update", diff, changed_by)
    return "updated"


def fetch_probe_inventory_item(conn, part_number):
    row = conn.execute("SELECT * FROM probe_inventory WHERE part_number = ?", (part_number,)).fetchone()
    if row is None:
        return None
    return dict(row)


def upsert_probe_inventory(conn, record, changed_by="importer"):
    existing = fetch_probe_inventory_item(conn, record["part_number"])
    if existing is None:
        conn.execute(
            """INSERT INTO probe_inventory (
                part_number, description, location, quantity, min_quantity, customer, last_modify_date,
                thread_size, sphere_dk, length, ml_ewl, tip_material, shaft_material, probe_type, link
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record["part_number"],
                record.get("description"),
                record.get("location"),
                record.get("quantity", 0),
                record.get("min_quantity", 0),
                record.get("customer"),
                record.get("last_modify_date"),
                record.get("thread_size"),
                record.get("sphere_dk"),
                record.get("length"),
                record.get("ml_ewl"),
                record.get("tip_material"),
                record.get("shaft_material"),
                record.get("probe_type"),
                record.get("link"),
            ),
        )
        record_change(conn, record["part_number"], "create", record, changed_by)
        return "inserted"

    if not is_probe_record_different(existing, record):
        return "skipped"

    conn.execute(
        """UPDATE probe_inventory SET
            description = ?, location = ?, quantity = ?, min_quantity = ?, customer = ?, last_modify_date = ?,
            thread_size = ?, sphere_dk = ?, length = ?, ml_ewl = ?,
            tip_material = ?, shaft_material = ?, probe_type = ?, link = ?
        WHERE part_number = ?""",
        (
            record.get("description"),
            record.get("location"),
            record.get("quantity", 0),
            record.get("min_quantity", 0),
            record.get("customer"),
            record.get("last_modify_date"),
            record.get("thread_size"),
            record.get("sphere_dk"),
            record.get("length"),
            record.get("ml_ewl"),
            record.get("tip_material"),
            record.get("shaft_material"),
            record.get("probe_type"),
            record.get("link"),
            record["part_number"],
        ),
    )
    all_fields = ["description", "location", "quantity", "min_quantity", "customer"] + PROBE_OPTIONAL_COLUMNS
    diff = {
        field: {"old": existing.get(field), "new": record.get(field)}
        for field in all_fields
        if existing.get(field) != record.get(field)
    }
    record_change(conn, record["part_number"], "update", diff, changed_by)
    return "updated"


def make_record(row, mapping, row_number):
    record = {}
    record["part_number"] = str(row[mapping["part_number"]]).strip()
    if not record["part_number"]:
        raise ValueError("Missing part_number")

    record["description"] = None
    record["location"] = None
    record["customer"] = None
    record["min_quantity"] = 0
    record["last_modify_date"] = now_date()

    if "description" in mapping:
        description = row[mapping["description"]]
        record["description"] = None if pd.isna(description) else str(description).strip()

    if "location" in mapping:
        location = row[mapping["location"]]
        record["location"] = None if pd.isna(location) else str(location).strip()

    if "customer" in mapping:
        customer = row[mapping["customer"]]
        record["customer"] = None if pd.isna(customer) else str(customer).strip()

    record["quantity"] = parse_int(row[mapping["quantity"]], "quantity", required=True)

    if "min_quantity" in mapping:
        record["min_quantity"] = parse_int(row[mapping["min_quantity"]], "min_quantity", required=False, default=0)

    if "last_modify_date" in mapping:
        parsed = parse_date(row[mapping["last_modify_date"]], "last_modify_date")
        if parsed is not None:
            record["last_modify_date"] = parsed

    return record

def make_probe_record(row, mapping, row_number):
    record = make_record(row, mapping, row_number)  # handles the shared fields

    for field in PROBE_OPTIONAL_COLUMNS:
        if field in mapping:
            value = row[mapping[field]]
            record[field] = None if pd.isna(value) else str(value).strip()
        else:
            record[field] = None

    return record

def import_excel(path, db_path=DB_PATH, changed_by="importer"):
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    conn = get_db_connection(db_path)

    summary = {
        "inventory_inserted": 0,
        "inventory_updated": 0,
        "inventory_skipped": 0,
        "probe_inserted": 0,
        "probe_updated": 0,
        "probe_skipped": 0,
        "invalid_rows": []
    }

    for sheet_name, df in sheets.items():
        sheet_lower = sheet_name.lower()

        for i, row in df.iterrows():
            try:
                if "probe" in sheet_lower:
                    record = make_probe_record(row, build_column_map(df.columns), i + 2)
                    action = upsert_probe_inventory(conn, record, changed_by)
                    summary[f"probe_{action}"] += 1
                else:
                    record = make_record(row, build_column_map(df.columns), i + 2)
                    action = upsert_inventory(conn, record, changed_by)
                    summary[f"inventory_{action}"] += 1

            except Exception as exc:
                summary["invalid_rows"].append({
                    "sheet": sheet_name,
                    "row": i + 2,
                    "reason": str(exc)
                })

    return summary

def inventory_query(conn, low_stock=False, location=None, customer=None, search=None):
    query = "SELECT * FROM inventory"
    clauses = []
    params = []

    if low_stock:
        clauses.append("quantity <= min_quantity AND min_quantity > 0")
    if location:
        clauses.append("location LIKE ?")
        params.append(f"%{location.strip()}%")
    if customer:
        clauses.append("LOWER(customer) LIKE LOWER(?)")
        params.append(f"%{customer.strip()}%")
    if search:
        clauses.append("""
            (LOWER(part_number) LIKE LOWER(?)
            OR LOWER(description) LIKE LOWER(?))
        """)
        params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY part_number ASC"
    return conn.execute(query, params).fetchall()


def probe_inventory_query(conn, low_stock=False, location=None, customer=None, search=None):
    query = "SELECT * FROM probe_inventory"
    clauses = []
    params = []

    if low_stock:
        clauses.append("quantity <= min_quantity AND min_quantity > 0")
    if location:
        clauses.append("location LIKE ?")
        params.append(f"%{location.strip()}%")
    if customer:
        clauses.append("LOWER(customer) LIKE LOWER(?)")
        params.append(f"%{customer.strip()}%")
    if search:
        clauses.append("""
            (LOWER(part_number) LIKE LOWER(?)
            OR LOWER(description) LIKE LOWER(?))
        """)
        params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY part_number ASC"
    return conn.execute(query, params).fetchall()


def export_rows(rows, output_path, fmt="csv"):
    df = pd.DataFrame([dict(row) for row in rows])
    if fmt == "xlsx":
        df.to_excel(output_path, index=False, engine="openpyxl")
    else:
        df.to_csv(output_path, index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inventory importer")
    parser.add_argument("file", help="Excel file to import")
    parser.add_argument("--db", default=DB_PATH, help="SQLite database path")
    args = parser.parse_args()
    summary = import_excel(args.file, db_path=args.db)

    logging.info(
        "Import completed: inventory_inserted=%d inventory_updated=%d inventory_skipped=%d probe_inserted=%d probe_updated=%d probe_skipped=%d invalid=%d",
        summary["inventory_inserted"],
        summary["inventory_updated"],
        summary["inventory_skipped"],
        summary["probe_inserted"],
        summary["probe_updated"],
        summary["probe_skipped"],
        len(summary["invalid_rows"]),
    )
    if summary["invalid_rows"]:
        logging.warning("Invalid rows: %s", summary["invalid_rows"])
