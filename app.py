import os, json, sqlite3, hashlib, base64, secrets, string, time, csv, io, tempfile, urllib.request, urllib.error
from datetime import datetime, date, timedelta
from contextlib import contextmanager
from pathlib import Path
from collections import Counter

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "accounts.db"
SALT_PATH = APP_DIR / ".salt"
BACKUP_DIR = APP_DIR / "backups"
AUTO_LOCK_SECONDS = 1800

app = FastAPI(title="账号管理工具")

# ==================== Encryption ====================

def _get_or_create_salt() -> bytes:
    if SALT_PATH.exists(): return SALT_PATH.read_bytes()
    salt = secrets.token_bytes(16); SALT_PATH.write_bytes(salt); return salt

def derive_key(master_password: str) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=_get_or_create_salt(), iterations=480_000)
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))

def encrypt(text: str, key: bytes) -> str:
    return Fernet(key).encrypt(text.encode()).decode() if text else ""

def decrypt(token: str, key: bytes) -> str:
    return Fernet(key).decrypt(token.encode()).decode() if token else ""

def hash_master(pwd: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pwd.encode(), _get_or_create_salt(), 480_000).hex()

# ==================== Database ====================

SCHEMA = """
CREATE TABLE IF NOT EXISTS master (id INTEGER PRIMARY KEY CHECK(id=1), hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    password_enc TEXT NOT NULL DEFAULT '',
    api_key_enc TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    monthly_cost REAL NOT NULL DEFAULT 0,
    sell_price REAL NOT NULL DEFAULT 0,
    total_income REAL NOT NULL DEFAULT 0,
    expire_date TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    account_status TEXT NOT NULL DEFAULT 'inventory',
    starred INTEGER NOT NULL DEFAULT 0,
    tags TEXT NOT NULL DEFAULT '',
    color_tag TEXT NOT NULL DEFAULT '',
    customer_name TEXT NOT NULL DEFAULT '',
    customer_contact TEXT NOT NULL DEFAULT '',
    auto_renew INTEGER NOT NULL DEFAULT 0,
    last_accessed TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS password_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    password_enc TEXT NOT NULL,
    changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER, action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, category TEXT NOT NULL DEFAULT '', platform TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '', monthly_cost REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS workspaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    icon TEXT NOT NULL DEFAULT '📁',
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT ''
);
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
    ("workspace","TEXT NOT NULL DEFAULT 'personal'"),
]

def init_db():
    with get_db() as conn:
        conn.executescript(SCHEMA)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(accounts)").fetchall()}
        for col, td in NEW_COLS:
            if col not in cols:
                conn.execute(f"ALTER TABLE accounts ADD COLUMN {col} {td}")
        if conn.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0] == 0:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute("INSERT INTO workspaces(name,icon,sort_order,created_at) VALUES(?,?,?,?)", ("售卖空间","💰",0,now))
            conn.execute("INSERT INTO workspaces(name,icon,sort_order,created_at) VALUES(?,?,?,?)", ("个人工作","👤",1,now))
        if conn.execute("SELECT COUNT(*) FROM templates").fetchone()[0] == 0:
            for t in [("DeepSeek","AI对话","DeepSeek","https://chat.deepseek.com",0),
                       ("DeepSeek API","AI开发","DeepSeek","https://platform.deepseek.com",0),
                       ("通义千问","AI对话","阿里云","https://tongyi.aliyun.com",0),
                       ("阿里 DashScope API","AI开发","阿里云","https://dashscope.console.aliyun.com",0),
                       ("ChatGPT Plus","AI对话","OpenAI","https://chat.openai.com",140),
                       ("Claude Pro","AI对话","Anthropic","https://claude.ai",140),
                       ("Midjourney","AI绘图","Midjourney","https://midjourney.com",210),
                       ("Cursor Pro","AI开发","Cursor","https://cursor.sh",140),
                       ("Notion AI","办公AI","Notion","https://notion.so",70),
                       ("Perplexity Pro","办公AI","Perplexity","https://perplexity.ai",140)]:
                conn.execute("INSERT INTO templates(name,category,platform,url,monthly_cost) VALUES(?,?,?,?,?)", t)
        conn.commit()

@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH)); conn.row_factory = sqlite3.Row
    try: yield conn
    finally: conn.close()

def log_activity(aid, action, detail=""):
    with get_db() as c:
        c.execute("INSERT INTO activity_log(account_id,action,detail,ts) VALUES(?,?,?,?)",
                  (aid, action, detail, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))); c.commit()

# ==================== Session ====================

_session = {"key": None, "last_active": 0}

def require_auth():
    if not _session["key"]: raise HTTPException(401, "未登录")
    if time.time() - _session["last_active"] > AUTO_LOCK_SECONDS:
        _session["key"] = None; raise HTTPException(401, "会话已过期")
    _session["last_active"] = time.time()
    return _session["key"]

# ==================== Helpers ====================

def now_str(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

# ==================== Routes ====================

@app.on_event("startup")
def startup(): init_db(); BACKUP_DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def index(): return HTMLResponse((APP_DIR / "templates" / "index.html").read_text(encoding="utf-8"))

@app.get("/api/status")
def status():
    with get_db() as c: row = c.execute("SELECT hash FROM master WHERE id=1").fetchone()
    logged = _session["key"] is not None
    if logged and time.time() - _session["last_active"] > AUTO_LOCK_SECONDS:
        _session["key"] = None; logged = False
    return {"initialized": row is not None, "logged_in": logged}

@app.post("/api/init")
async def init_master(req: Request):
    b = await req.json(); pwd = b.get("password","")
    if len(pwd) < 4: raise HTTPException(400, "主密码至少4位")
    with get_db() as c:
        if c.execute("SELECT 1 FROM master WHERE id=1").fetchone(): raise HTTPException(400, "已设置")
        c.execute("INSERT INTO master(id,hash) VALUES(1,?)", (hash_master(pwd),)); c.commit()
    _session["key"] = derive_key(pwd); _session["last_active"] = time.time()
    log_activity(None, "init", "系统初始化"); return {"ok": True}

@app.post("/api/login")
async def login(req: Request):
    b = await req.json(); pwd = b.get("password","")
    with get_db() as c: row = c.execute("SELECT hash FROM master WHERE id=1").fetchone()
    if not row: raise HTTPException(400, "未设置主密码")
    if hash_master(pwd) != row["hash"]: raise HTTPException(403, "主密码错误")
    _session["key"] = derive_key(pwd); _session["last_active"] = time.time()
    log_activity(None, "login", "登录"); return {"ok": True}

@app.post("/api/logout")
def logout(): log_activity(None, "logout", "登出"); _session["key"] = None; return {"ok": True}

@app.post("/api/change-password")
async def change_password(req: Request, key: bytes = Depends(require_auth)):
    b = await req.json(); old_p, new_p = b.get("old_password",""), b.get("new_password","")
    if len(new_p) < 4: raise HTTPException(400, "新密码至少4位")
    with get_db() as c:
        if hash_master(old_p) != c.execute("SELECT hash FROM master WHERE id=1").fetchone()["hash"]:
            raise HTTPException(403, "原密码错误")
    ok, nk = derive_key(old_p), derive_key(new_p)
    with get_db() as c:
        for r in c.execute("SELECT id,password_enc,api_key_enc FROM accounts").fetchall():
            np = encrypt(decrypt(r["password_enc"], ok), nk) if r["password_enc"] else ""
            na = encrypt(decrypt(r["api_key_enc"], ok), nk) if r["api_key_enc"] else ""
            c.execute("UPDATE accounts SET password_enc=?,api_key_enc=? WHERE id=?", (np, na, r["id"]))
        for r in c.execute("SELECT id,password_enc FROM password_history").fetchall():
            np = encrypt(decrypt(r["password_enc"], ok), nk) if r["password_enc"] else ""
            c.execute("UPDATE password_history SET password_enc=? WHERE id=?", (np, r["id"]))
        c.execute("UPDATE master SET hash=? WHERE id=1", (hash_master(new_p),)); c.commit()
    _session["key"] = nk; log_activity(None, "change_password", "修改主密码"); return {"ok": True}

# ==================== Workspaces ====================

@app.get("/api/workspaces")
def list_workspaces(key: bytes = Depends(require_auth)):
    with get_db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM workspaces ORDER BY sort_order, id").fetchall()]

@app.post("/api/workspaces")
async def create_workspace(req: Request, key: bytes = Depends(require_auth)):
    b = await req.json(); name = b.get("name","").strip(); icon = b.get("icon","📁")
    if not name: raise HTTPException(400, "名称不能为空")
    with get_db() as c:
        if c.execute("SELECT 1 FROM workspaces WHERE name=?", (name,)).fetchone():
            raise HTTPException(400, "同名空间已存在")
        mx = c.execute("SELECT COALESCE(MAX(sort_order),0) FROM workspaces").fetchone()[0]
        cur = c.execute("INSERT INTO workspaces(name,icon,sort_order,created_at) VALUES(?,?,?,?)",
                        (name, icon, mx + 1, now_str())); c.commit()
    return {"ok": True, "id": cur.lastrowid}

@app.put("/api/workspaces/{wid}")
async def update_workspace(wid: int, req: Request, key: bytes = Depends(require_auth)):
    b = await req.json(); name = b.get("name","").strip(); icon = b.get("icon","📁")
    if not name: raise HTTPException(400, "名称不能为空")
    with get_db() as c:
        old = c.execute("SELECT name FROM workspaces WHERE id=?", (wid,)).fetchone()
        if not old: raise HTTPException(404)
        dup = c.execute("SELECT 1 FROM workspaces WHERE name=? AND id!=?", (name, wid)).fetchone()
        if dup: raise HTTPException(400, "同名空间已存在")
        c.execute("UPDATE workspaces SET name=?, icon=? WHERE id=?", (name, icon, wid))
        if old["name"] != name:
            c.execute("UPDATE accounts SET workspace=? WHERE workspace=?", (name, old["name"]))
        c.commit()
    return {"ok": True}

@app.delete("/api/workspaces/{wid}")
def delete_workspace(wid: int, key: bytes = Depends(require_auth)):
    with get_db() as c:
        cnt = c.execute("SELECT COUNT(*) FROM workspaces").fetchone()[0]
        if cnt <= 1: raise HTTPException(400, "至少保留一个空间")
        ws = c.execute("SELECT name FROM workspaces WHERE id=?", (wid,)).fetchone()
        if not ws: raise HTTPException(404)
        first = c.execute("SELECT name FROM workspaces WHERE id!=? ORDER BY sort_order, id LIMIT 1", (wid,)).fetchone()
        c.execute("UPDATE accounts SET workspace=? WHERE workspace=?", (first["name"], ws["name"]))
        c.execute("DELETE FROM workspaces WHERE id=?", (wid,)); c.commit()
    return {"ok": True, "moved_to": first["name"]}

# ==================== Accounts CRUD ====================

def _acc_fields():
    return ["category","name","platform","username","url","monthly_cost","sell_price","total_income",
            "expire_date","account_status","starred","tags","color_tag","customer_name",
            "customer_contact","auto_renew","notes"]

@app.get("/api/accounts")
def list_accounts(workspace: str = "", key: bytes = Depends(require_auth)):
    with get_db() as c:
        if workspace:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0 AND workspace=? ORDER BY starred DESC, category, name", (workspace,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0 ORDER BY starred DESC, category, name").fetchall()
    return [row_to_dict(r, key) for r in rows]

@app.post("/api/accounts")
async def create_account(req: Request, key: bytes = Depends(require_auth)):
    b = await req.json(); now = now_str()
    tags = ",".join(b.get("tags",[])) if isinstance(b.get("tags"), list) else b.get("tags","")
    with get_db() as c:
        cur = c.execute("""INSERT INTO accounts(category,name,platform,username,password_enc,api_key_enc,url,
            monthly_cost,sell_price,total_income,expire_date,status,account_status,starred,tags,color_tag,
            customer_name,customer_contact,auto_renew,notes,workspace,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (b.get("category",""), b.get("name",""), b.get("platform",""), b.get("username",""),
             encrypt(b.get("password",""), key), encrypt(b.get("api_key",""), key), b.get("url",""),
             b.get("monthly_cost",0), b.get("sell_price",0), b.get("total_income",0),
             b.get("expire_date",""), "active", b.get("account_status","inventory"),
             1 if b.get("starred") else 0, tags, b.get("color_tag",""),
             b.get("customer_name",""), b.get("customer_contact",""),
             1 if b.get("auto_renew") else 0, b.get("notes",""), b.get("workspace",""), now, now)); c.commit()
    log_activity(cur.lastrowid, "create", f"创建: {b.get('name','')}"); return {"ok": True, "id": cur.lastrowid}

