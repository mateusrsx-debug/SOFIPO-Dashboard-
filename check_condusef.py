"""
CONDUSEF SOFIPO Data Monitor
Checks for new monthly data on CONDUSEF and sends email alerts when updates are found.
Runs via GitHub Actions on a daily schedule.
"""

import requests
import json
import os
import smtplib
import sys
from datetime import datetime
from html.parser import HTMLParser
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ============= CONFIG =============
CONDUSEF_URL = "https://registros.condusef.gob.mx/reco/cartera_credito_institucion.php"
STATE_FILE = "scripts/last_known_date.json"

ENTITIES = {
    "Klar Technologies": "Klar",
    "Libertad Servicios Financieros": "Libertad",
    "Stori México": "Stori",
    "Financiera Sustentable": "Sustentable",
    "NU México Financiera": "NU México",
}

RECIPIENTS = [
    "mateus.raffaelli@itaubba.com",
    "pedro.leduc@itaubba.com",
    "mateusrsx@gmail.com",
]

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


# ============= HTML TABLE PARSER =============
class CONDUSEFParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_td = False
        self.current_row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "td":
            self.in_td = True
            self.current_cell = ""
        if tag == "tr":
            self.current_row = []

    def handle_endtag(self, tag):
        if tag == "td":
            self.in_td = False
            self.current_row.append(self.current_cell.strip())
        if tag == "tr" and len(self.current_row) >= 5:
            self.rows.append(self.current_row[:5])

    def handle_data(self, data):
        if self.in_td:
            self.current_cell += data


def parse_number(s):
    try:
        return int(s.replace(",", "").strip())
    except (ValueError, AttributeError):
        return 0


def parse_pct(s):
    try:
        return float(s.replace("%", "").strip())
    except (ValueError, AttributeError):
        return 0.0


