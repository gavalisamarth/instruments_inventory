# =============================================================================
# EMAIL ALERT MODULE
# File: email_alerts.py
#
# This module handles all email functionality for the inventory system:
#   1. send_low_stock_alert() - triggered immediately after an issue
#      causes stock to drop below MinStock
#   2. send_daily_report()    - sends a full low stock summary every morning
#
# Uses Python's built-in libraries:
#   smtplib  - handles the connection to Gmail's mail server
#   email    - builds the email message (subject, body, formatting)
#   schedule - runs the daily report at a fixed time every day
#
# BEGINNER NOTE:
#   Think of smtplib as a "postman" that connects to Gmail's post office
#   (smtp.gmail.com) and delivers your email to the recipients.
# =============================================================================


import smtplib                              # Connects to Gmail SMTP server
import schedule                             # Schedules daily report task
import time                                 # Used by schedule to keep running
import threading                            # Runs scheduler in background
import datetime                             # For timestamps in emails
import pandas as pd                         # To read inventory CSV
import os                                   # File path utilities

from email.mime.multipart import MIMEMultipart  # Builds email with multiple parts
from email.mime.text      import MIMEText        # Builds plain text / HTML email body

# Import our config file
try:
    import email_config as cfg
    EMAIL_MODULE_READY = True
except ImportError:
    print("[WARNING] email_config.py not found. Email alerts will be disabled.")
    EMAIL_MODULE_READY = False


# Path to the recipients Excel file
# This sits in the same folder as the script
SCRIPT_DIR          = os.path.dirname(os.path.abspath(__file__))
RECIPIENTS_FILE     = os.path.join(SCRIPT_DIR, "recipients.xlsx")


# =============================================================================
# LOAD RECIPIENTS FROM EXCEL FILE
#
# Instead of hardcoding emails in email_config.py, we read them from
# recipients.xlsx. This means plant administrators can add or remove
# recipients simply by editing the Excel file — no coding needed.
#
# The Excel file has 4 columns:
#   Name   -> Person's full name (for reference)
#   Role   -> Their role (e.g. Store Manager, HOD)
#   Email  -> Their email address
#   Active -> "yes" to include them, "no" to skip them
#
# WHY "Active" column?
# If someone goes on leave or changes role, you just change "yes" to "no"
# in Excel. No code changes needed. Very practical for real plants.
# =============================================================================

def load_recipients():
    """
    Reads the 'Email' sheet from recipients.xlsx and returns
    a list of active email addresses (where Active = 'yes').

    Falls back to email_config.RECIPIENTS if file is missing.
    """

    if not os.path.exists(RECIPIENTS_FILE):
        print("  [WARNING] recipients.xlsx not found.")
        if EMAIL_MODULE_READY:
            return cfg.RECIPIENTS
        return []

    try:
        # Read the 'Email' sheet specifically
        # recipients.xlsx has multiple sheets: Email, WhatsApp
        try:
            df = pd.read_excel(RECIPIENTS_FILE, sheet_name="Email")
        except Exception:
            # Fallback: if no sheet named 'Email', read first sheet
            df = pd.read_excel(RECIPIENTS_FILE)

        df.columns  = df.columns.str.strip()
        df["Active"] = df["Active"].astype(str).str.strip().str.lower()
        df["Email"]  = df["Email"].astype(str).str.strip()

        active_df  = df[df["Active"] == "yes"]
        recipients = active_df["Email"].tolist()

        if not recipients:
            print("  [WARNING] No active recipients in recipients.xlsx Email sheet.")
            print("  Set Active = 'yes' for at least one recipient.")
            return []

        print(f"  [OK] {len(recipients)} email recipient(s) loaded.")
        return recipients

    except Exception as e:
        print(f"  [EMAIL ERROR] Could not read recipients.xlsx: {e}")
        if EMAIL_MODULE_READY:
            return cfg.RECIPIENTS
        return []




