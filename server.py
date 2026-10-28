"""Local-only Nexo Stock server with a SQLite database and same-origin API."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(os.environ.get("NEXO_STOCK_APP_DIR") or Path(__file__).resolve().parent).resolve()
DATA_DIR = Path(os.environ.get("NEXO_STOCK_DATA_DIR") or ROOT / "data").resolve()
DB_PATH = DATA_DIR / "control_stock.sqlite3"
SCHEMA_PATH = ROOT / "database" / "schema.sql"
HOST = "127.0.0.1"
PORT = int(os.environ.get("NEXO_STOCK_PORT", "8765"))

COLLECTIONS = {
    "nexo-stock-products": "products",
    "nexo-stock-movements": "movements",
    "nexo-stock-suppliers": "suppliers",
    "nexo-stock-vehicles": "vehicles",
    "nexo-stock-users": "users",
    "nexo-stock-settings": "settings",
    "nexo-stock-audit": "audit",
    "nexo-stock-email-simulations": "email_simulations",
}
IMPORT_ORDER = [
    "nexo-stock-suppliers",
    "nexo-stock-vehicles",
    "nexo-stock-products",
    "nexo-stock-movements",
    "nexo-stock-users",
    "nexo-stock-settings",
    "nexo-stock-audit",
    "nexo-stock-email-simulations",
]


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 10000")
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_meta'").fetchone():
        connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        if os.name != "nt":
            try:
                DB_PATH.chmod(0o600)
            except OSError:
                pass
    return connection


def json_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def money_minor(value: object) -> int:
    try:
        return round(float(value or 0) * 100)
    except (TypeError, ValueError):
        return 0


def upsert_collection(db: sqlite3.Connection, key: str, value: object) -> None:
    if key not in COLLECTIONS:
        raise ValueError("Colección desconocida")
    kind = COLLECTIONS[key]
    now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()

    if kind == "products":
        if not isinstance(value, list):
            raise ValueError("La colección de repuestos debe ser una lista")
        ids = []
        for item in value:
            product_id = int(item["id"])
            ids.append(product_id)
            db.execute(
                """INSERT INTO products(id,name,sku,category,supplier_name,cost_minor,minimum_stock,payload_json,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,sku=excluded.sku,category=excluded.category,
                   supplier_name=excluded.supplier_name,cost_minor=excluded.cost_minor,
                   minimum_stock=excluded.minimum_stock,payload_json=excluded.payload_json,updated_at=excluded.updated_at""",
                (product_id, str(item.get("name", "")), str(item.get("sku", "")), str(item.get("category", "")),
                 str(item.get("supplier", "")), money_minor(item.get("cost")), int(item.get("min", 0) or 0),
                 json_value(item), now),
            )
            db.execute("DELETE FROM product_codes WHERE product_id=?", (product_id,))
            codes = set([str(item.get("barcode", "") or "").strip(), *[str(c).strip() for c in item.get("barcodes", [])]])
            for code in filter(None, codes):
                db.execute("INSERT OR IGNORE INTO product_codes(product_id,code) VALUES(?,?)", (product_id, code))
            db.execute("DELETE FROM stock_balances WHERE product_id=?", (product_id,))
            stocks = item.get("workshopStock") or {}
            locations = item.get("storageByWorkshop") or {}
            for workshop in set(["Bella Unión", "Montevideo", *stocks.keys(), *locations.keys()]):
                place = locations.get(workshop) or {}
                db.execute(
                    "INSERT INTO stock_balances(product_id,workshop,quantity,cabinet,space) VALUES(?,?,?,?,?)",
                    (product_id, str(workshop), max(0, int(stocks.get(workshop, 0) or 0)),
                     str(place.get("cabinet", "")), str(place.get("space", ""))),
                )
        if ids:
            placeholders = ",".join("?" for _ in ids)
            db.execute(f"DELETE FROM products WHERE id NOT IN ({placeholders})", ids)
        else:
            db.execute("DELETE FROM products")

    elif kind == "movements":
        if not isinstance(value, list):
            raise ValueError("La colección de movimientos debe ser una lista")
        ids = []
        for item in value:
            movement_id = str(item["id"])
            ids.append(movement_id)
            product_id = item.get("productId")
            db.execute(
                """INSERT INTO movements(id,product_id,type,moved_at,quantity,unit_cost_minor,supplier_name,
                   source_workshop,destination_workshop,vehicle_name,reference,reason,breakdown_type,
                   breakdown_other,user_name,payload_json)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET product_id=excluded.product_id,type=excluded.type,
                   moved_at=excluded.moved_at,quantity=excluded.quantity,unit_cost_minor=excluded.unit_cost_minor,
                   supplier_name=excluded.supplier_name,source_workshop=excluded.source_workshop,
                   destination_workshop=excluded.destination_workshop,vehicle_name=excluded.vehicle_name,
                   reference=excluded.reference,reason=excluded.reason,breakdown_type=excluded.breakdown_type,
                   breakdown_other=excluded.breakdown_other,user_name=excluded.user_name,payload_json=excluded.payload_json""",
                (movement_id, int(product_id) if product_id is not None else None, str(item.get("type", "ajuste")),
                 str(item.get("date", now)), int(item.get("quantity", 0) or 0), money_minor(item.get("unitCost")),
                 str(item.get("supplier", "")), str(item.get("warehouse", "")), str(item.get("destination", "")),
                 str(item.get("vehicleId", "")), str(item.get("reference", "")), str(item.get("reason", "")),
                 str(item.get("breakdownType", "")), str(item.get("breakdownOther", "")),
                 str(item.get("user", "")), json_value(item)),
            )
        if ids:
            placeholders = ",".join("?" for _ in ids)
            db.execute(f"DELETE FROM movements WHERE id NOT IN ({placeholders})", ids)
        else:
            db.execute("DELETE FROM movements")

    elif kind == "suppliers":
        if not isinstance(value, list):
            raise ValueError("La colección de proveedores debe ser una lista")
        ids = []
        for item in value:
            supplier_id = str(item["id"])
            ids.append(supplier_id)
            db.execute(
                """INSERT INTO suppliers(id,name,tax_id,contact,phone,email,address,city,department,website,
                   payment_terms,notes,payload_json,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,tax_id=excluded.tax_id,contact=excluded.contact,
                   phone=excluded.phone,email=excluded.email,address=excluded.address,city=excluded.city,
                   department=excluded.department,website=excluded.website,payment_terms=excluded.payment_terms,
                   notes=excluded.notes,payload_json=excluded.payload_json,updated_at=excluded.updated_at""",
                (supplier_id, str(item.get("name", "")), str(item.get("taxId", "")), str(item.get("contact", "")),
                 str(item.get("phone", "")), str(item.get("email", "")), str(item.get("address", "")),
                 str(item.get("city", "")), str(item.get("department", "")), str(item.get("website", "")),
                 str(item.get("paymentTerms", "")), str(item.get("notes", "")), json_value(item), now),
            )
        if ids:
            placeholders = ",".join("?" for _ in ids)
            db.execute(f"DELETE FROM suppliers WHERE id NOT IN ({placeholders})", ids)
        else:
            db.execute("DELETE FROM suppliers")

    elif kind == "vehicles":
        if not isinstance(value, list):
            raise ValueError("La colección de vehículos debe ser una lista")
        names = []
        for item in value:
            name = str(item["name"])
            names.append(name)
            db.execute(
                """INSERT INTO vehicles(name,type,make,model,year,mileage,payload_json,updated_at)
                   VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(name) DO UPDATE SET type=excluded.type,make=excluded.make,model=excluded.model,
                   year=excluded.year,mileage=excluded.mileage,payload_json=excluded.payload_json,updated_at=excluded.updated_at""",
                (name, str(item.get("type", "Coche")), str(item.get("make", "")), str(item.get("model", "")),
                 int(item["year"]) if str(item.get("year", "")).isdigit() else None,
                 int(item["mileage"]) if str(item.get("mileage", "")).isdigit() else None, json_value(item), now),
            )
        if names:
            placeholders = ",".join("?" for _ in names)
            db.execute(f"DELETE FROM vehicles WHERE name NOT IN ({placeholders})", names)
        else:
            db.execute("DELETE FROM vehicles")

    elif kind == "users":
        if not isinstance(value, list):
            raise ValueError("La colección de usuarios debe ser una lista")
        ids = []
        for item in value:
            user_id = str(item["id"])
            ids.append(user_id)
            username = str(item.get("username") or user_id)
            db.execute(
                """INSERT INTO users(id,username,name,email,role,active,password_hash,password_salt,payload_json,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET username=excluded.username,name=excluded.name,email=excluded.email,
                   role=excluded.role,active=excluded.active,password_hash=excluded.password_hash,
                   password_salt=excluded.password_salt,payload_json=excluded.payload_json,updated_at=excluded.updated_at""",
                (user_id, username, str(item.get("name", "")), str(item.get("email", "")),
                 str(item.get("role", "Consulta")), int(bool(item.get("active", True))),
                 str(item.get("passwordHash", "")), str(item.get("passwordSalt", "")), json_value(item), now),
            )
        if ids:
            placeholders = ",".join("?" for _ in ids)
            db.execute(f"DELETE FROM users WHERE id NOT IN ({placeholders})", ids)
        else:
            db.execute("DELETE FROM users")

    elif kind == "settings":
        if not isinstance(value, dict):
            raise ValueError("La configuración debe ser un objeto")
        db.execute("DELETE FROM app_settings")
        for setting, setting_value in value.items():
            db.execute("INSERT INTO app_settings(key,value_json,updated_at) VALUES(?,?,?)",
                       (str(setting), json_value(setting_value), now))

    elif kind == "audit":
        if not isinstance(value, list):
            raise ValueError("La auditoría debe ser una lista")
        ids = []
        for item in value:
            entry_id = str(item["id"])
            ids.append(entry_id)
            db.execute(
                """INSERT INTO audit_entries(id,occurred_at,user_id,user_name,role,action,detail,payload_json)
                   VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET occurred_at=excluded.occurred_at,user_id=excluded.user_id,
                   user_name=excluded.user_name,role=excluded.role,action=excluded.action,detail=excluded.detail,
                   payload_json=excluded.payload_json""",
                (entry_id, str(item.get("date", now)), item.get("userId"), str(item.get("userName", "")),
                 str(item.get("role", "")), str(item.get("action", "")), str(item.get("detail", "")), json_value(item)),
            )
        if ids:
            placeholders = ",".join("?" for _ in ids)
            db.execute(f"DELETE FROM audit_entries WHERE id NOT IN ({placeholders})", ids)
        else:
            db.execute("DELETE FROM audit_entries")

    elif kind == "email_simulations":
        if not isinstance(value, list):
            raise ValueError("Los correos de prueba deben ser una lista")
        ids = []
        for item in value:
            email_id = str(item["id"])
            ids.append(email_id)
            db.execute(
                """INSERT INTO email_simulations(id,supplier_id,supplier_name,recipient,subject,body,simulated_at,payload_json)
                   VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET supplier_id=excluded.supplier_id,supplier_name=excluded.supplier_name,
                   recipient=excluded.recipient,subject=excluded.subject,body=excluded.body,
                   simulated_at=excluded.simulated_at,payload_json=excluded.payload_json""",
                (email_id, item.get("supplierId"), str(item.get("supplierName", "")), str(item.get("to", "")),
                 str(item.get("subject", "")), str(item.get("body", "")), str(item.get("date", now)), json_value(item)),
            )
        if ids:
            placeholders = ",".join("?" for _ in ids)
            db.execute(f"DELETE FROM email_simulations WHERE id NOT IN ({placeholders})", ids)
        else:
            db.execute("DELETE FROM email_simulations")

def read_collection(db: sqlite3.Connection, key: str) -> object | None:
    kind = COLLECTIONS[key]
    if kind in {"products", "movements", "suppliers", "vehicles", "users", "audit", "email_simulations"}:
        table = {
            "products": ("products", "id"),
            "movements": ("movements", "moved_at DESC"),
            "suppliers": ("suppliers", "name COLLATE NOCASE"),
            "vehicles": ("vehicles", "rowid"),
            "users": ("users", "rowid"),
            "audit": ("audit_entries", "occurred_at DESC"),
            "email_simulations": ("email_simulations", "simulated_at DESC"),
        }[kind]
        rows = db.execute(f"SELECT payload_json FROM {table[0]} ORDER BY {table[1]}").fetchall()
        return [json.loads(row[0]) for row in rows]
    if kind == "settings":
        rows = db.execute("SELECT key,value_json FROM app_settings ORDER BY key").fetchall()
        return {row[0]: json.loads(row[1]) for row in rows}
    return None


def get_bootstrap(db: sqlite3.Connection) -> dict:
    initialized = db.execute("SELECT value FROM app_meta WHERE key='initialized'").fetchone()
    collections = {}
    for key in COLLECTIONS:
        data = read_collection(db, key)
        if data is not None and (data or key == "nexo-stock-settings"):
            collections[key] = data
    return {"initialized": bool(initialized), "collections": collections}


class Handler(SimpleHTTPRequestHandler):
    server_version = "NexoStockLocal/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def send_json(self, status: int, payload: object) -> None:
        body = json_value(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> object:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 12_000_000:
            raise ValueError("Tamaño de solicitud inválido")
        return json.loads(self.rfile.read(length))

    def trusted_origin(self) -> bool:
        origin = self.headers.get("Origin")
        return not origin or origin in (f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            with closing(connect()) as db:
                self.send_json(200, {"ok": True, "database": "SQLite", "initialized": bool(db.execute("SELECT value FROM app_meta WHERE key='initialized'").fetchone())})
            return
        if path == "/api/bootstrap":
            with closing(connect()) as db:
                self.send_json(200, get_bootstrap(db))
            return
        super().do_GET()

    def do_POST(self) -> None:
        if not self.trusted_origin():
            self.send_json(403, {"error": "Origen no permitido"})
            return
        path = urlparse(self.path).path
        try:
            body = self.read_json()
            if path == "/api/import":
                collections = body.get("collections", {})
                if not isinstance(collections, dict):
                    raise ValueError("Formato de importación inválido")
                with closing(connect()) as db:
                    with db:
                        for key in IMPORT_ORDER:
                            if key in collections:
                                upsert_collection(db, key, collections[key])
                        db.execute("INSERT INTO app_meta(key,value) VALUES('initialized','1') ON CONFLICT(key) DO UPDATE SET value='1'")
                    self.send_json(200, {"ok": True, "bootstrap": get_bootstrap(db)})
                return
            if path == "/api/shutdown":
                self.send_json(200, {"ok": True})
                import threading
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if path.startswith("/api/collections/"):
                key = unquote(path.rsplit("/", 1)[-1])
                with closing(connect()) as db:
                    with db:
                        upsert_collection(db, key, body.get("value"))
                    self.send_json(200, {"ok": True})
                return
            self.send_json(404, {"error": "Ruta no encontrada"})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError, sqlite3.IntegrityError) as exc:
            self.send_json(400, {"error": str(exc)[:240]})
        except sqlite3.Error:
            self.send_json(500, {"error": "No se pudo guardar en la base de datos"})

    def log_message(self, format: str, *args) -> None:
        print("%s - %s" % (self.log_date_time_string(), format % args))


def main() -> None:
    connect().close()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Nexo Stock con SQLite listo en http://localhost:{PORT}")
    print(f"Base de datos local: {DB_PATH}")
    print("El servidor solo escucha conexiones de esta computadora (127.0.0.1).")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando Nexo Stock...")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