@app.put("/api/accounts/{aid}")
async def update_account(aid: int, req: Request, key: bytes = Depends(require_auth)):
    b = await req.json(); now = now_str()
    tags = ",".join(b.get("tags",[])) if isinstance(b.get("tags"), list) else b.get("tags","")
    with get_db() as c:
        old = c.execute("SELECT password_enc FROM accounts WHERE id=? AND deleted=0", (aid,)).fetchone()
        if not old: raise HTTPException(404)
        old_pwd = decrypt(old["password_enc"], key) if old["password_enc"] else ""
        new_pwd = b.get("password","")
        if old_pwd and new_pwd and old_pwd != new_pwd:
            c.execute("INSERT INTO password_history(account_id,password_enc,changed_at) VALUES(?,?,?)",
                      (aid, old["password_enc"], now))
        c.execute("""UPDATE accounts SET category=?,name=?,platform=?,username=?,password_enc=?,api_key_enc=?,url=?,
            monthly_cost=?,sell_price=?,total_income=?,expire_date=?,account_status=?,starred=?,tags=?,color_tag=?,
            customer_name=?,customer_contact=?,auto_renew=?,notes=?,workspace=?,updated_at=? WHERE id=?""",
            (b.get("category",""), b.get("name",""), b.get("platform",""), b.get("username",""),
             encrypt(new_pwd, key), encrypt(b.get("api_key",""), key), b.get("url",""),
             b.get("monthly_cost",0), b.get("sell_price",0), b.get("total_income",0),
             b.get("expire_date",""), b.get("account_status","inventory"),
             1 if b.get("starred") else 0, tags, b.get("color_tag",""),
             b.get("customer_name",""), b.get("customer_contact",""),
             1 if b.get("auto_renew") else 0, b.get("notes",""), b.get("workspace",""), now, aid)); c.commit()
    log_activity(aid, "update", f"更新: {b.get('name','')}"); return {"ok": True}

