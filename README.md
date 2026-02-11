# CONDUSEF SOFIPO Credit Dashboard

Live dashboard tracking credit portfolio data for Mexican SOFIPOs (Klar, Stori, NU México, Libertad, Sustentable) from CONDUSEF.

**Dashboard:** Hosted via GitHub Pages at `https://<your-username>.github.io/<repo-name>/`

## 🚀 Setup Instructions

### 1. Create the repository
Push all files to a new GitHub repository.

### 2. Enable GitHub Pages
- Go to **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: `main`, folder: `/ (root)`
- Save — site will be live in ~1 minute

### 3. Configure email alerts (one-time setup)

The workflow sends alerts to:
- mateus.raffaelli@itaubba.com
- pedro.leduc@itaubba.com
- mateusrsx@gmail.com

**Steps to enable:**

#### a) Create a Gmail App Password
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** if not already on
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Create a new app password (name it "CONDUSEF Monitor")
5. Copy the 16-character password

#### b) Add GitHub Secrets
1. Go to your repo → **Settings → Secrets and variables → Actions**
2. Click **New repository secret** and add:
   - `GMAIL_USER` → your Gmail address (e.g., `mateusrsx@gmail.com`)
   - `GMAIL_APP_PASSWORD` → the 16-char app password from step (a)

### 4. Test the workflow
- Go to **Actions** tab in your repo
- Click **"Check CONDUSEF for new SOFIPO data"**
- Click **"Run workflow"** → **"Run workflow"**
- Check the run logs — it should find Jan 2026 data and send an email

## 📁 File Structure

```
├── index.html                              # Dashboard (GitHub Pages)
├── scripts/
│   ├── check_condusef.py                   # CONDUSEF monitor script
│   └── last_known_date.json                # State tracker (auto-updated)
├── .github/
│   └── workflows/
│       └── check-condusef.yml              # Daily check workflow
└── README.md
```

## ⚙️ How it works

1. **GitHub Actions** runs `check_condusef.py` daily at 14:00 UTC
2. The script checks CONDUSEF for months after the last known date
3. If new data is found → sends a styled HTML email to all recipients
4. Updates `last_known_date.json` so it doesn't alert again for the same month
5. The dashboard itself also fetches live data on each page load via CORS proxy

## 📧 Modifying recipients

Edit the `RECIPIENTS` list in `scripts/check_condusef.py`:

```python
RECIPIENTS = [
    "mateus.raffaelli@itaubba.com",
    "pedro.leduc@itaubba.com",
    "mateusrsx@gmail.com",
]
```
