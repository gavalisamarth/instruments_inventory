# -*- coding: utf-8 -*-
# =============================================================================
# AI-POWERED INSTRUMENT INVENTORY ASSISTANT
# File: inventory_chatbot_copy.py
#
# Author  : Samarth Gavali - Control & Instrumentation Internship
# Project : Main Store ChatBot - Adani Thermal Power Plant
#
# What this program does:
#   1. Loads inventory from plant_inventory.xlsx (updated by seniors from SAP)
#   2. Search instruments by name, code, or category
#   3. Display full inventory table
#   4. Show inventory summary and category breakdown
#   5. Issue instruments: deducts quantity, saves back to Excel, logs transaction
#   6. Sends email alert to officials when stock drops below minimum
#   7. Sends daily email report every morning automatically
#
# NOTIFICATION SYSTEM: Outlook / Email only
#   - Low stock alert  -> fired immediately after each issue
#   - Daily report     -> sent every morning at configured time
#   - Recipients       -> managed via recipients.xlsx (no code changes needed)
#
# DATA SOURCE: plant_inventory.xlsx
#   - Seniors export from SAP and update the Inventory sheet
#   - No code changes needed when data changes
# =============================================================================


# =============================================================================
# IMPORTS
# =============================================================================

import pandas as pd    # Reading/writing Excel and data analysis
import os              # File path handling
import datetime        # Timestamps for logs

# Email alerts module (optional - program runs fine without it)
try:
    import email_alerts
    print("[OK] Email alert module loaded.")
except ImportError:
    email_alerts = None
    print("[WARNING] email_alerts.py not found. Email alerts disabled.")


# =============================================================================
# FILE PATHS  (change here only if files are moved)
# =============================================================================

# Folder where this script lives
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Inventory Excel file — seniors update this from SAP
INVENTORY_FILE  = os.path.join(SCRIPT_DIR, "plant_inventory.xlsx")
INVENTORY_SHEET = "Inventory"

# Transaction log — auto-created, do not edit manually
LOG_FILE_PATH = os.path.join(SCRIPT_DIR, "issue_log.csv")


# =============================================================================
# FUNCTION: load_inventory
# Reads the Inventory sheet from plant_inventory.xlsx
# =============================================================================

def load_inventory():
    """
    Loads inventory data from plant_inventory.xlsx.
    Returns a DataFrame, or None if the file is missing or broken.
    """

    if not os.path.exists(INVENTORY_FILE):
        print("\n[ERROR] plant_inventory.xlsx not found!")
        print(f"   Expected location: {INVENTORY_FILE}")
        print("   Ask seniors to place the updated Excel file in this folder.")
        return None

    try:
        df = pd.read_excel(INVENTORY_FILE, sheet_name=INVENTORY_SHEET)

        # Clean column names (remove accidental spaces)
        df.columns = df.columns.str.strip()

        # Clean string values in all columns
        df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

        # Drop completely empty rows (seniors may leave blank rows)
        df = df.dropna(subset=["ItemCode", "ItemName"])
        df = df.reset_index(drop=True)

        print(f"\n[OK] Inventory loaded: {len(df)} items from plant_inventory.xlsx\n")
        return df

    except Exception as error:
        print(f"\n[ERROR] Could not load inventory: {error}")
        return None


# =============================================================================
# FUNCTION: save_inventory
# Writes the updated DataFrame back to plant_inventory.xlsx
# Preserves all other sheets (Instructions, Column Guide)
# =============================================================================

def save_inventory(df):
    """
    Saves the updated inventory DataFrame back to plant_inventory.xlsx.
    Only the Inventory sheet is replaced. Other sheets are untouched.

    Returns True if saved successfully, False if failed.
    """
    try:
        with pd.ExcelWriter(
            INVENTORY_FILE,
            engine          = "openpyxl",
            mode            = "a",           # Append mode — don't destroy other sheets
            if_sheet_exists = "replace"      # Only replace the Inventory sheet
        ) as writer:
            df.to_excel(writer, sheet_name=INVENTORY_SHEET, index=False)

        return True

    except Exception as error:
        print(f"\n[ERROR] Could not save to plant_inventory.xlsx: {error}")
        print("   Make sure the file is not currently open in Excel.")
        return False


