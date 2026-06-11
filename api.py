# =============================================================================
# api.py — FastAPI Backend
# Adani Thermal Power Plant | C&I Main Store
# Serves: React Dashboard at port 5173
# =============================================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import os, datetime, json, uuid

app = FastAPI(title="Adani Store API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SCRIPT_DIR      = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE  = os.path.join(SCRIPT_DIR, "plant_inventory.xlsx")
LOG_FILE        = os.path.join(SCRIPT_DIR, "issue_log.csv")
RES_FILE        = os.path.join(SCRIPT_DIR, "reservations.json")

# ── helpers ──────────────────────────────────────────────────────────────────

def read_inventory():
    df = pd.read_excel(INVENTORY_FILE, sheet_name="Inventory")
    df.columns = df.columns.str.strip()
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0).astype(int)
    df["MinStock"] = pd.to_numeric(df["MinStock"], errors="coerce").fillna(0).astype(int)
    return df

def write_inventory(df: pd.DataFrame):
    with pd.ExcelWriter(INVENTORY_FILE, engine="openpyxl", mode="a",
                        if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name="Inventory", index=False)

def read_log():
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()
    df = pd.read_csv(LOG_FILE)
    df.columns = df.columns.str.strip()
    if "Department" not in df.columns:
        df["Department"] = "Not Specified"
    return df

def append_log(entry: dict):
    row = pd.DataFrame([entry])
    if os.path.exists(LOG_FILE):
        row.to_csv(LOG_FILE, mode="a", header=False, index=False)
    else:
        row.to_csv(LOG_FILE, index=False)

def read_reservations():
    if not os.path.exists(RES_FILE):
        return []
    with open(RES_FILE) as f:
        return json.load(f)

