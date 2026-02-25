import os, json, sqlite3, hashlib, base64, secrets, string, csv, io, shutil, glob
import urllib.request, urllib.error
from datetime import datetime, date, timedelta
from contextlib import contextmanager
from pathlib import Path
from collections import Counter
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

import sys
if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
else:
    APP_DIR = Path(__file__).parent

DB_PATH = APP_DIR / "accounts.db"
SALT_PATH = APP_DIR / ".salt"
BACKUP_DIR = APP_DIR / "backups"

CATS = ['AI对话','AI开发','AI绘图','办公AI','社交通讯','游戏娱乐','购物电商','金融支付','其他']
AS_MAP = {'inventory':'库存中','rented':'已出租','sold':'已售出','recycled':'已回收'}

def _get_or_create_salt():
    if SALT_PATH.exists(): return SALT_PATH.read_bytes()
    salt = secrets.token_bytes(16); SALT_PATH.write_bytes(salt); return salt

def derive_key(master_password):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=_get_or_create_salt(), iterations=480_000)
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

def encrypt(text, key):
    return Fernet(key).encrypt(text.encode()).decode() if text else ""

def decrypt(token, key):
    return Fernet(key).decrypt(token.encode()).decode() if token else ""

def hash_master(pwd):
    return hashlib.pbkdf2_hmac("sha256", pwd.encode(), _get_or_create_salt(), 480_000).hex()

SCHEMA = """
CREATE TABLE IF NOT EXISTS master (id INTEGER PRIMARY KEY CHECK(id=1), hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL DEFAULT '', name TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT '', username TEXT NOT NULL DEFAULT '', password_enc TEXT NOT NULL DEFAULT '',
    api_key_enc TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '', monthly_cost REAL NOT NULL DEFAULT 0,
    sell_price REAL NOT NULL DEFAULT 0, total_income REAL NOT NULL DEFAULT 0, expire_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active', account_status TEXT NOT NULL DEFAULT 'inventory',
    starred INTEGER NOT NULL DEFAULT 0, tags TEXT NOT NULL DEFAULT '', color_tag TEXT NOT NULL DEFAULT '',
    customer_name TEXT NOT NULL DEFAULT '', customer_contact TEXT NOT NULL DEFAULT '',
    auto_renew INTEGER NOT NULL DEFAULT 0, last_accessed TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
    deleted INTEGER NOT NULL DEFAULT 0, deleted_at TEXT NOT NULL DEFAULT '',
    workspace TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS password_history (id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, password_enc TEXT NOT NULL, changed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS activity_log (id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER, action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', ts TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS templates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, category TEXT NOT NULL DEFAULT '', platform TEXT NOT NULL DEFAULT '', url TEXT NOT NULL DEFAULT '', monthly_cost REAL NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS workspaces (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, icon TEXT NOT NULL DEFAULT '📁', ws_type TEXT NOT NULL DEFAULT 'personal', sort_order INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL DEFAULT '');
"""

NEW_COLS = [
    ("sell_price","REAL NOT NULL DEFAULT 0"),("total_income","REAL NOT NULL DEFAULT 0"),
    ("account_status","TEXT NOT NULL DEFAULT 'inventory'"),("color_tag","TEXT NOT NULL DEFAULT ''"),
    ("customer_name","TEXT NOT NULL DEFAULT ''"),("customer_contact","TEXT NOT NULL DEFAULT ''"),
    ("auto_renew","INTEGER NOT NULL DEFAULT 0"),("last_accessed","TEXT NOT NULL DEFAULT ''"),
    ("deleted","INTEGER NOT NULL DEFAULT 0"),("deleted_at","TEXT NOT NULL DEFAULT ''"),
    ("api_key_enc","TEXT NOT NULL DEFAULT ''"),("monthly_cost","REAL NOT NULL DEFAULT 0"),
    ("expire_date","TEXT NOT NULL DEFAULT ''"),("status","TEXT NOT NULL DEFAULT 'active'"),
    ("starred","INTEGER NOT NULL DEFAULT 0"),("tags","TEXT NOT NULL DEFAULT ''"),
    ("workspace","TEXT NOT NULL DEFAULT ''"),
]