# =============================================================================
# FUNCTION: log_issue
# Records every transaction to issue_log.csv (audit trail)
# =============================================================================


# Path to the Excel log file
LOG_EXCEL_PATH = os.path.join(SCRIPT_DIR, "issue_log.xlsx")
LOG_SHEET      = "Transaction Log"


def log_issue(engineer_name, item_code, item_name, qty_taken, qty_remaining, department=""):
    """
    Records every instrument issue to BOTH:
      1. issue_log.csv  - simple backup, always available
      2. issue_log.xlsx - rich Excel with 3 analysis sheets

    Columns: Date, Time, EngineerName, Department, ItemCode, ItemName,
             QuantityTaken, QuantityLeft
    """

    now = datetime.datetime.now()

    log_entry = {
        "Date"          : now.strftime("%d-%m-%Y"),
        "Time"          : now.strftime("%H:%M:%S"),
        "EngineerName"  : engineer_name,
        "Department"    : department.strip() if department else "Not Specified",
        "ItemCode"      : item_code,
        "ItemName"      : item_name,
        "QuantityTaken" : qty_taken,
        "QuantityLeft"  : qty_remaining
    }

    new_row = pd.DataFrame([log_entry])

    # ----------------------------------------------------------------
    # Write to CSV (simple, fast, always works)
    # ----------------------------------------------------------------
    file_exists = os.path.exists(LOG_FILE_PATH)
    new_row.to_csv(
        LOG_FILE_PATH,
        mode   = "a",
        index  = False,
        header = not file_exists
    )

    # ----------------------------------------------------------------
    # Write to Excel log (rich, with summary sheets)
    # Reads existing log, appends new row, rebuilds all 3 sheets
    # ----------------------------------------------------------------
    try:
        # Load existing log or start fresh
        if os.path.exists(LOG_EXCEL_PATH):
            existing = pd.read_excel(LOG_EXCEL_PATH, sheet_name=LOG_SHEET)
            full_log = pd.concat([existing, new_row], ignore_index=True)
        else:
            full_log = new_row

        # Build summary by engineer
        eng_summary = full_log.groupby("EngineerName").agg(
            Total_Issues    = ("QuantityTaken", "count"),
            Total_Qty_Taken = ("QuantityTaken", "sum")
        ).reset_index().sort_values("Total_Qty_Taken", ascending=False)

        # Build summary by item
        item_summary = full_log.groupby(["ItemCode", "ItemName"]).agg(
            Times_Issued = ("QuantityTaken", "count"),
            Total_Taken  = ("QuantityTaken", "sum")
        ).reset_index().sort_values("Total_Taken", ascending=False)

        # Write all 3 sheets to Excel
        with pd.ExcelWriter(LOG_EXCEL_PATH, engine="openpyxl") as writer:
            full_log.to_excel(    writer, sheet_name="Transaction Log", index=False)
            eng_summary.to_excel( writer, sheet_name="By Engineer",     index=False)
            item_summary.to_excel(writer, sheet_name="By Item",         index=False)

    except Exception as e:
        # Excel log failure should never crash the main program
        print(f"  [WARNING] Could not update issue_log.xlsx: {e}")
        print("  CSV log was still saved successfully.")



# =============================================================================
# FUNCTION: show_inventory
# Prints the full inventory table
# =============================================================================

