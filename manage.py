import argparse
import csv
import os
import sqlite3

import pandas as pd

import import_inventory


def print_row(row):
    print(
        f"{row['part_number']}: {row['description'] or ''} | loc={row['location'] or ''} | qty={row['quantity']} | min={row['min_quantity']} | cust={row['customer'] or ''} | last_modify={row['last_modify_date']}"
    )


def cmd_import(args):
    summary = import_inventory.import_excel(args.file, db_path=args.db, changed_by='cli')
    print(f"Import summary: inserted={summary['inserted']} updated={summary['updated']} skipped={summary['skipped']} invalid={len(summary['invalid_rows'])}")
    if summary['invalid_rows']:
        print("Invalid rows:")
        for invalid in summary['invalid_rows']:
            print(f"  row {invalid['row']}: {invalid['reason']}")


def cmd_list(args):
    conn = import_inventory.get_db_connection(args.db)
    rows = import_inventory.inventory_query(
        conn,
        low_stock=args.low_stock,
        location=args.location,
        customer=args.customer,
        search=args.search,
    )
    if not rows:
        print("No inventory rows found.")
        return
    for row in rows:
        print_row(row)


def cmd_show(args):
    conn = import_inventory.get_db_connection(args.db)
    row = import_inventory.fetch_inventory_item(conn, args.part_number)
    if row is None:
        print(f"Item not found: {args.part_number}")
        return
    print_row(row)


def cmd_export(args):
    conn = import_inventory.get_db_connection(args.db)
    rows = import_inventory.inventory_query(
        conn,
        low_stock=args.low_stock,
        location=args.location,
        customer=args.customer,
        search=args.search,
    )
    fmt = args.format.lower()
    if fmt not in ("csv", "xlsx"):
        raise ValueError("Export format must be csv or xlsx")
    import_inventory.export_rows(rows, args.file, fmt=fmt)
    print(f"Exported {len(rows)} rows to {args.file}")


def cmd_bulk_update(args):
    summary = import_inventory.import_excel(args.file, db_path=args.db, changed_by='bulk-update')
    print(f"Bulk update summary: inserted={summary['inserted']} updated={summary['updated']} skipped={summary['skipped']} invalid={len(summary['invalid_rows'])}")
    if summary['invalid_rows']:
        print("Invalid rows:")
        for invalid in summary['invalid_rows']:
            print(f"  row {invalid['row']}: {invalid['reason']}")


def main():
    parser = argparse.ArgumentParser(description="Inventory management CLI")
    parser.add_argument("--db", default=import_inventory.DB_PATH, help="SQLite database path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    import_parser = subparsers.add_parser("import", help="Import inventory from Excel")
    import_parser.add_argument("file", help="Excel file path")
    import_parser.set_defaults(func=cmd_import)

    export_parser = subparsers.add_parser("export", help="Export inventory to file")
    export_parser.add_argument("file", help="Destination file path")
    export_parser.add_argument("--format", default="csv", choices=["csv", "xlsx"], help="Export format")
    export_parser.add_argument("--low-stock", action="store_true", help="Only include low stock items")
    export_parser.add_argument("--location", help="Filter by location")
    export_parser.add_argument("--customer", help="Filter by customer")
    export_parser.add_argument("--search", help="Search by part number or description")
    export_parser.set_defaults(func=cmd_export)

    show_parser = subparsers.add_parser("show", help="Show a single inventory item")
    show_parser.add_argument("part_number", help="Part number to show")
    show_parser.set_defaults(func=cmd_show)

    list_parser = subparsers.add_parser("list", help="List inventory items")
    list_parser.add_argument("--low-stock", action="store_true", help="Only list low stock items")
    list_parser.add_argument("--location", help="Filter by location")
    list_parser.add_argument("--customer", help="Filter by customer")
    list_parser.add_argument("--search", help="Search by term")
    list_parser.set_defaults(func=cmd_list)

    bulk_parser = subparsers.add_parser("bulk-update", help="Bulk update inventory from Excel")
    bulk_parser.add_argument("--file", required=True, help="Excel update file")
    bulk_parser.set_defaults(func=cmd_bulk_update)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