WS_NEW_COLS = [("ws_type","TEXT NOT NULL DEFAULT 'personal'")]

@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH)); conn.row_factory = sqlite3.Row
    try: yield conn
    finally: conn.close()

def now_str(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_activity(aid, action, detail=""):
    with get_db() as c:
        c.execute("INSERT INTO activity_log(account_id,action,detail,ts) VALUES(?,?,?,?)",
                  (aid, action, detail, now_str())); c.commit()

def auto_backup(max_keep=5):
    BACKUP_DIR.mkdir(exist_ok=True)
    if not DB_PATH.exists(): return
    fn = f"auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    shutil.copy2(str(DB_PATH), str(BACKUP_DIR / fn))
    auto_files = sorted(BACKUP_DIR.glob("auto_*.db"), key=lambda p: p.stat().st_mtime)
    while len(auto_files) > max_keep:
        auto_files.pop(0).unlink(missing_ok=True)

def init_db():
    BACKUP_DIR.mkdir(exist_ok=True)
    with get_db() as conn:
        conn.executescript(SCHEMA)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(accounts)").fetchall()}
        for col, td in NEW_COLS:
            if col not in cols:
                conn.execute(f"ALTER TABLE accounts ADD COLUMN {col} {td}")
        ws_cols = {r[1] for r in conn.execute("PRAGMA table_info(workspaces)").fetchall()}
        for col, td in WS_NEW_COLS:
            if col not in ws_cols:
                conn.execute(f"ALTER TABLE workspaces ADD COLUMN {col} {td}")
        if conn.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0] == 0:
            n = now_str()
            conn.execute("INSERT INTO workspaces(name,icon,ws_type,sort_order,created_at) VALUES(?,?,?,?,?)", ("售卖空间","💰","merchant",0,n))
            conn.execute("INSERT INTO workspaces(name,icon,ws_type,sort_order,created_at) VALUES(?,?,?,?,?)", ("个人空间","👤","personal",1,n))
        if conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0] == 0:
            for t in [("DeepSeek","AI对话","DeepSeek","https://chat.deepseek.com",0),
                       ("ChatGPT Plus","AI对话","OpenAI","https://chat.openai.com",140),
                       ("Claude Pro","AI对话","Anthropic","https://claude.ai",140),
                       ("Cursor Pro","AI开发","Cursor","https://cursor.sh",140),
                       ("Midjourney","AI绘图","Midjourney","https://midjourney.com",210)]:
                conn.execute("INSERT INTO templates(name,category,platform,url,monthly_cost) VALUES(?,?,?,?,?)", t)
        conn.commit()

def is_initialized():
    with get_db() as c:
        return c.execute("SELECT 1 FROM master WHERE id=1").fetchone() is not None

def set_master_password(pwd):
    with get_db() as c:
        c.execute("INSERT INTO master(id,hash) VALUES(1,?)", (hash_master(pwd),)); c.commit()
    log_activity(None, "init", "系统初始化")
    return derive_key(pwd)

def verify_password(pwd):
    with get_db() as c:
        row = c.execute("SELECT hash FROM master WHERE id=1").fetchone()
    if not row: return None
    if hash_master(pwd) != row["hash"]: return None
    log_activity(None, "login", "登录")
    return derive_key(pwd)

