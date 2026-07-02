import os
import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = r"C:\InventoryApp\inventory.db" 
EXPORT_DIR = r"C:\InventoryApp\exports"

os.makedirs(EXPORT_DIR, exist_ok=True)

def export_table(conn, table_name, writer):
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    df.to_excel(writer, sheet_name=table_name, index=False)

def main():
    conn = sqlite3.connect(DB_PATH)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(EXPORT_DIR, f"inventory_export_{timestamp}.xlsx")

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        export_table(conn, "inventory", writer)
        export_table(conn, "probe_inventory", writer)

    conn.close()
    print(f"Exported Excel file → {file_path}")

if __name__ == "__main__":
    main()