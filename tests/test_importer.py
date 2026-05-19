import os
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import import_inventory


class ImporterTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_inventory.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_excel(self, rows, filename="sample_inventory.xlsx"):
        path = os.path.join(self.temp_dir.name, filename)
        df = pd.DataFrame(rows)
        df.to_excel(path, index=False, engine="openpyxl")
        return path

    def test_import_creates_rows_and_skips_invalid(self):
        rows = [
            {
                "Part No": "ABC-123",
                "Description": "Widget",
                "Location": "A1",
                "Qty": 10,
                "Min Qty": 5,
                "Customer": "Acme",
            },
            {
                "Part Number": "XYZ-999",
                "Description": "Gadget",
                "Location": "B2",
                "Qty": "abc",
                "Min Qty": 2,
                "Customer": "Beta",
            },
        ]
        path = self.write_excel(rows)
        summary = import_inventory.import_excel(path, db_path=self.db_path)

        self.assertEqual(summary["inserted"], 1)
        self.assertEqual(summary["updated"], 0)
        self.assertEqual(summary["skipped"], 0)
        self.assertEqual(len(summary["invalid_rows"]), 1)

        conn = import_inventory.get_db_connection(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        self.assertEqual(count, 1)

    def test_import_updates_existing_row(self):
        rows = [
            {"Part No": "ABC-123", "Description": "Widget", "Location": "A1", "Qty": 10, "Min Qty": 5, "Customer": "Acme"},
        ]
        path = self.write_excel(rows, filename="initial.xlsx")
        import_inventory.import_excel(path, db_path=self.db_path)

        conn = import_inventory.get_db_connection(self.db_path)
        existing = conn.execute("SELECT * FROM inventory WHERE part_number = ?", ("ABC-123",)).fetchone()
        self.assertIsNotNone(existing)
        original_last_modify_date = existing["last_modify_date"]

        updated_rows = [
            {"Part No": "ABC-123", "Description": "Widget","Location": "A1", "Qty": 8, "Min Qty": 5, "Customer": "Acme"},
        ]
        update_path = self.write_excel(updated_rows, filename="updated.xlsx")
        summary = import_inventory.import_excel(update_path, db_path=self.db_path)

        self.assertEqual(summary["inserted"], 0)
        self.assertEqual(summary["updated"], 1)
        self.assertEqual(summary["skipped"], 0)

        updated = conn.execute("SELECT * FROM inventory WHERE part_number = ?", ("ABC-123",)).fetchone()
        self.assertEqual(updated["quantity"], 8)
        self.assertNotEqual(updated["last_modify_date"], original_last_modify_date)


if __name__ == "__main__":
    unittest.main()