@app.patch("/api/accounts/{aid}/star")
def toggle_star(aid: int, key: bytes = Depends(require_auth)):
    with get_db() as c:
        r = c.execute("SELECT starred FROM accounts WHERE id=? AND deleted=0", (aid,)).fetchone()
        if not r: raise HTTPException(404)
        c.execute("UPDATE accounts SET starred=? WHERE id=?", (0 if r["starred"] else 1, aid)); c.commit()
    return {"ok": True}

@app.patch("/api/accounts/{aid}/access")
def mark_accessed(aid: int, key: bytes = Depends(require_auth)):
    with get_db() as c:
        c.execute("UPDATE accounts SET last_accessed=? WHERE id=?", (now_str(), aid)); c.commit()
    return {"ok": True}

@app.delete("/api/accounts/{aid}")
def soft_delete(aid: int, key: bytes = Depends(require_auth)):
    with get_db() as c:
        r = c.execute("SELECT name FROM accounts WHERE id=? AND deleted=0", (aid,)).fetchone()
        c.execute("UPDATE accounts SET deleted=1, deleted_at=? WHERE id=?", (now_str(), aid)); c.commit()
    log_activity(aid, "delete", f"删除: {r['name'] if r else aid}"); return {"ok": True}

@app.post("/api/accounts/batch-delete")
async def batch_delete(req: Request, key: bytes = Depends(require_auth)):
    ids = (await req.json()).get("ids", [])
    if not ids: return {"ok": True}
    ph = ",".join("?" for _ in ids)
    with get_db() as c:
        c.execute(f"UPDATE accounts SET deleted=1, deleted_at=? WHERE id IN ({ph})", [now_str()] + ids); c.commit()
    log_activity(None, "batch_delete", f"批量删除 {len(ids)} 个"); return {"ok": True, "deleted": len(ids)}