# =============================================================================
# FUNCTION 0: SEND ISSUE CONFIRMATION EMAIL
# Triggered on EVERY instrument issue — regardless of stock level
# Sends full issue details to all active recipients
# =============================================================================

def send_issue_confirmation(engineer_name, emp_id, item_code, item_name,
                             category, location, qty_taken, qty_remaining, purpose=""):
    """
    Sends an immediate confirmation email every time an instrument is issued.

    Parameters:
        engineer_name  -> Full name of the engineer who took the item
        emp_id         -> Employee ID (optional, shown as N/A if blank)
        item_code      -> e.g. PT001
        item_name      -> e.g. Rosemount 3051 Pressure Transmitter
        category       -> e.g. Pressure Transmitter
        location       -> Rack location
        qty_taken      -> How many units were taken
        qty_remaining  -> Stock left after the issue
        purpose        -> Work order / reason (optional)
    """

    if not EMAIL_MODULE_READY:
        print("  [EMAIL SKIPPED] email_config.py not configured.")
        return False

    now      = datetime.datetime.now()
    date_str = now.strftime("%d-%m-%Y")
    time_str = now.strftime("%H:%M")
    emp_show = emp_id.strip() if emp_id and emp_id.strip() else "N/A"
    purpose_show = purpose.strip() if purpose and purpose.strip() else "Not specified"

    # Stock status label
    stock_color = "#c0392b" if qty_remaining == 0 else ("#e67e22" if qty_remaining < 5 else "#27ae60")
    stock_label = "OUT OF STOCK" if qty_remaining == 0 else f"{qty_remaining} units remaining"

    subject = (
        f"[ISSUE CONFIRMATION] {item_name} | "
        f"Issued to: {engineer_name} | {date_str} {time_str}"
    )

    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333; margin: 0; padding: 0;">

        <div style="background: #1a1a2e; padding: 20px 30px;">
            <h2 style="color: #f97316; margin: 0; font-size: 20px; letter-spacing: 1px;">
                ADANI STORE TERMINAL
            </h2>
            <p style="color: #9ca3af; margin: 4px 0 0; font-size: 12px; letter-spacing: 1px;">
                {cfg.PLANT_NAME} &nbsp;|&nbsp; {cfg.DEPARTMENT}
            </p>
        </div>

        <div style="padding: 24px 30px; background: #ffffff;">

            <h3 style="color: #111; font-size: 16px; margin: 0 0 6px;">
                ✅ Instrument Issue Confirmation
            </h3>
            <p style="color: #6b7280; font-size: 13px; margin: 0 0 24px;">
                The following instrument has been issued from the main store.
            </p>

            <table style="width:100%; border-collapse:collapse; font-size:13px; margin-bottom:24px;">

                <tr style="background:#f8f9fa;">
                    <td colspan="2" style="padding:10px 14px; font-weight:700;
                        color:#f97316; letter-spacing:0.5px; font-size:11px;
                        text-transform:uppercase; border-bottom:2px solid #f97316;">
                        ENGINEER DETAILS
                    </td>
                </tr>
                <tr>
                    <td style="padding:10px 14px; color:#6b7280; font-weight:600;
                        width:40%; border-bottom:1px solid #f0f0f0;">Engineer Name</td>
                    <td style="padding:10px 14px; color:#111; font-weight:700;
                        border-bottom:1px solid #f0f0f0;">{engineer_name}</td>
                </tr>
                <tr style="background:#f8f9fa;">
                    <td style="padding:10px 14px; color:#6b7280; font-weight:600;
                        border-bottom:1px solid #f0f0f0;">Employee ID</td>
                    <td style="padding:10px 14px; color:#111;
                        border-bottom:1px solid #f0f0f0;">{emp_show}</td>
                </tr>

                <tr>
                    <td colspan="2" style="padding:10px 14px; font-weight:700;
                        color:#f97316; letter-spacing:0.5px; font-size:11px;
                        text-transform:uppercase; border-bottom:2px solid #f97316;
                        border-top:12px solid #f8f9fa;">
                        INSTRUMENT DETAILS
                    </td>
                </tr>
                <tr style="background:#f8f9fa;">
                    <td style="padding:10px 14px; color:#6b7280; font-weight:600;
                        border-bottom:1px solid #f0f0f0;">Item Code</td>
                    <td style="padding:10px 14px; color:#f97316; font-weight:700;
                        border-bottom:1px solid #f0f0f0;">{item_code}</td>
                </tr>
                <tr>
                    <td style="padding:10px 14px; color:#6b7280; font-weight:600;
                        border-bottom:1px solid #f0f0f0;">Instrument Name</td>
                    <td style="padding:10px 14px; color:#111; font-weight:600;
                        border-bottom:1px solid #f0f0f0;">{item_name}</td>
                </tr>
                <tr style="background:#f8f9fa;">
                    <td style="padding:10px 14px; color:#6b7280; font-weight:600;
                        border-bottom:1px solid #f0f0f0;">Category</td>
                    <td style="padding:10px 14px; color:#111;
                        border-bottom:1px solid #f0f0f0;">{category}</td>
                </tr>
                <tr>
                    <td style="padding:10px 14px; color:#6b7280; font-weight:600;
                        border-bottom:1px solid #f0f0f0;">Store Location</td>
                    <td style="padding:10px 14px; color:#111;
                        border-bottom:1px solid #f0f0f0;">{location}</td>
                </tr>

                <tr>
                    <td colspan="2" style="padding:10px 14px; font-weight:700;
                        color:#f97316; letter-spacing:0.5px; font-size:11px;
                        text-transform:uppercase; border-bottom:2px solid #f97316;
                        border-top:12px solid #f8f9fa;">
                        TRANSACTION DETAILS
                    </td>
                </tr>
                <tr style="background:#f8f9fa;">
                    <td style="padding:10px 14px; color:#6b7280; font-weight:600;
                        border-bottom:1px solid #f0f0f0;">Quantity Issued</td>
                    <td style="padding:10px 14px; color:#111; font-weight:700;
                        border-bottom:1px solid #f0f0f0;">{qty_taken} unit(s)</td>
                </tr>
                <tr>
                    <td style="padding:10px 14px; color:#6b7280; font-weight:600;
                        border-bottom:1px solid #f0f0f0;">Stock Remaining</td>
                    <td style="padding:10px 14px; font-weight:700;
                        color:{stock_color}; border-bottom:1px solid #f0f0f0;">
                        {stock_label}
                    </td>
                </tr>
                <tr style="background:#f8f9fa;">
                    <td style="padding:10px 14px; color:#6b7280; font-weight:600;
                        border-bottom:1px solid #f0f0f0;">Date &amp; Time</td>
                    <td style="padding:10px 14px; color:#111;
                        border-bottom:1px solid #f0f0f0;">{date_str} at {time_str}</td>
                </tr>
                <tr>
                    <td style="padding:10px 14px; color:#6b7280; font-weight:600;">
                        Purpose / Work Order</td>
                    <td style="padding:10px 14px; color:#111;">{purpose_show}</td>
                </tr>

            </table>

            <hr style="border:none; border-top:1px solid #e5e7eb; margin:20px 0;">
            <p style="font-size:11px; color:#9ca3af; margin:0;">
                This is an automated confirmation from the {cfg.DEPARTMENT}
                Inventory Assistant. Do not reply to this email.
            </p>
        </div>

    </body>
    </html>
    """

    return _send_email(subject, body_html)


# =============================================================================
# FUNCTION 1: SEND LOW STOCK ALERT
# Triggered immediately when an issue causes stock to drop below MinStock
# =============================================================================

def send_low_stock_alert(item_code, item_name, qty_left, min_stock,
                          location, engineer_name, qty_taken):
    """
    Sends an immediate email alert to all recipients when an instrument's
    stock falls below the minimum required level after being issued.

    Parameters:
        item_code     -> e.g. PT001
        item_name     -> e.g. Rosemount 3051 Pressure Transmitter
        qty_left      -> Quantity remaining after the issue
        min_stock     -> Minimum stock threshold
        location      -> Rack location in store
        engineer_name -> Who took the item
        qty_taken     -> How many were taken
    """

    if not EMAIL_MODULE_READY:
        print("  [EMAIL SKIPPED] email_config.py not configured.")
        return False

    # ------------------------------------------------------------------
    # BUILD THE EMAIL SUBJECT
    # ------------------------------------------------------------------
    now        = datetime.datetime.now()
    date_str   = now.strftime("%d-%m-%Y")
    time_str   = now.strftime("%H:%M")

    subject = (
        f"[LOW STOCK ALERT] {item_name} | "
        f"Qty: {qty_left} | {cfg.PLANT_NAME} | {date_str}"
    )

    # ------------------------------------------------------------------
    # BUILD THE EMAIL BODY (HTML format for professional appearance)
    #
    # HTML emails look like a formatted document instead of plain text.
    # We write the email body as an HTML string.
    # ------------------------------------------------------------------
    body_html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">

        <h2 style="color: #c0392b;">
            &#9888; LOW STOCK ALERT
        </h2>

        <p>
            This is an automated alert from the
            <strong>{cfg.PLANT_NAME}</strong> Inventory System.<br>
            An instrument has been issued and stock has dropped
            below the minimum required level.
        </p>

        <hr>

        <h3>Issue Details</h3>
        <table border="1" cellpadding="8" cellspacing="0"
               style="border-collapse: collapse; width: 100%;">
            <tr style="background-color: #f2f2f2;">
                <td><strong>Item Code</strong></td>
                <td>{item_code}</td>
            </tr>
            <tr>
                <td><strong>Item Name</strong></td>
                <td>{item_name}</td>
            </tr>
            <tr style="background-color: #f2f2f2;">
                <td><strong>Location</strong></td>
                <td>{location}</td>
            </tr>
            <tr>
                <td><strong>Issued To</strong></td>
                <td>{engineer_name}</td>
            </tr>
            <tr style="background-color: #f2f2f2;">
                <td><strong>Quantity Taken</strong></td>
                <td>{qty_taken} units</td>
            </tr>
            <tr>
                <td><strong>Quantity Remaining</strong></td>
                <td style="color: #c0392b; font-weight: bold;">
                    {qty_left} units
                </td>
            </tr>
            <tr style="background-color: #f2f2f2;">
                <td><strong>Minimum Required</strong></td>
                <td>{min_stock} units</td>
            </tr>
            <tr>
                <td><strong>Date & Time</strong></td>
                <td>{date_str} at {time_str}</td>
            </tr>
        </table>

        <br>
        <p style="color: #c0392b; font-weight: bold;">
            &#9888; Please arrange for immediate procurement/restocking.
        </p>

        <hr>
        <p style="font-size: 12px; color: #888;">
            This is an automated message from the {cfg.DEPARTMENT}
            Inventory Assistant. Do not reply to this email.
        </p>

    </body>
    </html>
    """

    # Send the email
    return _send_email(subject, body_html)