# ============= CONDUSEF FETCH =============
def fetch_month(year, month):
    """Fetch CONDUSEF data for a specific month. Returns dict or None."""
    params = {"sec": 27, "anio_s": year, "trim_s": month, "mone_s": "peso"}
    try:
        resp = requests.get(CONDUSEF_URL, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Request failed for {year}-{month:02d}: {e}")
        return None

    if "CARTERA TOTAL" not in resp.text:
        return None

    parser = CONDUSEFParser()
    parser.feed(resp.text)

    results = {}
    for row in parser.rows:
        name = row[0]
        for search_name, short_name in ENTITIES.items():
            if search_name in name:
                results[short_name] = {
                    "cartera_total": parse_number(row[1]),
                    "cartera_vigente": parse_number(row[2]),
                    "cartera_vencida": parse_number(row[3]),
                    "imora": parse_pct(row[4]),
                }

    return results if results else None


def next_month(year, month):
    if month == 12:
        return year + 1, 1
    return year, month + 1


# ============= STATE MANAGEMENT =============
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_year": 2025, "last_month": 12}


def save_state(year, month):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_year": year, "last_month": month}, f, indent=2)


# ============= EMAIL =============
def format_number(n):
    """Format as MXN currency."""
    if n >= 1e9:
        return f"${n/1e9:,.1f}B"
    if n >= 1e6:
        return f"${n/1e6:,.1f}M"
    if n >= 1e3:
        return f"${n/1e3:,.1f}K"
    return f"${n:,.0f}"


def build_email_html(new_periods):
    """Build a styled HTML email with the new data."""
    rows_html = ""
    for period, data in new_periods.items():
        rows_html += f"""
        <tr style="background:#FFF7ED;">
            <td colspan="5" style="padding:12px 16px; font-weight:700; font-size:15px; color:#EC7000; border-bottom:2px solid #EC7000;">
                📅 {period}
            </td>
        </tr>"""
        for entity, vals in sorted(data.items()):
            imora_color = "#059669" if vals["imora"] < 10 else ("#d97706" if vals["imora"] < 20 else "#dc2626")
            rows_html += f"""
        <tr>
            <td style="padding:10px 16px; border-bottom:1px solid #f3f4f6; font-weight:600;">{entity}</td>
            <td style="padding:10px 16px; border-bottom:1px solid #f3f4f6; text-align:right; font-variant-numeric:tabular-nums;">{format_number(vals['cartera_total'])}</td>
            <td style="padding:10px 16px; border-bottom:1px solid #f3f4f6; text-align:right; font-variant-numeric:tabular-nums;">{format_number(vals['cartera_vigente'])}</td>
            <td style="padding:10px 16px; border-bottom:1px solid #f3f4f6; text-align:right; font-variant-numeric:tabular-nums;">{format_number(vals['cartera_vencida'])}</td>
            <td style="padding:10px 16px; border-bottom:1px solid #f3f4f6; text-align:right; font-weight:700; color:{imora_color};">{vals['imora']:.1f}%</td>
        </tr>"""

    html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif; max-width:700px; margin:0 auto; background:#fff;">
        <div style="background:#1a1a2e; padding:24px 30px; border-radius:12px 12px 0 0;">
            <table><tr>
                <td><h1 style="color:#fff; font-size:20px; margin:0;">🔔 CONDUSEF SOFIPO Data Update</h1>
                <p style="color:#9ca3af; font-size:13px; margin:4px 0 0;">New credit portfolio data available</p></td>
                <td style="text-align:right; padding-left:20px;">
                    <div style="background:#EC7000; color:#fff; padding:8px 14px; border-radius:8px; font-weight:700; font-size:14px;">
                        Itaú BBA<br><span style="font-weight:400; font-size:11px;">Equity Research</span>
                    </div>
                </td>
            </tr></table>
        </div>

        <div style="padding:24px 30px;">
            <p style="color:#374151; font-size:14px; margin-bottom:20px;">
                New monthly data has been published on CONDUSEF for the tracked SOFIPOs.
                The dashboard has been updated automatically.
            </p>

            <table style="width:100%; border-collapse:collapse; font-size:13px; border:1px solid #e5e7eb; border-radius:8px;">
                <thead>
                    <tr style="background:#1a1a2e;">
                        <th style="padding:12px 16px; color:#fff; text-align:left; font-size:12px;">Entity</th>
                        <th style="padding:12px 16px; color:#fff; text-align:right; font-size:12px;">Total Loans</th>
                        <th style="padding:12px 16px; color:#fff; text-align:right; font-size:12px;">Performing</th>
                        <th style="padding:12px 16px; color:#fff; text-align:right; font-size:12px;">Non-Performing</th>
                        <th style="padding:12px 16px; color:#fff; text-align:right; font-size:12px;">IMORA</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <p style="color:#6b7280; font-size:12px; margin-top:24px; padding-top:16px; border-top:1px solid #e5e7eb;">
                Source: <a href="https://registros.condusef.gob.mx" style="color:#EC7000;">registros.condusef.gob.mx</a> — Section 27 (SOFIPOs)<br>
                This is an automated alert from the CONDUSEF SOFIPO Credit Dashboard.
            </p>
        </div>
    </div>"""
    return html


def send_email(subject, html_body):
    """Send email via Gmail SMTP using App Password."""
    sender = os.environ.get("GMAIL_USER")
    password = os.environ.get("GMAIL_APP_PASSWORD")

    if not sender or not password:
        print("ERROR: GMAIL_USER or GMAIL_APP_PASSWORD not set.")
        print("Skipping email — printing data to console instead.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"CONDUSEF Monitor <{sender}>"
    msg["To"] = ", ".join(RECIPIENTS)

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, RECIPIENTS, msg.as_string())
        print(f"✅ Email sent to {len(RECIPIENTS)} recipients.")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


# ============= MAIN =============
def main():
    print("=" * 50)
    print("CONDUSEF SOFIPO Data Monitor")
    print(f"Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    state = load_state()
    last_y, last_m = state["last_year"], state["last_month"]
    print(f"Last known data: {last_y}-{last_m:02d}")

    now = datetime.now()
    current_y, current_m = now.year, now.month

    check_y, check_m = next_month(last_y, last_m)
    new_periods = {}

    while (check_y, check_m) <= (current_y, current_m):
        date_str = f"{check_y}-{check_m:02d}"
        print(f"Checking {date_str}...", end=" ")

        data = fetch_month(check_y, check_m)
        if data:
            period_label = f"{MONTH_NAMES[check_m]} {check_y}"
            new_periods[period_label] = data
            last_y, last_m = check_y, check_m
            print(f"✅ Found {len(data)} entities")
        else:
            print("No data yet")
            break

        check_y, check_m = next_month(check_y, check_m)

    if new_periods:
        period_count = len(new_periods)
        period_names = ", ".join(new_periods.keys())
        print(f"\n🔔 {period_count} new period(s) found: {period_names}")

        subject = f"🔔 CONDUSEF SOFIPO Update — {period_names}"
        html = build_email_html(new_periods)
        send_email(subject, html)

        save_state(last_y, last_m)
        print(f"State updated to {last_y}-{last_m:02d}")
    else:
        print("\n✅ No new data. Everything up to date.")

    return 1 if new_periods else 0


if __name__ == "__main__":
    sys.exit(main())