def write_reservations(data):
    with open(RES_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def status_label(qty, min_stock):
    if qty == 0:         return "out_of_stock"
    if qty < min_stock:  return "low_stock"
    if qty < min_stock * 1.5: return "warning"
    return "in_stock"

# ── models ───────────────────────────────────────────────────────────────────

class IssueRequest(BaseModel):
    engineer_name: str
    emp_id: Optional[str] = ""
    department: Optional[str] = "C&I"
    quantity: int = 1
    purpose: Optional[str] = ""

class ReservationCreate(BaseModel):
    engineer_name: str
    emp_id: Optional[str] = ""
    department: Optional[str] = "C&I"
    item_code: str
    item_name: str
    quantity: int
    purpose: Optional[str] = ""

# ── ROUTES ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "Adani Store API", "version": "2.0"}

# ── Dashboard Stats ───────────────────────────────────────────────────────────

@app.get("/dashboard/stats")
def dashboard_stats():
    df  = read_inventory()
    log = read_log()
    res = read_reservations()

    low   = df[df["Quantity"] < df["MinStock"]]
    out   = df[df["Quantity"] == 0]
    pend  = [r for r in res if r["status"] == "pending"]

    return {
        "total_instruments":  int(len(df)),
        "total_units":        int(df["Quantity"].sum()),
        "low_stock_count":    int(len(low)),
        "out_of_stock_count": int(len(out)),
        "active_reservations":int(len([r for r in res if r["status"] == "approved"])),
        "pending_approvals":  int(len(pend)),
        "total_issued_today": int(
            len(log[log["Date"] == datetime.date.today().strftime("%d-%m-%Y")])
            if not log.empty and "Date" in log.columns else 0
        ),
        "categories": int(df["Category"].nunique()) if "Category" in df.columns else 0,
    }

# ── Inventory ─────────────────────────────────────────────────────────────────

@app.get("/inventory")
def get_inventory():
    df = read_inventory()
    records = []
    for _, row in df.iterrows():
        qty = int(row["Quantity"])
        mn  = int(row["MinStock"])
        records.append({
            "item_code":  str(row.get("ItemCode", "")),
            "item_name":  str(row.get("ItemName", "")),
            "category":   str(row.get("Category", "")),
            "quantity":   qty,
            "min_stock":  mn,
            "location":   str(row.get("Location", "")),
            "status":     status_label(qty, mn),
        })
    return records

@app.get("/inventory/{item_code}")
def get_item(item_code: str):
    df   = read_inventory()
    rows = df[df["ItemCode"].str.upper() == item_code.upper()]
    if rows.empty:
        raise HTTPException(404, f"Item {item_code} not found")
    row = rows.iloc[0]
    qty = int(row["Quantity"]); mn = int(row["MinStock"])
    return {
        "item_code": str(row["ItemCode"]),
        "item_name": str(row["ItemName"]),
        "category":  str(row.get("Category","")),
        "quantity":  qty,
        "min_stock": mn,
        "location":  str(row.get("Location","")),
        "status":    status_label(qty, mn),
    }

@app.patch("/inventory/{item_code}/issue")
def issue_item(item_code: str, req: IssueRequest):
    df   = read_inventory()
    mask = df["ItemCode"].str.upper() == item_code.upper()
    if not mask.any():
        raise HTTPException(404, f"Item {item_code} not found")

    idx = df[mask].index[0]
    cur = int(df.loc[idx, "Quantity"])
    if req.quantity > cur:
        raise HTTPException(400, f"Only {cur} units available")

    new_qty = cur - req.quantity
    df.loc[idx, "Quantity"] = new_qty
    write_inventory(df)

    row = df.loc[idx]
    append_log({
        "Date":          datetime.date.today().strftime("%d-%m-%Y"),
        "Time":          datetime.datetime.now().strftime("%H:%M:%S"),
        "EngineerName":  req.engineer_name,
        "Department":    req.department or "C&I",
        "ItemCode":      item_code.upper(),
        "ItemName":      str(row["ItemName"]),
        "QuantityTaken": req.quantity,
        "QuantityLeft":  new_qty,
    })

    return {
        "success":       True,
        "item_code":     item_code.upper(),
        "item_name":     str(row["ItemName"]),
        "qty_taken":     req.quantity,
        "qty_remaining": new_qty,
        "status":        status_label(new_qty, int(row["MinStock"])),
    }

# ── Transaction Log ───────────────────────────────────────────────────────────

@app.get("/log")
def get_log(limit: int = 200):
    log = read_log()
    if log.empty:
        return []
    cols = ["Date","Time","EngineerName","Department","ItemCode","ItemName","QuantityTaken","QuantityLeft"]
    for c in cols:
        if c not in log.columns:
            log[c] = ""
    return log[cols].tail(limit).iloc[::-1].to_dict(orient="records")

# ── Low Stock Alerts ──────────────────────────────────────────────────────────

@app.get("/alerts/lowstock")
def low_stock():
    df  = read_inventory()
    low = df[df["Quantity"] < df["MinStock"]].copy()
    result = []
    for _, row in low.iterrows():
        qty = int(row["Quantity"]); mn = int(row["MinStock"])
        result.append({
            "item_code":    str(row["ItemCode"]),
            "item_name":    str(row["ItemName"]),
            "category":     str(row.get("Category","")),
            "quantity":     qty,
            "min_stock":    mn,
            "location":     str(row.get("Location","")),
            "status":       status_label(qty, mn),
            "deficit":      mn - qty,
            "urgency":      "critical" if qty == 0 else ("high" if qty < mn // 2 else "medium"),
        })
    result.sort(key=lambda x: x["quantity"])
    return result

# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/analytics/top10")
def top10():
    log = read_log()
    if log.empty or "ItemCode" not in log.columns:
        return []
    g = (log.groupby(["ItemCode","ItemName"])
           .agg(times_issued=("ItemCode","count"),
                total_qty=("QuantityTaken","sum"))
           .reset_index()
           .sort_values("times_issued", ascending=False)
           .head(10))
    return g.to_dict(orient="records")

@app.get("/analytics/monthly")
def monthly():
    log = read_log()
    if log.empty or "Date" not in log.columns:
        return []
    log["Date"] = pd.to_datetime(log["Date"], dayfirst=True, errors="coerce")
    log["Month"] = log["Date"].dt.strftime("%b %Y")
    log["MonthKey"] = log["Date"].dt.to_period("M")
    g = (log.groupby(["MonthKey","Month"])
           .agg(total_issues=("ItemCode","count"),
                total_qty=("QuantityTaken","sum"))
           .reset_index()
           .sort_values("MonthKey"))
    return g[["Month","total_issues","total_qty"]].to_dict(orient="records")

@app.get("/analytics/department")
def department():
    log = read_log()
    if log.empty or "Department" not in log.columns:
        return []
    g = (log.groupby("Department")
           .agg(total_issues=("ItemCode","count"),
                total_qty=("QuantityTaken","sum"))
           .reset_index()
           .sort_values("total_issues", ascending=False))
    return g.to_dict(orient="records")

@app.get("/analytics/categories")
def categories():
    log = read_log()
    df  = read_inventory()
    if log.empty:
        return []
    cat_map = df.set_index("ItemCode")["Category"].to_dict() if "Category" in df.columns else {}
    log = log.copy()
    log["Category"] = log["ItemCode"].map(cat_map).fillna("Other")
    g = (log.groupby("Category")["QuantityTaken"]
           .sum().reset_index()
           .sort_values("QuantityTaken", ascending=False))
    return g.to_dict(orient="records")

# ── Reservations ─────────────────────────────────────────────────────────────

@app.get("/reservations")
def get_reservations():
    return read_reservations()

@app.post("/reservations")
def create_reservation(req: ReservationCreate):
    res = read_reservations()
    new = {
        "id":            str(uuid.uuid4())[:8].upper(),
        "engineer_name": req.engineer_name,
        "emp_id":        req.emp_id or "",
        "department":    req.department or "C&I",
        "item_code":     req.item_code,
        "item_name":     req.item_name,
        "quantity":      req.quantity,
        "purpose":       req.purpose or "",
        "status":        "pending",
        "created_at":    datetime.datetime.now().isoformat(),
        "updated_at":    datetime.datetime.now().isoformat(),
    }
    res.append(new)
    write_reservations(res)
    return new

@app.patch("/reservations/{res_id}/approve")
def approve_reservation(res_id: str):
    res = read_reservations()
    for r in res:
        if r["id"] == res_id:
            r["status"] = "approved"
            r["updated_at"] = datetime.datetime.now().isoformat()
            write_reservations(res)
            return r
    raise HTTPException(404, "Reservation not found")

@app.patch("/reservations/{res_id}/reject")
def reject_reservation(res_id: str):
    res = read_reservations()
    for r in res:
        if r["id"] == res_id:
            r["status"] = "rejected"
            r["updated_at"] = datetime.datetime.now().isoformat()
            write_reservations(res)
            return r
    raise HTTPException(404, "Reservation not found")

@app.patch("/reservations/{res_id}/issue")
def issue_reservation(res_id: str):
    res = read_reservations()
    for r in res:
        if r["id"] == res_id and r["status"] == "approved":
            # Actually issue from inventory
            df   = read_inventory()
            mask = df["ItemCode"].str.upper() == r["item_code"].upper()
            if mask.any():
                idx = df[mask].index[0]
                cur = int(df.loc[idx,"Quantity"])
                qty = int(r["quantity"])
                if qty <= cur:
                    df.loc[idx,"Quantity"] = cur - qty
                    write_inventory(df)
                    append_log({
                        "Date":         datetime.date.today().strftime("%d-%m-%Y"),
                        "Time":         datetime.datetime.now().strftime("%H:%M:%S"),
                        "EngineerName": r["engineer_name"],
                        "Department":   r["department"],
                        "ItemCode":     r["item_code"],
                        "ItemName":     r["item_name"],
                        "QuantityTaken": qty,
                        "QuantityLeft":  cur - qty,
                    })
            r["status"] = "issued"
            r["updated_at"] = datetime.datetime.now().isoformat()
            write_reservations(res)
            return r
    raise HTTPException(404, "Reservation not found or not approved")

# ── AI Query ──────────────────────────────────────────────────────────────────

class AIQuery(BaseModel):
    question: str

@app.post("/ai/query")
def ai_query(req: AIQuery):
    q   = req.question.lower().strip()
    df  = read_inventory()
    log = read_log()
    now = datetime.datetime.now().strftime("%d %b %Y, %H:%M")

    # Stock check for specific item code
    import re
    codes = re.findall(r'\b[a-z]{2}\d{3}\b', q)
    if codes:
        code = codes[0].upper()
        rows = df[df["ItemCode"].str.upper() == code]
        if not rows.empty:
            r = rows.iloc[0]
            qty = int(r["Quantity"]); mn = int(r["MinStock"])
            st  = "✅ In Stock" if qty >= mn else ("⚠️ Low Stock" if qty > 0 else "🔴 Out of Stock")
            return {"answer": f"**{code} — {r['ItemName']}**\n\nQuantity: **{qty}** units\nMin Stock: {mn} units\nLocation: {r.get('Location','—')}\nStatus: {st}"}

    # Low stock query
    if any(w in q for w in ["low stock","low-stock","below minimum","running low","shortage"]):
        low = df[df["Quantity"] < df["MinStock"]]
        if low.empty:
            return {"answer": "✅ No items are currently below minimum stock levels. Inventory looks healthy!"}
        items = "\n".join([f"• **{r['ItemCode']}** — {r['ItemName']} ({int(r['Quantity'])} remaining, min: {int(r['MinStock'])})" for _, r in low.head(8).iterrows()])
        return {"answer": f"⚠️ **{len(low)} items are below minimum stock:**\n\n{items}"}

    # Out of stock
    if any(w in q for w in ["out of stock","zero stock","not available","unavailable"]):
        out = df[df["Quantity"] == 0]
        if out.empty:
            return {"answer": "✅ No items are currently out of stock!"}
        items = "\n".join([f"• **{r['ItemCode']}** — {r['ItemName']}" for _, r in out.iterrows()])
        return {"answer": f"🔴 **{len(out)} items are out of stock:**\n\n{items}"}

    # Total inventory
    if any(w in q for w in ["total","how many","count","inventory size","all items"]):
        return {"answer": f"📦 **Inventory Summary as of {now}:**\n\n• Total instrument types: **{len(df)}**\n• Total units in store: **{int(df['Quantity'].sum())}**\n• Low stock items: **{len(df[df['Quantity'] < df['MinStock']])}**\n• Out of stock: **{len(df[df['Quantity']==0])}**\n• Categories: **{df['Category'].nunique() if 'Category' in df.columns else '—'}**"}

    # Who reserved / issued an item
    if any(w in q for w in ["who","reserved","issued","taken","borrowed"]) and not log.empty:
        item_words = [w for w in q.split() if len(w) > 3 and w not in ["who","what","when","have","been","that","this","item","last","were","reserved","issued","taken"]]
        if item_words:
            pattern = "|".join(item_words)
            matches = log[log["ItemName"].str.lower().str.contains(pattern, na=False) |
                         log["ItemCode"].str.lower().str.contains(pattern, na=False)]
            if not matches.empty:
                recent = matches.tail(5)
                items = "\n".join([f"• **{r['EngineerName']}** took {int(r['QuantityTaken'])} × {r['ItemName']} on {r['Date']}" for _, r in recent.iterrows()])
                return {"answer": f"📋 **Recent issues matching your query:**\n\n{items}"}

    # Department usage
    if any(w in q for w in ["department","dept","which dept","team"]) and not log.empty:
        if "Department" in log.columns:
            g = log.groupby("Department").size().sort_values(ascending=False)
            items = "\n".join([f"• **{dept}**: {cnt} transactions" for dept, cnt in g.items()])
            return {"answer": f"🏢 **Department-wise instrument usage:**\n\n{items}"}

    # Top items
    if any(w in q for w in ["top","most used","frequently","popular","common"]) and not log.empty:
        g = log.groupby("ItemName")["QuantityTaken"].sum().sort_values(ascending=False).head(5)
        items = "\n".join([f"{i+1}. **{name}** — {int(qty)} units issued" for i, (name,qty) in enumerate(g.items())])
        return {"answer": f"📊 **Top 5 Most Used Instruments:**\n\n{items}"}

    # Greeting
    if any(w in q for w in ["hello","hi","hey","help","what can you"]):
        return {"answer": f"👋 **Hello! I'm the Adani Store AI Assistant.**\n\nI can help you with:\n• Check stock: *\"Do we have PT001?\"*\n• Low stock: *\"Show low stock items\"*\n• Usage: *\"Who last took RTD sensors?\"*\n• Summary: *\"Total inventory?\"*\n• Alerts: *\"What is out of stock?\"*\n\nWhat would you like to know?"}

    # Default
    return {"answer": f"🤔 I couldn't find a specific answer for that. Try asking:\n\n• *\"Do we have PT001?\"*\n• *\"Show low stock items\"*\n• *\"Total inventory count\"*\n• *\"Who issued pressure transmitters?\"*\n• *\"What's out of stock?\"*"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