# =============================================================================
# FUNCTION 2: SEND DAILY LOW STOCK REPORT
# Runs every morning at the time set in email_config.py
# Scans ALL items below MinStock and sends a full report
# =============================================================================

def send_daily_report(inventory_file_path):
    """
    Reads the inventory Excel file, finds all items below MinStock,
    and sends a formatted daily report email.

    Parameter:
        inventory_file_path -> Full path to plant_inventory.xlsx
    """

    if not EMAIL_MODULE_READY:
        return False

    # Load inventory fresh from Excel
    try:
        df = pd.read_excel(inventory_file_path, sheet_name="Inventory")
        df.columns = df.columns.str.strip()
        df = df.dropna(subset=["ItemCode", "ItemName"])
    except Exception as e:
        print(f"[EMAIL ERROR] Could not read inventory for daily report: {e}")
        return False

    # Find all items where Quantity is less than MinStock
    low_stock_df = df[df["Quantity"] < df["MinStock"]].copy()

    # ------------------------------------------------------------------
    # BUILD EMAIL SUBJECT
    # ------------------------------------------------------------------
    now      = datetime.datetime.now()
    date_str = now.strftime("%d-%m-%Y")

    if low_stock_df.empty:
        subject = (
            f"[DAILY REPORT] All Stock OK | "
            f"{cfg.PLANT_NAME} | {date_str}"
        )
    else:
        subject = (
            f"[DAILY REPORT] {len(low_stock_df)} Items Below Min Stock | "
            f"{cfg.PLANT_NAME} | {date_str}"
        )

    # ------------------------------------------------------------------
    # BUILD EMAIL BODY (HTML)
    # ------------------------------------------------------------------

    if low_stock_df.empty:
        # All good — send a positive report
        body_html = f"""
        <html><body style="font-family: Arial, sans-serif; color: #333;">
            <h2 style="color: #27ae60;">Daily Inventory Report — {date_str}</h2>
            <p><strong>{cfg.PLANT_NAME}</strong> | {cfg.DEPARTMENT}</p>
            <hr>
            <p style="color: #27ae60; font-size: 18px;">
                &#10003; All instrument stock levels are within acceptable limits.
            </p>
            <p>No procurement action required today.</p>
            <hr>
            <p style="font-size: 12px; color: #888;">
                Automated Daily Report — {cfg.DEPARTMENT} Inventory System
            </p>
        </body></html>
        """
    else:
        # Build HTML table rows for each low stock item
        table_rows = ""
        for _, row in low_stock_df.iterrows():
            # Calculate how short we are
            shortfall = int(row["MinStock"]) - int(row["Quantity"])

            # Color-code rows: red if zero stock, orange if low
            if row["Quantity"] == 0:
                row_color = "#ffcccc"  # Red background
                status    = "OUT OF STOCK"
            else:
                row_color = "#fff3cd"  # Yellow/orange background
                status    = "LOW STOCK"

            table_rows += f"""
            <tr style="background-color: {row_color};">
                <td>{row['ItemCode']}</td>
                <td>{row['ItemName']}</td>
                <td>{row['Category']}</td>
                <td style="text-align:center;">{int(row['Quantity'])}</td>
                <td style="text-align:center;">{int(row['MinStock'])}</td>
                <td style="text-align:center; color: #c0392b;">
                    <strong>-{shortfall}</strong>
                </td>
                <td>{row['Location']}</td>
                <td style="font-weight: bold;">{status}</td>
            </tr>
            """

        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333;">

            <h2 style="color: #e67e22;">
                Daily Inventory Report — {date_str}
            </h2>
            <p><strong>{cfg.PLANT_NAME}</strong> | {cfg.DEPARTMENT}</p>

            <hr>

            <p style="color: #c0392b;">
                <strong>&#9888; {len(low_stock_df)} item(s) are below
                minimum stock level and require procurement attention.</strong>
            </p>

            <table border="1" cellpadding="8" cellspacing="0"
                   style="border-collapse: collapse; width: 100%;
                          font-size: 13px;">
                <thead>
                    <tr style="background-color: #2c3e50; color: white;">
                        <th>Item Code</th>
                        <th>Item Name</th>
                        <th>Category</th>
                        <th>Current Qty</th>
                        <th>Min Stock</th>
                        <th>Shortfall</th>
                        <th>Location</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>

            <br>
            <p>Please initiate procurement for the above items at the earliest.</p>

            <hr>
            <p style="font-size: 12px; color: #888;">
                This is an automated daily report generated at
                {now.strftime("%H:%M")} by the {cfg.DEPARTMENT}
                Inventory Assistant. Do not reply to this email.
            </p>

        </body>
        </html>
        """

    return _send_email(subject, body_html)


# =============================================================================
# PRIVATE HELPER: _send_email()
#
# The underscore prefix (_) is a Python convention meaning:
# "This function is for internal use only — don't call it from outside."
#
# This function handles the actual SMTP connection and email transmission.
# Both send_low_stock_alert() and send_daily_report() use this same function.
# This avoids repeating the SMTP connection code twice.
# =============================================================================

def _send_email(subject, body_html):
    """
    Internal helper. Connects to Gmail SMTP and sends the email.

    Parameters:
        subject   -> Email subject line
        body_html -> HTML formatted email body
    Returns:
        True if sent successfully, False if failed
    """

    try:
        # ------------------------------------------------------------------
        # LOAD RECIPIENTS FRESH FROM EXCEL EVERY TIME
        # This means if someone updates recipients.xlsx while the program
        # is running, the next email will use the updated list automatically
        # ------------------------------------------------------------------
        recipients = load_recipients()

        if not recipients:
            print("  [EMAIL ERROR] No active recipients found. Email not sent.")
            return False

        # ------------------------------------------------------------------
        # BUILD THE EMAIL MESSAGE OBJECT
        # ------------------------------------------------------------------
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"]    = cfg.SENDER_EMAIL
        message["To"]      = ", ".join(recipients)

        # Attach the HTML body to the message
        html_part = MIMEText(body_html, "html")
        message.attach(html_part)

        # ------------------------------------------------------------------
        # CONNECT TO GMAIL SMTP SERVER
        #
        # smtplib.SMTP() opens a connection to Gmail's mail server
        # Port 587 is the standard port for secure email (TLS encryption)
        #
        # with statement ensures the connection is closed automatically
        # even if something goes wrong — this is called a "context manager"
        # ------------------------------------------------------------------
        with smtplib.SMTP(cfg.SMTP_SERVER, cfg.SMTP_PORT) as server:

            # Start TLS encryption (secures the connection like HTTPS)
            server.starttls()

            # Log in with sender email and App Password
            server.login(cfg.SENDER_EMAIL, cfg.SENDER_PASSWORD)

            # Send the email to all active recipients from Excel file
            server.sendmail(
                cfg.SENDER_EMAIL,
                recipients,
                message.as_string()
            )

        print(f"  [EMAIL SENT] Alert sent to {len(recipients)} recipient(s).")
        return True

    except smtplib.SMTPAuthenticationError:
        # This error means the App Password is wrong or not set up
        print("  [EMAIL ERROR] Authentication failed!")
        print("  Make sure you have set SENDER_PASSWORD in email_config.py")
        print("  Use a Gmail App Password, NOT your regular Gmail password.")
        print("  Guide: myaccount.google.com → Search 'App Passwords'")
        return False

    except smtplib.SMTPException as e:
        print(f"  [EMAIL ERROR] SMTP error: {e}")
        return False

    except Exception as e:
        print(f"  [EMAIL ERROR] Unexpected error: {e}")
        return False


# =============================================================================
# DAILY REPORT SCHEDULER
#
# schedule library lets us run a function at a fixed time every day.
# We run the scheduler in a BACKGROUND THREAD so it doesn't block
# the main program's menu from working.
#
# WHAT IS A THREAD?
# Imagine your program is one worker doing tasks one at a time.
# A thread is a second worker running alongside the first.
# The scheduler thread watches the clock in the background.
# The main thread keeps showing the menu to the engineer.
# Both run at the same time without interrupting each other.
# =============================================================================

def start_daily_scheduler(inventory_file_path):
    """
    Starts the background scheduler that sends the daily email report
    every morning at the time set in email_config.py.

    Runs in a background thread so the main menu is not blocked.

    Parameter:
        inventory_file_path -> Path to plant_inventory.xlsx
    """

    if not EMAIL_MODULE_READY:
        return

    schedule.every().day.at(cfg.DAILY_REPORT_TIME).do(
        send_daily_report, inventory_file_path=inventory_file_path
    )

    print(f"  [SCHEDULER] Daily email report scheduled at {cfg.DAILY_REPORT_TIME}.")

    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(30)

    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
