CREATE TABLE IF NOT EXISTS inventory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  part_number TEXT NOT NULL UNIQUE,
  description TEXT,
  location TEXT,
  quantity INTEGER NOT NULL DEFAULT 0,
  min_quantity INTEGER NOT NULL DEFAULT 0,
  customer TEXT,
  last_modify_date TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inventory_location ON inventory(location);

CREATE TABLE IF NOT EXISTS probe_inventory (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  part_number TEXT NOT NULL UNIQUE,
  description TEXT,
  location TEXT,
  quantity INTEGER NOT NULL DEFAULT 0,
  min_quantity INTEGER NOT NULL DEFAULT 0,
  customer TEXT,
  last_modify_date TEXT NOT NULL,
  thread_size TEXT,
  sphere_dk TEXT,
  length TEXT,
  ml_ewl TEXT,
  tip_material TEXT,
  shaft_material TEXT,
  probe_type TEXT,
  link TEXT
);

CREATE INDEX IF NOT EXISTS idx_probe_inventory_location ON probe_inventory(location);

CREATE TABLE IF NOT EXISTS changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  part_number TEXT NOT NULL,
  action TEXT NOT NULL,
  changed_by TEXT,
  timestamp TEXT NOT NULL,
  diff TEXT
);

CREATE TABLE IF NOT EXISTS inventory_locations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  location_code TEXT NOT NULL,
  description TEXT,
  last_updated TEXT
);

INSERT OR IGNORE INTO inventory_locations (id, location_code, description, last_updated) VALUES
  (1, 'A 1-1 / 12-4', 'Upstairs In Inventory', '11/27/2027'),
  (2, 'B 1-1 / 12-4', 'Upstairs In Inventory', '11/27/2023'),
  (3, 'C 1-1 / 12-4', 'Upstairs In Inventory', '11/27/2023'),
  (4, 'D 1-5 Shelf', 'Upstairs In Inventory', '11/27/2023'),
  (5, 'E 1-5 Shelf', 'Upstairs In Inventory', '11/27/2023'),
  (6, 'F 1-5 Shelf', 'Upstairs In Inventory', '11/27/2023'),
  (7, 'G 1-5 Shelf', 'Upstairs In Inventory', '11/27/2023'),
  (8, 'H 1-5 Shelf', 'Upstairs In Inventory', '11/27/2023'),
  (9, 'U-Table', 'Upstairs In Inventory Under Table w/ Lamp', '11/27/2023'),
  (10, 'Drawer', 'Downstairs In "LISTA" Hardware Drawer', '11/27/2023'),
  (11, 'LAB 1-1 / 1-8', 'Drawers Across From Contura "LISTA"', '11/28/2023'),
  (12, 'LAB 2-1 / 2-9', 'Drawers Next to Fabweaver 3D Printers "GLOBAL"', '11/28/2023');