def change_master_password(old_pwd, new_pwd, old_key):
    with get_db() as c:
        if hash_master(old_pwd) != c.execute("SELECT hash FROM master WHERE id=1").fetchone()["hash"]:
            return None
    nk = derive_key(new_pwd)
    with get_db() as c:
        for r in c.execute("SELECT id,password_enc,api_key_enc FROM accounts").fetchall():
            np = encrypt(decrypt(r["password_enc"], old_key), nk) if r["password_enc"] else ""
            na = encrypt(decrypt(r["api_key_enc"], old_key), nk) if r["api_key_enc"] else ""
            c.execute("UPDATE accounts SET password_enc=?,api_key_enc=? WHERE id=?", (np, na, r["id"]))
        for r in c.execute("SELECT id,password_enc FROM password_history").fetchall():
            np = encrypt(decrypt(r["password_enc"], old_key), nk) if r["password_enc"] else ""
            c.execute("UPDATE password_history SET password_enc=? WHERE id=?", (np, r["id"]))
        c.execute("UPDATE master SET hash=? WHERE id=1", (hash_master(new_pwd),)); c.commit()
    log_activity(None, "change_password", "修改主密码")
    return nk

def row_to_dict(r, key, include_password=True):
    exp = r["expire_date"]; days_left = None; auto_status = r["status"]
    if exp:
        try:
            dl = (datetime.strptime(exp, "%Y-%m-%d").date() - date.today()).days; days_left = dl
            if dl < 0: auto_status = "expired"
            elif dl <= 7: auto_status = "expiring"
        except ValueError: pass
    tags = [t.strip() for t in r["tags"].split(",") if t.strip()] if r["tags"] else []
    d = {c: r[c] for c in ["id","category","name","platform","username","url","monthly_cost",
         "sell_price","total_income","expire_date","status","account_status","starred","color_tag",
         "customer_name","customer_contact","auto_renew","last_accessed","notes","created_at","updated_at","workspace"]}
    d.update({"days_left": days_left, "status": auto_status, "starred": bool(r["starred"]),
              "auto_renew": bool(r["auto_renew"]), "tags": tags})
    if include_password:
        d["password"] = decrypt(r["password_enc"], key)
        d["api_key"] = decrypt(r["api_key_enc"], key)
    return d

def password_strength(pwd):
    if not pwd: return 0
    s = 0
    if len(pwd) >= 8: s += 1
    if len(pwd) >= 12: s += 1
    if any(c.isupper() for c in pwd): s += 1
    if any(c.isdigit() for c in pwd): s += 1
    if any(c in "!@#$%^&*_+-=?~`|\\/<>,.;:'\"{}" for c in pwd): s += 1
    return min(s, 4)

def list_workspaces():
    with get_db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM workspaces ORDER BY sort_order, id").fetchall()]

def get_workspace_type(ws_name):
    with get_db() as c:
        r = c.execute("SELECT ws_type FROM workspaces WHERE name=?", (ws_name,)).fetchone()
        return r["ws_type"] if r else "personal"

def create_workspace(name, icon, ws_type="personal"):
    with get_db() as c:
        if c.execute("SELECT 1 FROM workspaces WHERE name=?", (name,)).fetchone():
            raise ValueError("同名空间已存在")
        mx = c.execute("SELECT COALESCE(MAX(sort_order),0) FROM workspaces").fetchone()[0]
        cur = c.execute("INSERT INTO workspaces(name,icon,ws_type,sort_order,created_at) VALUES(?,?,?,?,?)",
                        (name, icon, ws_type, mx+1, now_str())); c.commit()
    return cur.lastrowid

def update_workspace(wid, name, icon, ws_type=None):
    with get_db() as c:
        old = c.execute("SELECT name FROM workspaces WHERE id=?", (wid,)).fetchone()
        if not old: return
        if ws_type:
            c.execute("UPDATE workspaces SET name=?, icon=?, ws_type=? WHERE id=?", (name, icon, ws_type, wid))
        else:
            c.execute("UPDATE workspaces SET name=?, icon=? WHERE id=?", (name, icon, wid))
        if old["name"] != name:
            c.execute("UPDATE accounts SET workspace=? WHERE workspace=?", (name, old["name"]))
        c.commit()

