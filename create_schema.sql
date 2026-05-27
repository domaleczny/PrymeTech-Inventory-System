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