@app.post("/api/accounts/batch-update-price")
async def batch_update_price(req: Request, key: bytes = Depends(require_auth)):
    b = await req.json(); ids = b.get("ids",[]); field = b.get("field","monthly_cost"); value = b.get("value",0)
    if field not in ("monthly_cost","sell_price"): raise HTTPException(400)
    ph = ",".join("?" for _ in ids)
    with get_db() as c:
        c.execute(f"UPDATE accounts SET {field}=?, updated_at=? WHERE id IN ({ph})", [value, now_str()] + ids); c.commit()
    return {"ok": True}

# ==================== Recycle Bin ====================

@app.get("/api/recycle")
def list_recycle(key: bytes = Depends(require_auth)):
    with get_db() as c:
        rows = c.execute("SELECT * FROM accounts WHERE deleted=1 ORDER BY deleted_at DESC").fetchall()
    return [row_to_dict(r, key, include_password=False) for r in rows]

@app.post("/api/recycle/{aid}/restore")
def restore_account(aid: int, key: bytes = Depends(require_auth)):
    with get_db() as c:
        c.execute("UPDATE accounts SET deleted=0, deleted_at='' WHERE id=?", (aid,)); c.commit()
    log_activity(aid, "restore", "从回收站恢复"); return {"ok": True}