def delete_workspace(wid):
    with get_db() as c:
        cnt = c.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0]
        if cnt <= 1: raise ValueError("至少保留一个空间")
        ws = c.execute("SELECT name FROM workspaces WHERE id=?", (wid,)).fetchone()
        if not ws: return
        first = c.execute("SELECT name FROM workspaces WHERE id!=? ORDER BY sort_order, id LIMIT 1", (wid,)).fetchone()
        c.execute("UPDATE accounts SET workspace=? WHERE workspace=?", (first["name"], ws["name"]))
        c.execute("DELETE FROM workspaces WHERE id=?", (wid,)); c.commit()
        return first["name"]

def list_accounts(key, workspace=""):
    with get_db() as c:
        if workspace:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0 AND workspace=? ORDER BY starred DESC, category, name", (workspace,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0 ORDER BY starred DESC, category, name").fetchall()
    return [row_to_dict(r, key) for r in rows]

def create_account(data, key):
    now = now_str()
    tags = ",".join(data.get("tags",[])) if isinstance(data.get("tags"), list) else data.get("tags","")
    with get_db() as c:
        cur = c.execute("""INSERT INTO accounts(category,name,platform,username,password_enc,api_key_enc,url,
            monthly_cost,sell_price,total_income,expire_date,status,account_status,starred,tags,color_tag,
            customer_name,customer_contact,auto_renew,notes,workspace,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (data.get("category",""), data.get("name",""), data.get("platform",""), data.get("username",""),
             encrypt(data.get("password",""), key), encrypt(data.get("api_key",""), key), data.get("url",""),
             data.get("monthly_cost",0), data.get("sell_price",0), data.get("total_income",0),
             data.get("expire_date",""), "active", data.get("account_status","inventory"),
             1 if data.get("starred") else 0, tags, data.get("color_tag",""),
             data.get("customer_name",""), data.get("customer_contact",""),
             1 if data.get("auto_renew") else 0, data.get("notes",""), data.get("workspace",""), now, now)); c.commit()
    log_activity(cur.lastrowid, "create", f"创建: {data.get('name','')}")
    return cur.lastrowid

def update_account(aid, data, key):
    now = now_str()
    tags = ",".join(data.get("tags",[])) if isinstance(data.get("tags"), list) else data.get("tags","")
    with get_db() as c:
        old = c.execute("SELECT password_enc FROM accounts WHERE id=? AND deleted=0", (aid,)).fetchone()
        if not old: return
        old_pwd = decrypt(old["password_enc"], key) if old["password_enc"] else ""
        new_pwd = data.get("password","")
        if old_pwd and new_pwd and old_pwd != new_pwd:
            c.execute("INSERT INTO password_history(account_id,password_enc,changed_at) VALUES(?,?,?)", (aid, old["password_enc"], now))
        c.execute("""UPDATE accounts SET category=?,name=?,platform=?,username=?,password_enc=?,api_key_enc=?,url=?,
            monthly_cost=?,sell_price=?,total_income=?,expire_date=?,account_status=?,starred=?,tags=?,color_tag=?,
            customer_name=?,customer_contact=?,auto_renew=?,notes=?,workspace=?,updated_at=? WHERE id=?""",
            (data.get("category",""), data.get("name",""), data.get("platform",""), data.get("username",""),
             encrypt(new_pwd, key), encrypt(data.get("api_key",""), key), data.get("url",""),
             data.get("monthly_cost",0), data.get("sell_price",0), data.get("total_income",0),
             data.get("expire_date",""), data.get("account_status","inventory"),
             1 if data.get("starred") else 0, tags, data.get("color_tag",""),
             data.get("customer_name",""), data.get("customer_contact",""),
             1 if data.get("auto_renew") else 0, data.get("notes",""), data.get("workspace",""), now, aid)); c.commit()
    log_activity(aid, "update", f"更新: {data.get('name','')}")

def toggle_star(aid):
    with get_db() as c:
        r = c.execute("SELECT starred FROM accounts WHERE id=? AND deleted=0", (aid,)).fetchone()
        if r: c.execute("UPDATE accounts SET starred=? WHERE id=?", (0 if r["starred"] else 1, aid)); c.commit()

def mark_accessed(aid):
    with get_db() as c:
        c.execute("UPDATE accounts SET last_accessed=? WHERE id=?", (now_str(), aid)); c.commit()

def soft_delete(aid):
    with get_db() as c:
        r = c.execute("SELECT name FROM accounts WHERE id=? AND deleted=0", (aid,)).fetchone()
        c.execute("UPDATE accounts SET deleted=1, deleted_at=? WHERE id=?", (now_str(), aid)); c.commit()
    if r: log_activity(aid, "delete", f"删除: {r['name']}")

def list_recycle(key):
    with get_db() as c:
        rows = c.execute("SELECT * FROM accounts WHERE deleted=1 ORDER BY deleted_at DESC").fetchall()
    return [row_to_dict(r, key, include_password=False) for r in rows]

def restore_account(aid):
    with get_db() as c:
        c.execute("UPDATE accounts SET deleted=0, deleted_at='' WHERE id=?", (aid,)); c.commit()
    log_activity(aid, "restore", "恢复")

def permanent_delete(aid):
    with get_db() as c:
        c.execute("DELETE FROM accounts WHERE id=? AND deleted=1", (aid,))
        c.execute("DELETE FROM password_history WHERE account_id=?", (aid,)); c.commit()

def empty_recycle():
    with get_db() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM accounts WHERE deleted=1").fetchall()]
        c.execute("DELETE FROM accounts WHERE deleted=1")
        if ids:
            ph = ",".join("?" for _ in ids)
            c.execute(f"DELETE FROM password_history WHERE account_id IN ({ph})", ids)
        c.commit()

def get_stats(key, workspace=""):
    with get_db() as c:
        if workspace:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0 AND workspace=?", (workspace,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0").fetchall()
    total = len(rows); cats = {}; total_cost = 0.0
    expiring_soon = expired = active = starred_count = 0; today = date.today()
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
        total_cost += r["monthly_cost"] or 0
        if r["starred"]: starred_count += 1
        exp = r["expire_date"]
        if exp:
            try:
                dl = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
                if dl < 0: expired += 1
                elif dl <= 7: expiring_soon += 1
                else: active += 1
            except ValueError: active += 1
        else: active += 1
    with get_db() as c: recycle_count = c.execute("SELECT COUNT(*) FROM accounts WHERE deleted=1").fetchone()[0]
    return {"total": total, "categories": cats, "total_monthly_cost": round(total_cost, 2),
            "yearly_cost": round(total_cost * 12, 2), "active": active, "expiring_soon": expiring_soon,
            "expired": expired, "starred": starred_count, "recycle_count": recycle_count}

def security_analysis(key, workspace=""):
    with get_db() as c:
        if workspace:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0 AND workspace=?", (workspace,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0").fetchall()
    results = []; pwd_map = {}
    for r in rows:
        pwd = decrypt(r["password_enc"], key) if r["password_enc"] else ""
        strength = password_strength(pwd)
        if pwd: pwd_map.setdefault(pwd, []).append(r["id"])
        results.append({"id": r["id"], "name": r["name"], "platform": r["platform"], "category": r["category"],
                        "strength": strength, "weak": strength <= 1 and len(pwd) > 0, "empty": len(pwd) == 0,
                        "password_length": len(pwd)})
    dup_ids = set()
    for pwd, ids in pwd_map.items():
        if len(ids) > 1: dup_ids.update(ids)
    for r in results:
        r["duplicate"] = r["id"] in dup_ids
        health = 100
        if r["weak"]: health -= 40
        if r["duplicate"]: health -= 30
        if r["empty"]: health -= 50
        if r["password_length"] < 8 and r["password_length"] > 0: health -= 20
        r["health"] = max(0, health)
    weak_c = sum(1 for r in results if r["weak"])
    dup_c = sum(1 for r in results if r["duplicate"])
    empty_c = sum(1 for r in results if r["empty"])
    avg_h = round(sum(r["health"] for r in results) / len(results)) if results else 100
    return {"accounts": results, "summary": {"total": len(results), "weak": weak_c, "duplicate": dup_c, "empty": empty_c, "avg_health": avg_h}}

def finance_analysis(key, workspace=""):
    with get_db() as c:
        if workspace:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0 AND workspace=?", (workspace,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0").fetchall()
    total_cost = sum(r["monthly_cost"] or 0 for r in rows)
    total_sell = sum(r["sell_price"] or 0 for r in rows if r["account_status"] in ("rented","sold"))
    total_income = sum(r["total_income"] or 0 for r in rows)
    profit = total_sell - total_cost
    cat_costs = {}; status_counts = Counter()
    for r in rows:
        cat = r["category"] or "其他"
        cat_costs[cat] = cat_costs.get(cat, 0) + (r["monthly_cost"] or 0)
        status_counts[r["account_status"]] += 1
    return {"monthly_cost": round(total_cost, 2), "yearly_cost": round(total_cost * 12, 2),
            "monthly_sell": round(total_sell, 2), "monthly_profit": round(profit, 2),
            "yearly_profit": round(profit * 12, 2), "total_income": round(total_income, 2),
            "profit_rate": round(profit / total_cost * 100, 1) if total_cost > 0 else 0,
            "category_costs": cat_costs, "status_counts": dict(status_counts), "total_accounts": len(rows)}

def generate_password(length=16, uppercase=True, digits=True, symbols=True):
    length = max(8, min(length, 64)); chars = string.ascii_lowercase
    req = [secrets.choice(string.ascii_lowercase)]
    if uppercase: chars += string.ascii_uppercase; req.append(secrets.choice(string.ascii_uppercase))
    if digits: chars += string.digits; req.append(secrets.choice(string.digits))
    if symbols: chars += "!@#$%^&*_+-=?"; req.append(secrets.choice("!@#$%^&*_+-=?"))
    pool = req + [secrets.choice(chars) for _ in range(length - len(req))]
    secrets.SystemRandom().shuffle(pool)
    return "".join(pool)

def list_templates():
    with get_db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM templates ORDER BY category,name").fetchall()]

def get_logs(limit=100):
    with get_db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]

def export_data(key):
    with get_db() as c:
        rows = c.execute("SELECT * FROM accounts WHERE deleted=0 ORDER BY id").fetchall()
    data = [row_to_dict(r, key) for r in rows]
    content = json.dumps(data, ensure_ascii=False, indent=2)
    fn = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    (BACKUP_DIR / fn).write_text(content, encoding="utf-8")
    log_activity(None, "export", f"导出 {len(data)} 条")
    return content, fn

def import_json(items, key):
    now = now_str(); count = 0
    with get_db() as c:
        for item in items:
            tags = ",".join(item.get("tags",[])) if isinstance(item.get("tags"), list) else item.get("tags","")
            c.execute("""INSERT INTO accounts(category,name,platform,username,password_enc,api_key_enc,url,
                monthly_cost,sell_price,total_income,expire_date,account_status,starred,tags,color_tag,
                customer_name,customer_contact,auto_renew,notes,workspace,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item.get("category",""), item.get("name",""), item.get("platform",""), item.get("username",""),
                 encrypt(item.get("password",""), key), encrypt(item.get("api_key",""), key), item.get("url",""),
                 item.get("monthly_cost",0), item.get("sell_price",0), item.get("total_income",0),
                 item.get("expire_date",""), item.get("account_status","inventory"),
                 1 if item.get("starred") else 0, tags, item.get("color_tag",""),
                 item.get("customer_name",""), item.get("customer_contact",""),
                 1 if item.get("auto_renew") else 0, item.get("notes",""), item.get("workspace",""), now, now))
            count += 1
        c.commit()
    log_activity(None, "import", f"导入 {count} 条")
    return count

