import os, sqlite3, uuid
from contextlib import closing
from pathlib import Path
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Home Cash Backend")
DB = Path(os.environ.get("HOME_CASH_DB", str(Path(__file__).with_name("cash.sqlite3"))))
DENOMS = [10000,5000,2000,1000,500,100,25,10,5,1]

def connect():
    c = sqlite3.connect(DB, timeout=15)
    c.row_factory = sqlite3.Row
    return c

with closing(connect()) as c, c:
    c.execute("CREATE TABLE IF NOT EXISTS inventory (denom INTEGER PRIMARY KEY, quantity INTEGER NOT NULL CHECK(quantity>=0))")
    c.executemany("INSERT OR IGNORE INTO inventory VALUES (?,0)", [(d,) for d in DENOMS])
    c.execute("CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending')")

async def ynab(path):
    token = os.environ.get("YNAB_TOKEN")
    if not token:
        raise HTTPException(503, "YNAB token not configured")
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            r = await client.get("https://api.ynab.com/v1/" + path, headers={"Authorization": "Bearer " + token})
        except httpx.RequestError:
            raise HTTPException(503, "YNAB unavailable")
    if r.status_code != 200:
        raise HTTPException(502, "YNAB returned status " + str(r.status_code))
    return r.json()["data"]

@app.get("/api/health")
def health():
    return {"status":"ok","drawer":"simulation","ynab_configured":bool(os.environ.get("YNAB_TOKEN"))}

@app.get("/api/ynab/budgets")
async def budgets():
    data = await ynab("budgets")
    return [{"id":b["id"],"name":b["name"]} for b in data["budgets"]]

@app.get("/api/ynab/accounts")
async def accounts():
    budget = os.environ.get("YNAB_BUDGET_ID")
    if not budget:
        raise HTTPException(503,"Budget not configured")
    data = await ynab("budgets/"+budget+"/accounts")
    return [{"id":a["id"],"name":a["name"],"type":a["type"],"balance_milliunits":a["balance"]} for a in data["accounts"] if not a["closed"] and not a["deleted"]]

@app.get("/api/ynab/categories")
async def categories():
    budget = os.environ.get("YNAB_BUDGET_ID")
    if not budget:
        raise HTTPException(503,"Budget not configured")
    data = await ynab("budgets/"+budget+"/categories")
    return [{"name":g["name"],"categories":[{"id":a["id"],"name":a["name"]} for a in g["categories"] if not a["hidden"] and not a["deleted"]]} for g in data["category_groups"] if not g["hidden"] and not g["deleted"]]

@app.get("/api/inventory")
def inventory():
    with closing(connect()) as c:
        rows = c.execute("SELECT * FROM inventory ORDER BY denom DESC").fetchall()
    return {"balance_cents":sum(r["denom"]*r["quantity"] for r in rows),"counts":[dict(r) for r in rows]}

@app.get("/api/reconciliation")
async def reconciliation():
    budget = os.environ.get("YNAB_BUDGET_ID")
    account = os.environ.get("YNAB_CASH_ACCOUNT_ID")
    if not budget or not account:
        raise HTTPException(503,"Budget and cash account not configured")
    data = await ynab("budgets/"+budget+"/accounts/"+account)
    balance = inventory()["balance_cents"]
    ynab_balance = data["account"]["balance"]
    return {"drawer_cents":balance,"ynab_milliunits":ynab_balance,"difference_milliunits":balance*10-ynab_balance}