@app.delete("/api/recycle/{aid}")
def permanent_delete(aid: int, key: bytes = Depends(require_auth)):
    with get_db() as c:
        c.execute("DELETE FROM accounts WHERE id=? AND deleted=1", (aid,))
        c.execute("DELETE FROM password_history WHERE account_id=?", (aid,)); c.commit()
    return {"ok": True}

@app.post("/api/recycle/empty")
def empty_recycle(key: bytes = Depends(require_auth)):
    with get_db() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM accounts WHERE deleted=1").fetchall()]
        c.execute("DELETE FROM accounts WHERE deleted=1")
        if ids:
            ph = ",".join("?" for _ in ids)
            c.execute(f"DELETE FROM password_history WHERE account_id IN ({ph})", ids)
        c.commit()
    return {"ok": True}

# ==================== Password History ====================

@app.get("/api/accounts/{aid}/password-history")
def get_pwd_history(aid: int, key: bytes = Depends(require_auth)):
    with get_db() as c:
        rows = c.execute("SELECT * FROM password_history WHERE account_id=? ORDER BY changed_at DESC", (aid,)).fetchall()
    return [{"id": r["id"], "password": decrypt(r["password_enc"], key), "changed_at": r["changed_at"]} for r in rows]

# ==================== Security Analysis ====================