def import_csv_text(csv_text, key, workspace=""):
    now = now_str(); count = 0
    reader = csv.DictReader(io.StringIO(csv_text))
    with get_db() as c:
        for row in reader:
            c.execute("""INSERT INTO accounts(category,name,platform,username,password_enc,api_key_enc,url,
                monthly_cost,sell_price,expire_date,account_status,tags,customer_name,notes,workspace,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (row.get("category","其他"), row.get("name",""), row.get("platform",""), row.get("username",""),
                 encrypt(row.get("password",""), key), encrypt(row.get("api_key",""), key), row.get("url",""),
                 float(row.get("monthly_cost",0) or 0), float(row.get("sell_price",0) or 0),
                 row.get("expire_date",""), row.get("account_status","inventory"),
                 row.get("tags",""), row.get("customer_name",""), row.get("notes",""), workspace, now, now))
            count += 1
        c.commit()
    log_activity(None, "import_csv", f"CSV导入 {count} 条")
    return count

def get_password_history(aid, key):
    with get_db() as c:
        rows = c.execute("SELECT * FROM password_history WHERE account_id=? ORDER BY changed_at DESC", (aid,)).fetchall()
    return [{"id": r["id"], "password": decrypt(r["password_enc"], key), "changed_at": r["changed_at"]} for r in rows]

def migrate_from_old_db(old_db_path, old_salt_path, old_password, new_key, target_workspace="", skip_duplicates=True):
    old_salt = Path(old_salt_path).read_bytes()
    if len(old_salt) != 16:
        raise ValueError("无效的 .salt 文件（应为16字节）")

    old_kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=old_salt, iterations=480_000)
    old_key = base64.urlsafe_b64encode(old_kdf.derive(old_password.encode()))

    old_conn = sqlite3.connect(str(old_db_path))
    old_conn.row_factory = sqlite3.Row

    try:
        master_row = old_conn.execute("SELECT hash FROM master WHERE id=1").fetchone()
    except Exception:
        old_conn.close()
        raise ValueError("无效的数据库文件")

    if not master_row:
        old_conn.close()
        raise ValueError("旧数据库未初始化（未设置主密码）")

    expected_hash = hashlib.pbkdf2_hmac("sha256", old_password.encode(), old_salt, 480_000).hex()
    if expected_hash != master_row["hash"]:
        old_conn.close()
        raise ValueError("旧版本主密码错误")

    old_cols = {r[1] for r in old_conn.execute("PRAGMA table_info(accounts)").fetchall()}
    try:
        if "deleted" in old_cols:
            old_accounts = [dict(r) for r in old_conn.execute("SELECT * FROM accounts WHERE deleted=0").fetchall()]
        else:
            old_accounts = [dict(r) for r in old_conn.execute("SELECT * FROM accounts").fetchall()]
    except Exception:
        old_conn.close()
        raise ValueError("无法读取旧数据库账号数据")

    existing = set()
    if skip_duplicates:
        with get_db() as c:
            for r in c.execute("SELECT name, username, platform FROM accounts WHERE deleted=0").fetchall():
                existing.add((r["name"], r["username"], r["platform"]))

    ws_migrated = 0
    try:
        old_workspaces = [dict(r) for r in old_conn.execute("SELECT * FROM workspaces").fetchall()]
        with get_db() as c:
            existing_ws = {r["name"] for r in c.execute("SELECT name FROM workspaces").fetchall()}
            for ws in old_workspaces:
                ws_name = ws.get("name", "")
                if ws_name and ws_name not in existing_ws:
                    c.execute("INSERT INTO workspaces(name,icon,sort_order,created_at) VALUES(?,?,?,?)",
                              (ws_name, ws.get("icon", "📁"), ws.get("sort_order", 0), now_str()))
                    ws_migrated += 1
            c.commit()
    except Exception:
        pass

    now = now_str()
    migrated = skipped = 0
    errors = []
    id_map = {}

    with get_db() as c:
        for r in old_accounts:
            name = r.get("name", "")
            username = r.get("username", "")
            platform = r.get("platform", "")

            if skip_duplicates and (name, username, platform) in existing:
                skipped += 1
                continue

            try:
                pwd = ""
                if r.get("password_enc"):
                    try: pwd = Fernet(old_key).decrypt(r["password_enc"].encode()).decode()
                    except Exception: pass

                api_k = ""
                if r.get("api_key_enc"):
                    try: api_k = Fernet(old_key).decrypt(r["api_key_enc"].encode()).decode()
                    except Exception: pass

                ws = target_workspace or r.get("workspace", "") or ""

                cur = c.execute("""INSERT INTO accounts(category,name,platform,username,password_enc,api_key_enc,url,
                    monthly_cost,sell_price,total_income,expire_date,status,account_status,starred,tags,color_tag,
                    customer_name,customer_contact,auto_renew,notes,workspace,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (r.get("category", ""), name, platform, username,
                     encrypt(pwd, new_key), encrypt(api_k, new_key),
                     r.get("url", ""), float(r.get("monthly_cost", 0) or 0),
                     float(r.get("sell_price", 0) or 0), float(r.get("total_income", 0) or 0),
                     r.get("expire_date", ""), "active", r.get("account_status", "inventory"),
                     int(r.get("starred", 0) or 0), r.get("tags", ""), r.get("color_tag", ""),
                     r.get("customer_name", ""), r.get("customer_contact", ""),
                     int(r.get("auto_renew", 0) or 0), r.get("notes", ""), ws,
                     r.get("created_at", now), now))

                old_id = r.get("id")
                if old_id is not None:
                    id_map[old_id] = cur.lastrowid
                migrated += 1
            except Exception as e:
                errors.append(f"{name}: {e}")
        c.commit()

    ph_count = 0
    try:
        old_ph = [dict(r) for r in old_conn.execute("SELECT * FROM password_history").fetchall()]
        with get_db() as c:
            for ph in old_ph:
                new_acc_id = id_map.get(ph.get("account_id"))
                if new_acc_id is None:
                    continue
                if ph.get("password_enc"):
                    try: old_ph_pwd = Fernet(old_key).decrypt(ph["password_enc"].encode()).decode()
                    except Exception: continue
                else:
                    continue
                c.execute("INSERT INTO password_history(account_id,password_enc,changed_at) VALUES(?,?,?)",
                          (new_acc_id, encrypt(old_ph_pwd, new_key), ph.get("changed_at", now)))
                ph_count += 1
            c.commit()
    except Exception:
        pass

    old_conn.close()
    log_activity(None, "migrate", f"数据迁移: 导入 {migrated} 条, 跳过 {skipped} 条")
    return {"migrated": migrated, "skipped": skipped, "workspaces": ws_migrated, "password_history": ph_count, "errors": errors}


def check_api_key(provider, api_key, base_url=""):
    result = {"valid": False, "provider": provider, "models": [], "error": None, "info": {}}
    try:
        if provider == "deepseek":
            rq = urllib.request.Request("https://api.deepseek.com/models",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"})
            with urllib.request.urlopen(rq, timeout=15) as resp:
                data = json.loads(resp.read())
                result["valid"] = True
                result["models"] = sorted([m["id"] for m in data.get("data",[])])
            try:
                rq2 = urllib.request.Request("https://api.deepseek.com/user/balance",
                    headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"})
                with urllib.request.urlopen(rq2, timeout=10) as resp2:
                    bal = json.loads(resp2.read())
                    for bi in bal.get("balance_infos", []):
                        if bi.get("currency") == "CNY": result["info"]["balance_cny"] = bi.get("total_balance", "?")
            except Exception: pass
        elif provider == "openai_compatible":
            if not base_url: result["error"] = "请填写 Base URL"; return result
            rq = urllib.request.Request(f"{base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"})
            with urllib.request.urlopen(rq, timeout=15) as resp:
                data = json.loads(resp.read())
                result["valid"] = True
                result["models"] = sorted([m["id"] for m in data.get("data",[])])[:30]
    except urllib.error.HTTPError as e:
        result["error"] = {401: "API Key 无效或已过期", 403: "权限不足", 429: "请求频率超限"}.get(e.code, f"HTTP {e.code}")
    except Exception as e:
        result["error"] = str(e)
    return result
