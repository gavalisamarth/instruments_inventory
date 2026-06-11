# =============================================================================
# EMAIL CONFIGURATION FILE
# File: email_config.py
#
# SECURITY RULES:
#   1. NEVER share this file with anyone
#   2. NEVER upload this file to GitHub or any cloud service
#   3. This file contains sensitive credentials
#
# HOW TO GET YOUR GMAIL APP PASSWORD:
#   Step 1: Go to https://myaccount.google.com
#   Step 2: Search "App Passwords" in the search bar
#   Step 3: Click App Passwords
#   Step 4: Select app: Mail | Select device: Windows Computer
#   Step 5: Click Generate
#   Step 6: Copy the 16-character password shown
#   Step 7: Paste it below (remove the spaces)
#
# NOTE: An App Password is NOT your regular Gmail password.
#       It is a special one-time password only for this program.
# =============================================================================


# --- SENDER DETAILS ---
# The Gmail account your bot uses to send emails
SENDER_EMAIL    = "whysamarthh@gmail.com"
SENDER_PASSWORD = "wjnvlsliquskadqr"
# Example: SENDER_PASSWORD = "abcdefghijklmnop"


# --- RECIPIENT LIST ---
# Add as many email addresses as needed
# These people will receive ALL alerts and daily reports
RECIPIENTS = [
    "samarthdgavali@gmail.com",       # Official / Procurement (example)
    # Add more real recipient emails below when ready:
    # "storemanager@powerplant.com",
    # "hod.ci@powerplant.com",
]
# To add more: just add another line like:
# "newperson@example.com",


# --- GMAIL SMTP SERVER SETTINGS ---
# Do not change these unless you switch from Gmail
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 587    # Port 587 uses TLS encryption (secure connection)


# --- DAILY REPORT SCHEDULE ---
# Time to send the daily morning low-stock report
# Format: "HH:MM" in 24-hour time
DAILY_REPORT_TIME = "08:00"


# --- PLANT DETAILS (used in email subject and body) ---
PLANT_NAME  = "Thermal Power Plant - Main Store"
DEPARTMENT  = "Control & Instrumentation"


# =============================================================================
# TWILIO WHATSAPP CONFIGURATION
#
# HOW TO GET THESE VALUES:
#   Step 1: Go to https://twilio.com and log in
#   Step 2: On the Console dashboard you will see:
#           Account SID  -> copy it here
#           Auth Token   -> click the eye icon, copy it here
#   Step 3: Go to Messaging -> Try it out -> Send a WhatsApp message
#           The sandbox number shown (e.g. +14155238886) goes in TWILIO_WHATSAPP_NUMBER
#
# SANDBOX SETUP (one time per recipient phone):
#   Each person who should receive WhatsApp alerts must send:
#   "join <your-sandbox-word>" to the Twilio sandbox number ONCE.
#   After that, they will receive all alerts automatically.
# =============================================================================

TWILIO_ACCOUNT_SID      = "PASTE_YOUR_ACCOUNT_SID_HERE"
TWILIO_AUTH_TOKEN       = "PASTE_YOUR_AUTH_TOKEN_HERE"
TWILIO_WHATSAPP_NUMBER  = "whatsapp:+14155238886"  # Twilio sandbox number

# Set to True to enable WhatsApp alerts alongside emails
# Set to False to disable WhatsApp without changing any other code
WHATSAPP_ALERTS_ENABLED = True