@app.get("/api/security")
def security_analysis(workspace: str = "", key: bytes = Depends(require_auth)):
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
        results.append({"id": r["id"], "name": r["name"], "platform": r["platform"],
                        "category": r["category"], "strength": strength,
                        "weak": strength <= 1 and len(pwd) > 0, "empty": len(pwd) == 0,
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
    weak_count = sum(1 for r in results if r["weak"])
    dup_count = sum(1 for r in results if r["duplicate"])
    empty_count = sum(1 for r in results if r["empty"])
    avg_health = round(sum(r["health"] for r in results) / len(results)) if results else 100
    return {"accounts": results, "summary": {"total": len(results), "weak": weak_count,
            "duplicate": dup_count, "empty": empty_count, "avg_health": avg_health}}

# ==================== Financial Analysis ====================

@app.get("/api/finance")
def finance_analysis(workspace: str = "", key: bytes = Depends(require_auth)):
    with get_db() as c:
        if workspace:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0 AND workspace=?", (workspace,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0").fetchall()
    total_cost = sum(r["monthly_cost"] or 0 for r in rows)
    total_sell = sum(r["sell_price"] or 0 for r in rows if r["account_status"] in ("rented","sold"))
    total_income = sum(r["total_income"] or 0 for r in rows)
    profit = total_sell - total_cost
    cat_costs = {}; cat_income = {}; status_counts = Counter()
    for r in rows:
        cat = r["category"] or "其他"
        cat_costs[cat] = cat_costs.get(cat, 0) + (r["monthly_cost"] or 0)
        cat_income[cat] = cat_income.get(cat, 0) + (r["sell_price"] or 0)
        status_counts[r["account_status"]] += 1
    return {
        "monthly_cost": round(total_cost, 2), "yearly_cost": round(total_cost * 12, 2),
        "monthly_sell": round(total_sell, 2), "monthly_profit": round(profit, 2),
        "yearly_profit": round(profit * 12, 2), "total_income": round(total_income, 2),
        "profit_rate": round(profit / total_cost * 100, 1) if total_cost > 0 else 0,
        "category_costs": cat_costs, "category_income": cat_income,
        "status_counts": dict(status_counts), "total_accounts": len(rows),
    }

# ==================== Stats ====================

@app.get("/api/stats")
def get_stats(workspace: str = "", key: bytes = Depends(require_auth)):
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
    recycle_count = c.execute("SELECT COUNT(*) FROM accounts WHERE deleted=1").fetchone()[0] if False else 0
    with get_db() as c: recycle_count = c.execute("SELECT COUNT(*) FROM accounts WHERE deleted=1").fetchone()[0]
    return {"total": total, "categories": cats, "total_monthly_cost": round(total_cost, 2),
            "yearly_cost": round(total_cost * 12, 2), "active": active, "expiring_soon": expiring_soon,
            "expired": expired, "starred": starred_count, "recycle_count": recycle_count}

# ==================== API Key Check ====================

@app.post("/api/check-api-key")
async def check_api_key(req: Request, key: bytes = Depends(require_auth)):
    b = await req.json(); provider = b.get("provider","deepseek"); api_key = b.get("api_key","")
    if not api_key: raise HTTPException(400, "请提供 API Key")
    result = {"valid": False, "provider": provider, "models": [], "error": None, "info": {}}
    try:
        if provider == "deepseek":
            rq = urllib.request.Request("https://api.deepseek.com/models",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"})
            with urllib.request.urlopen(rq, timeout=15) as resp:
                data = json.loads(resp.read())
                models = sorted([m["id"] for m in data.get("data",[])])
                result["valid"] = True
                result["models"] = models
                result["info"]["total_models"] = len(models)
                v3 = [m for m in models if "v3" in m.lower()]
                result["info"]["has_v3"] = len(v3) > 0
            try:
                rq2 = urllib.request.Request("https://api.deepseek.com/user/balance",
                    headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"})
                with urllib.request.urlopen(rq2, timeout=10) as resp2:
                    bal = json.loads(resp2.read())
                    if bal.get("is_available") is not None:
                        result["info"]["is_available"] = bal["is_available"]
                    infos = bal.get("balance_infos", [])
                    for bi in infos:
                        if bi.get("currency") == "CNY":
                            result["info"]["balance_cny"] = bi.get("total_balance", "未知")
                        elif bi.get("currency") == "USD":
                            result["info"]["balance_usd"] = bi.get("total_balance", "未知")
            except Exception:
                pass
        elif provider == "aliyun":
            body = json.dumps({
                "model": "qwen-turbo",
                "input": {"messages": [{"role": "user", "content": "hi"}]},
                "parameters": {"max_tokens": 1}
            }).encode()
            rq = urllib.request.Request("https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                data=body,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
            with urllib.request.urlopen(rq, timeout=15) as resp:
                data = json.loads(resp.read())
                if data.get("output"):
                    result["valid"] = True
                    result["info"]["model_used"] = data.get("model", "qwen-turbo")
                    result["info"]["usage"] = data.get("usage", {})
                    result["info"]["request_id"] = data.get("request_id", "")
                elif data.get("code"):
                    if data["code"] == "InvalidApiKey":
                        result["error"] = "API Key 无效"
                    else:
                        result["valid"] = True
                        result["info"]["note"] = data.get("message", "")
            try:
                rq2 = urllib.request.Request("https://dashscope.aliyuncs.com/api/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"})
                with urllib.request.urlopen(rq2, timeout=10) as resp2:
                    mdata = json.loads(resp2.read())
                    models = [m.get("model_id","") for m in mdata.get("data",{}).get("models",[])]
                    result["models"] = sorted(models)[:30]
                    result["info"]["total_models"] = len(models)
            except Exception:
                pass
        elif provider == "openai_compatible":
            base_url = b.get("base_url", "").rstrip("/")
            if not base_url: raise HTTPException(400, "请填写 Base URL")
            rq = urllib.request.Request(f"{base_url}/models",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"})
            with urllib.request.urlopen(rq, timeout=15) as resp:
                data = json.loads(resp.read())
                models = sorted([m["id"] for m in data.get("data",[])])
                result["valid"] = True
                result["models"] = models[:30]
                result["info"]["total_models"] = len(models)
        else:
            result["error"] = f"不支持的平台: {provider}"
    except urllib.error.HTTPError as e:
        result["error"] = f"HTTP {e.code}: {e.reason}"
        if e.code == 401: result["error"] = "API Key 无效或已过期"
        elif e.code == 403: result["error"] = "权限不足"
        elif e.code == 429: result["error"] = "请求频率超限"
    except Exception as e:
        result["error"] = str(e)
    return result

# ==================== CSV Import ====================

@app.post("/api/import-csv")
async def import_csv(req: Request, key: bytes = Depends(require_auth)):
    b = await req.json(); csv_text = b.get("csv_text",""); now = now_str(); count = 0
    reader = csv.DictReader(io.StringIO(csv_text))
    with get_db() as c:
        for row in reader:
            tags = row.get("tags","")
            c.execute("""INSERT INTO accounts(category,name,platform,username,password_enc,api_key_enc,url,
                monthly_cost,sell_price,expire_date,account_status,tags,customer_name,notes,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (row.get("category","其他"), row.get("name",""), row.get("platform",""),
                 row.get("username",""), encrypt(row.get("password",""), key),
                 encrypt(row.get("api_key",""), key), row.get("url",""),
                 float(row.get("monthly_cost",0) or 0), float(row.get("sell_price",0) or 0),
                 row.get("expire_date",""), row.get("account_status","inventory"),
                 tags, row.get("customer_name",""), row.get("notes",""), now, now))
            count += 1
        c.commit()
    log_activity(None, "import_csv", f"CSV导入 {count} 条"); return {"ok": True, "imported": count}

# ==================== Other ====================

@app.get("/api/generate-password")
def gen_pwd(length: int = 16, uppercase: bool = True, digits: bool = True, symbols: bool = True):
    length = max(8, min(length, 64)); chars = string.ascii_lowercase
    req = [secrets.choice(string.ascii_lowercase)]
    if uppercase: chars += string.ascii_uppercase; req.append(secrets.choice(string.ascii_uppercase))
    if digits: chars += string.digits; req.append(secrets.choice(string.digits))
    if symbols: chars += "!@#$%^&*_+-=?"; req.append(secrets.choice("!@#$%^&*_+-=?"))
    pool = req + [secrets.choice(chars) for _ in range(length - len(req))]
    secrets.SystemRandom().shuffle(pool); return {"password": "".join(pool)}

@app.get("/api/templates")
def list_templates(key: bytes = Depends(require_auth)):
    with get_db() as c: return [dict(r) for r in c.execute("SELECT * FROM templates ORDER BY category,name").fetchall()]

@app.get("/api/logs")
def get_logs(limit: int = 100, key: bytes = Depends(require_auth)):
    with get_db() as c: return [dict(r) for r in c.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]

@app.get("/api/export")
def export_data(key: bytes = Depends(require_auth)):
    with get_db() as c: rows = c.execute("SELECT * FROM accounts WHERE deleted=0 ORDER BY id").fetchall()
    data = [row_to_dict(r, key) for r in rows]
    content = json.dumps(data, ensure_ascii=False, indent=2)
    fn = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = BACKUP_DIR / fn
    backup_path.write_text(content, encoding="utf-8")
    log_activity(None, "export", f"导出 {len(data)} 条 → {fn}")
    return StreamingResponse(iter([content]), media_type="application/json",
                             headers={"Content-Disposition": f"attachment; filename={fn}"})

@app.post("/api/import")
async def import_data(req: Request, key: bytes = Depends(require_auth)):
    items = (await req.json()).get("accounts",[]); now = now_str(); count = 0
    with get_db() as c:
        for item in items:
            tags = ",".join(item.get("tags",[])) if isinstance(item.get("tags"), list) else item.get("tags","")
            c.execute("""INSERT INTO accounts(category,name,platform,username,password_enc,api_key_enc,url,
                monthly_cost,sell_price,total_income,expire_date,account_status,starred,tags,color_tag,
                customer_name,customer_contact,auto_renew,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (item.get("category",""), item.get("name",""), item.get("platform",""),
                 item.get("username",""), encrypt(item.get("password",""), key),
                 encrypt(item.get("api_key",""), key), item.get("url",""),
                 item.get("monthly_cost",0), item.get("sell_price",0), item.get("total_income",0),
                 item.get("expire_date",""), item.get("account_status","inventory"),
                 1 if item.get("starred") else 0, tags, item.get("color_tag",""),
                 item.get("customer_name",""), item.get("customer_contact",""),
                 1 if item.get("auto_renew") else 0, item.get("notes",""), now, now)); count += 1
        c.commit()
    log_activity(None, "import", f"导入 {count} 条"); return {"ok": True, "imported": count}

@app.get("/api/recent")
def recent_accounts(workspace: str = "", key: bytes = Depends(require_auth)):
    with get_db() as c:
        if workspace:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0 AND workspace=? AND last_accessed!='' ORDER BY last_accessed DESC LIMIT 10", (workspace,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM accounts WHERE deleted=0 AND last_accessed!='' ORDER BY last_accessed DESC LIMIT 10").fetchall()
    return [row_to_dict(r, key, include_password=False) for r in rows]

# ==================== Data Migration ====================

@app.post("/api/migrate")
async def migrate_data(req: Request, key: bytes = Depends(require_auth)):
    b = await req.json()
    db_b64 = b.get("db_data", "")
    salt_b64 = b.get("salt_data", "")
    old_password = b.get("old_password", "")
    target_workspace = b.get("target_workspace", "")
    skip_duplicates = b.get("skip_duplicates", True)

    if not db_b64 or not salt_b64 or not old_password:
        raise HTTPException(400, "请提供旧数据库文件、salt文件和旧主密码")

    try:
        db_bytes = base64.b64decode(db_b64)
        salt_bytes = base64.b64decode(salt_b64)
    except Exception:
        raise HTTPException(400, "文件解码失败，请确认文件正确")

    if len(salt_bytes) != 16:
        raise HTTPException(400, "无效的 .salt 文件（应为16字节）")

    old_kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt_bytes, iterations=480_000)
    old_key = base64.urlsafe_b64encode(old_kdf.derive(old_password.encode()))

    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.db')
    try:
        with os.fdopen(tmp_fd, 'wb') as f:
            f.write(db_bytes)

        old_conn = sqlite3.connect(tmp_path)
        old_conn.row_factory = sqlite3.Row

        try:
            master_row = old_conn.execute("SELECT hash FROM master WHERE id=1").fetchone()
        except Exception:
            old_conn.close()
            raise HTTPException(400, "无效的数据库文件，无法读取主密码表")

        if not master_row:
            old_conn.close()
            raise HTTPException(400, "旧数据库未初始化（未设置主密码）")

        expected_hash = hashlib.pbkdf2_hmac("sha256", old_password.encode(), salt_bytes, 480_000).hex()
        if expected_hash != master_row["hash"]:
            old_conn.close()
            raise HTTPException(403, "旧版本主密码错误")

        old_cols = {r[1] for r in old_conn.execute("PRAGMA table_info(accounts)").fetchall()}
        try:
            if "deleted" in old_cols:
                old_accounts = [dict(r) for r in old_conn.execute("SELECT * FROM accounts WHERE deleted=0").fetchall()]
            else:
                old_accounts = [dict(r) for r in old_conn.execute("SELECT * FROM accounts").fetchall()]
        except Exception:
            old_conn.close()
            raise HTTPException(400, "无法读取旧数据库账号数据")

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
        migrated = 0
        skipped = 0
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
                        try:
                            pwd = Fernet(old_key).decrypt(r["password_enc"].encode()).decode()
                        except Exception:
                            pwd = ""

                    api_k = ""
                    if r.get("api_key_enc"):
                        try:
                            api_k = Fernet(old_key).decrypt(r["api_key_enc"].encode()).decode()
                        except Exception:
                            api_k = ""

                    new_pwd_enc = encrypt(pwd, key)
                    new_api_enc = encrypt(api_k, key)

                    ws = target_workspace or r.get("workspace", "") or ""

                    cur = c.execute("""INSERT INTO accounts(category,name,platform,username,password_enc,api_key_enc,url,
                        monthly_cost,sell_price,total_income,expire_date,status,account_status,starred,tags,color_tag,
                        customer_name,customer_contact,auto_renew,notes,workspace,created_at,updated_at)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (r.get("category", ""), name, platform, username, new_pwd_enc, new_api_enc,
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
                    errors.append(f"{name}: {str(e)}")
            c.commit()

        ph_count = 0
        try:
            old_ph = [dict(r) for r in old_conn.execute("SELECT * FROM password_history").fetchall()]
            with get_db() as c:
                for ph in old_ph:
                    new_acc_id = id_map.get(ph.get("account_id"))
                    if new_acc_id is None:
                        continue
                    old_ph_pwd = ""
                    if ph.get("password_enc"):
                        try:
                            old_ph_pwd = Fernet(old_key).decrypt(ph["password_enc"].encode()).decode()
                        except Exception:
                            continue
                    new_ph_enc = encrypt(old_ph_pwd, key)
                    c.execute("INSERT INTO password_history(account_id,password_enc,changed_at) VALUES(?,?,?)",
                              (new_acc_id, new_ph_enc, ph.get("changed_at", now)))
                    ph_count += 1
                c.commit()
        except Exception:
            pass

        old_conn.close()
        log_activity(None, "migrate", f"数据迁移: 导入 {migrated} 条, 跳过 {skipped} 条")

        return {
            "ok": True, "migrated": migrated, "skipped": skipped,
            "workspaces_migrated": ws_migrated, "password_history": ph_count,
            "errors": errors[:10]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"迁移失败: {str(e)}")
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

if __name__ == "__main__":
    import uvicorn; uvicorn.run(app, host="127.0.0.1", port=8899)