def show_inventory(df):
    """Displays the complete inventory in a formatted table."""

    print("\n" + "=" * 75)
    print("           MAIN STORE - COMPLETE INSTRUMENT INVENTORY")
    print("           Adani Thermal Power Plant")
    print("=" * 75)

    pd.set_option("display.max_rows",    None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width",       None)
    pd.set_option("display.max_colwidth",None)

    print(df.to_string(index=False))

    print("=" * 75)
    print(f"  Total Items: {len(df)}")
    print("=" * 75 + "\n")


# =============================================================================
# FUNCTION: search_instrument
# Searches inventory by keyword across code, name, and category
# =============================================================================

def search_instrument(df):
    """
    Searches the inventory for instruments matching a keyword.
    Searches across ItemCode, ItemName, and Category simultaneously.
    Case-insensitive — 'RTD' finds 'rtd', 'Rtd', 'RTD'.
    """

    print("\n" + "-" * 50)
    print("  INSTRUMENT SEARCH")
    print("-" * 50)

    keyword = input("  Enter search keyword (name / code / category): ").strip()

    if not keyword:
        print("  [!] No keyword entered.")
        return

    results = df[
        df["ItemName"].str.contains(keyword, case=False, na=False) |
        df["ItemCode"].str.contains(keyword, case=False, na=False) |
        df["Category"].str.contains(keyword, case=False, na=False)
    ]

    if results.empty:
        print(f"\n  [NOT FOUND] No instruments matching: '{keyword}'")
        print("  Tip: Try a shorter keyword. Example: 'RTD' instead of 'RTD Sensor'")
        return

    print(f"\n  [FOUND] {len(results)} item(s) matching '{keyword}':\n")
    print("  " + "-" * 71)
    print(f"  {'CODE':<8} {'ITEM NAME':<42} {'QTY':>4}  {'MIN':>4}  {'LOCATION'}")
    print("  " + "-" * 71)

    for _, row in results.iterrows():
        qty       = int(row["Quantity"])
        min_stock = int(row["MinStock"])

        # Flag low stock items visually
        flag = " [LOW]" if qty < min_stock else ""
        if qty == 0:
            flag = " [OUT]"

        print(
            f"  {row['ItemCode']:<8} "
            f"{row['ItemName']:<42} "
            f"{qty:>4}  "
            f"{min_stock:>4}  "
            f"{row['Location']}{flag}"
        )

    print("  " + "-" * 71 + "\n")


# =============================================================================
# FUNCTION: inventory_summary
# Shows statistics and category breakdown
# =============================================================================

def inventory_summary(df):
    """
    Displays a high-level summary report:
    - Total items, total stock, categories
    - Highest and lowest stocked items
    - Stock breakdown by category
    """

    print("\n" + "=" * 55)
    print("       INVENTORY SUMMARY REPORT")
    print("       Adani Thermal Power Plant - Main Store")
    print("=" * 55)

    total_items      = len(df)
    total_qty        = df["Quantity"].sum()
    total_categories = df["Category"].nunique()
    low_stock_count  = len(df[df["Quantity"] < df["MinStock"]])
    out_of_stock     = len(df[df["Quantity"] == 0])

    print(f"  Total Unique Instruments : {total_items}")
    print(f"  Total Stock (all items)  : {int(total_qty)} units")
    print(f"  Categories               : {total_categories}")
    print(f"  Items Below Min Stock    : {low_stock_count}")
    print(f"  Items Out of Stock       : {out_of_stock}")

    max_row = df.loc[df["Quantity"].idxmax()]
    min_row = df.loc[df["Quantity"].idxmin()]

    print(f"\n  Highest Stock:")
    print(f"    {max_row['ItemCode']} - {max_row['ItemName']}")
    print(f"    Quantity: {int(max_row['Quantity'])} units @ {max_row['Location']}")

    print(f"\n  Lowest Stock:")
    print(f"    {min_row['ItemCode']} - {min_row['ItemName']}")
    print(f"    Quantity: {int(min_row['Quantity'])} units @ {min_row['Location']}")

    print(f"\n  Stock Breakdown by Category:")
    print("  " + "-" * 48)
    print(f"  {'Category':<28} {'Items':>5}  {'Total':>6}  {'Avg':>6}")
    print("  " + "-" * 48)

    category_summary = df.groupby("Category").agg(
        Item_Count  = ("ItemCode",  "count"),
        Total_Stock = ("Quantity",  "sum"),
        Avg_Stock   = ("Quantity",  "mean")
    ).reset_index().sort_values("Total_Stock", ascending=False)

    for _, row in category_summary.iterrows():
        print(
            f"  {row['Category']:<28} "
            f"{row['Item_Count']:>5}  "
            f"{int(row['Total_Stock']):>6}  "
            f"{row['Avg_Stock']:>6.1f}"
        )

    print("=" * 55 + "\n")


# =============================================================================
# FUNCTION: issue_instrument
# Full workflow: search → validate → confirm → deduct → save → log → alert
# =============================================================================

def issue_instrument(df):
    """
    Handles issuing an instrument to an engineer:
    1. Gets engineer name
    2. Searches for item
    3. Checks stock availability
    4. Warns if stock is already low
    5. Confirms with engineer
    6. Deducts quantity and saves to Excel
    7. Logs the transaction
    8. Sends email alert if stock falls below minimum

    Returns the updated DataFrame.
    """

    print("\n" + "-" * 55)
    print("  ISSUE INSTRUMENT FROM STORE")
    print("-" * 55)

    # --- Step 1: Engineer name ---
    engineer_name = input("  Engineer Name: ").strip()
    if not engineer_name:
        print("  [!] Engineer name cannot be empty.")
        return df

    # --- Step 2: Search for item ---
    keyword = input("  Item name or code: ").strip()
    if not keyword:
        print("  [!] No keyword entered.")
        return df

    results = df[
        df["ItemName"].str.contains(keyword, case=False, na=False) |
        df["ItemCode"].str.contains(keyword, case=False, na=False) |
        df["Category"].str.contains(keyword, case=False, na=False)
    ]

    if results.empty:
        print(f"\n  [NOT FOUND] No instrument matching: '{keyword}'")
        return df

    # --- Step 3: If multiple matches, let engineer pick ---
    if len(results) > 1:
        print(f"\n  {len(results)} items match '{keyword}'. Select one:")
        print("  " + "-" * 55)

        results_list = results.reset_index()
        for i, row in results_list.iterrows():
            print(
                f"  {i + 1}.  [{row['ItemCode']}] {row['ItemName']}"
                f"  | Qty: {int(row['Quantity'])}  | {row['Location']}"
            )

        print("  " + "-" * 55)

        try:
            pick = int(input(f"  Enter number (1-{len(results)}): ").strip()) - 1
            if pick < 0 or pick >= len(results):
                print("  [!] Invalid selection.")
                return df
            selected_row = results_list.iloc[pick]
        except ValueError:
            print("  [!] Please enter a number.")
            return df
    else:
        selected_row = results.iloc[0]

    # Extract item details
    item_code   = selected_row["ItemCode"]
    item_name   = selected_row["ItemName"]
    current_qty = int(selected_row["Quantity"])
    min_stock   = int(selected_row["MinStock"])
    location    = selected_row["Location"]

    print(f"\n  Item     : [{item_code}] {item_name}")
    print(f"  Location : {location}")
    print(f"  In Stock : {current_qty} units")
    print(f"  Min Stock: {min_stock} units")

    # --- Step 4: Out of stock check ---
    if current_qty == 0:
        print("\n  [OUT OF STOCK] This item is currently unavailable.")
        print("  Please contact procurement for restocking.")
        return df

    # --- Step 5: Already low before issue ---
    if current_qty <= min_stock:
        print(
            f"\n  [LOW STOCK WARNING] Only {current_qty} units left "
            f"(minimum required: {min_stock})."
        )
        print("  Procurement has been notified. Proceed with caution.")

    # --- Step 6: How many ---
    try:
        qty_requested = int(input("\n  How many units do you need? ").strip())
        if qty_requested <= 0:
            print("  [!] Quantity must be at least 1.")
            return df
    except ValueError:
        print("  [!] Please enter a valid number.")
        return df

    # --- Step 7: Insufficient stock check ---
    if qty_requested > current_qty:
        print(
            f"\n  [INSUFFICIENT STOCK] Requested {qty_requested} but "
            f"only {current_qty} available."
        )
        print(f"  Maximum you can take: {current_qty} units.")
        print("  Request blocked. Please contact procurement.")
        return df

    # --- Step 8: Confirm ---
    new_qty = current_qty - qty_requested
    print(f"\n  Confirm: Issue {qty_requested} x [{item_code}] {item_name}")
    print(f"  Stock after issue: {current_qty} - {qty_requested} = {new_qty} units")

    if new_qty < min_stock:
        print(
            f"  [!] WARNING: After this issue, stock ({new_qty}) will be "
            f"BELOW minimum ({min_stock})."
        )
        print("  Email alert will be sent to officials automatically.")

    confirm = input("\n  Confirm issue? (yes/no): ").strip().lower()
    if confirm not in ("yes", "y"):
        print("  [CANCELLED] No changes made.")
        return df

    # --- Step 9: Update DataFrame ---
    df.loc[selected_row.name, "Quantity"] = new_qty

    # --- Step 10: Save to Excel ---
    saved = save_inventory(df)

    if saved:
        print(f"\n  [OK] Issue complete!")
        print(f"  {qty_requested} x {item_name} issued to {engineer_name}.")
        print(f"  Remaining stock: {new_qty} units at {location}")

        # --- Step 11: Log transaction ---
        log_issue(engineer_name, item_code, item_name, qty_requested, new_qty)
        print(f"  [LOG] Transaction saved to issue_log.csv")

        # --- Step 12: Email alert if below minimum ---
        if new_qty < min_stock:
            print("\n  [ALERT] Stock below minimum - sending email alert...")
            if email_alerts:
                email_alerts.send_low_stock_alert(
                    item_code     = item_code,
                    item_name     = item_name,
                    qty_left      = new_qty,
                    min_stock     = min_stock,
                    location      = location,
                    engineer_name = engineer_name,
                    qty_taken     = qty_requested
                )
            else:
                print("  [EMAIL SKIPPED] email_alerts module not loaded.")

    else:
        # Save failed - reverse the in-memory change
        df.loc[selected_row.name, "Quantity"] = current_qty
        print("  [ERROR] Issue cancelled - could not save to file.")
        print("  Make sure plant_inventory.xlsx is not open in Excel.")

    return df


# =============================================================================
# FUNCTION: main
# Entry point — loads data, starts scheduler, runs menu loop
# =============================================================================

def main():
    """
    Starts the inventory assistant:
    - Loads inventory from Excel
    - Starts background email scheduler
    - Runs the interactive menu
    """

    print("\n" + "=" * 55)
    print("   AI-POWERED INSTRUMENT INVENTORY ASSISTANT")
    print("   Adani Thermal Power Plant - Main Store")
    print("=" * 55)

    # Load inventory on startup
    df = load_inventory()

    if df is None:
        print("[ABORT] Cannot start. Fix plant_inventory.xlsx and try again.")
        return

    # Start daily email report scheduler in background
    if email_alerts:
        email_alerts.start_daily_scheduler(INVENTORY_FILE)

    # --- Menu Loop ---
    while True:
        print("\n" + "-" * 40)
        print("  MAIN MENU")
        print("-" * 40)
        print("  1.  Search Instrument")
        print("  2.  Show Full Inventory")
        print("  3.  Inventory Summary")
        print("  4.  Issue Instrument (Take from Store)")
        print("  5.  Reload Inventory from Excel")
        print("  6.  Exit")
        print("-" * 40)

        choice = input("  Enter your choice (1-6): ").strip()

        if choice == "1":
            search_instrument(df)

        elif choice == "2":
            show_inventory(df)

        elif choice == "3":
            inventory_summary(df)

        elif choice == "4":
            df = issue_instrument(df)

        elif choice == "5":
            # Reload after seniors update the Excel file
            print("\n  [INFO] Make sure plant_inventory.xlsx is saved and closed in Excel.")
            confirm = input("  Reload now? (yes/no): ").strip().lower()

            if confirm in ("yes", "y"):
                new_df = load_inventory()
                if new_df is not None:
                    df = new_df
                    print("  [OK] Inventory reloaded from Excel.")
                else:
                    print("  [ERROR] Reload failed. Keeping previous data.")
            else:
                print("  [CANCELLED] Keeping previous data.")

        elif choice == "6":
            print("\nGoodbye! Exiting Inventory Assistant.\n")
            break

        else:
            print("\n  [!] Invalid choice. Please enter 1, 2, 3, 4, 5, or 6.")


# =============================================================================
# ENTRY GUARD
# =============================================================================

if __name__ == "__main__":
    main()
