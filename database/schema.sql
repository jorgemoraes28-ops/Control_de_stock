PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_meta (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL UNIQUE COLLATE NOCASE,
  tax_id TEXT NOT NULL DEFAULT '',
  contact TEXT NOT NULL DEFAULT '',
  phone TEXT NOT NULL DEFAULT '',
  email TEXT NOT NULL DEFAULT '',
  address TEXT NOT NULL DEFAULT '',
  city TEXT NOT NULL DEFAULT '',
  department TEXT NOT NULL DEFAULT '',
  website TEXT NOT NULL DEFAULT '',
  payment_terms TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vehicles (
  name TEXT PRIMARY KEY COLLATE NOCASE,
  type TEXT NOT NULL DEFAULT 'Coche',
  make TEXT NOT NULL DEFAULT '',
  model TEXT NOT NULL DEFAULT '',
  year INTEGER,
  mileage INTEGER,
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  sku TEXT NOT NULL UNIQUE COLLATE NOCASE,
  category TEXT NOT NULL,
  supplier_name TEXT NOT NULL DEFAULT '',
  cost_minor INTEGER NOT NULL DEFAULT 0 CHECK(cost_minor >= 0),
  minimum_stock INTEGER NOT NULL DEFAULT 0 CHECK(minimum_stock >= 0),
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_supplier ON products(supplier_name);

CREATE TABLE IF NOT EXISTS product_codes (
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  code TEXT NOT NULL COLLATE NOCASE,
  PRIMARY KEY(product_id, code),
  UNIQUE(code)
);
CREATE INDEX IF NOT EXISTS idx_product_codes_product ON product_codes(product_id);

CREATE TABLE IF NOT EXISTS stock_balances (
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  workshop TEXT NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
  cabinet TEXT NOT NULL DEFAULT '',
  space TEXT NOT NULL DEFAULT '',
  PRIMARY KEY(product_id, workshop)
);
CREATE INDEX IF NOT EXISTS idx_stock_balances_workshop ON stock_balances(workshop, quantity);

CREATE TABLE IF NOT EXISTS movements (
  id TEXT PRIMARY KEY,
  product_id INTEGER REFERENCES products(id) ON DELETE SET NULL,
  type TEXT NOT NULL CHECK(type IN ('entrada','salida','ajuste','traslado')),
  moved_at TEXT NOT NULL,
  quantity INTEGER NOT NULL DEFAULT 0 CHECK(quantity >= 0),
  unit_cost_minor INTEGER NOT NULL DEFAULT 0 CHECK(unit_cost_minor >= 0),
  supplier_name TEXT NOT NULL DEFAULT '',
  source_workshop TEXT NOT NULL DEFAULT '',
  destination_workshop TEXT NOT NULL DEFAULT '',
  vehicle_name TEXT NOT NULL DEFAULT '',
  reference TEXT NOT NULL DEFAULT '',
  reason TEXT NOT NULL DEFAULT '',
  breakdown_type TEXT NOT NULL DEFAULT '',
  breakdown_other TEXT NOT NULL DEFAULT '',
  user_name TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_movements_date ON movements(moved_at DESC);
CREATE INDEX IF NOT EXISTS idx_movements_product_date ON movements(product_id, moved_at DESC);
CREATE INDEX IF NOT EXISTS idx_movements_vehicle_date ON movements(vehicle_name, moved_at DESC);
CREATE INDEX IF NOT EXISTS idx_movements_supplier_date ON movements(supplier_name, moved_at DESC);

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE COLLATE NOCASE,
  name TEXT NOT NULL,
  email TEXT NOT NULL DEFAULT '',
  role TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
  password_hash TEXT NOT NULL DEFAULT '',
  password_salt TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_entries (
  id TEXT PRIMARY KEY,
  occurred_at TEXT NOT NULL,
  user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
  user_name TEXT NOT NULL DEFAULT '',
  role TEXT NOT NULL DEFAULT '',
  action TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_entries_date ON audit_entries(occurred_at DESC);

CREATE TABLE IF NOT EXISTS email_simulations (
  id TEXT PRIMARY KEY,
  supplier_id TEXT REFERENCES suppliers(id) ON DELETE SET NULL,
  supplier_name TEXT NOT NULL DEFAULT '',
  recipient TEXT NOT NULL,
  subject TEXT NOT NULL,
  body TEXT NOT NULL,
  simulated_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_email_simulations_date ON email_simulations(simulated_at DESC);

CREATE TABLE IF NOT EXISTS workshops (
  name TEXT PRIMARY KEY COLLATE NOCASE,
  active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1))
);
INSERT OR IGNORE INTO workshops(name) VALUES ('Bella Unión'), ('Montevideo');

PRAGMA user_version = 1;
