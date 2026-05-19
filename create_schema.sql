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

CREATE TABLE IF NOT EXISTS changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  part_number TEXT NOT NULL,
  action TEXT NOT NULL,
  changed_by TEXT,
  timestamp TEXT NOT NULL,
  diff TEXT
);
