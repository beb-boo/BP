
# 🩸 Blood Pressure Monitor & Telemedicine Platform

A comprehensive platform for tracking blood pressure, managing doctor-patient relationships, and empowering users with their health data.

**Key Components:**
1.  **Backend API**: Fast, Secure (Fernet Encryption), and Scalable (FastAPI).
2.  **Telegram Bot**: AI-powered OCR for effortless BP recording.
3.  **Web Application**: Modern dashboard for Patients and Doctors (Next.js).

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+ (for Web App)
- Google Gemini API Key (for OCR)

### 1️⃣ Configuration
Create a `.env` file in `app/` (copy from `.env.example` if available):
```env
# Database
DATABASE_URL=sqlite:///./blood_pressure.db

# Security
SECRET_KEY=your_super_secret_jwt_key
ENCRYPTION_KEY= # Generate using: python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
API_KEYS=bp-mobile-app-key,bp-web-app-key

# AI / OCR
GOOGLE_AI_API_KEY=your_gemini_api_key

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token

# Email / SMS (Optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_USER=your_email
EMAIL_PASSWORD=your_app_password
```

### 2️⃣ Running the Backend API
The core brain of the system.
```bash
# Install dependencies
pip install -r app/requirements.txt

# Run Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*   **Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

### 3️⃣ Running the Telegram Bot 🤖
Allows users to record BP by sending a photo.
```bash
# Run Bot (in a new terminal)
python3 -m app.bot.main
```
*   **Use it**: Open your bot in Telegram.
*   **Commands**:
    *   `/start` - Welcome & Status.
    *   `/login <email> <password>` - Link Telegram to your account.
    *   `/stats` - View recent 5 records.
    *   **[Send Photo]** - Auto-extract BP values and save.

### 4️⃣ Running the Web Application 🌐
Dashboard for patients and doctors.
```bash
cd frontend
# Install dependencies
npm install

# Run Dev Server
npm run dev
```
*   **URL**: [http://localhost:3000](http://localhost:3000)

---

## 🛠 Features Breakdown

### 🔐 Security & Privacy
*   **Field-Level Encryption**: Sensitive PII (Citizen ID, Medical License) is encrypted *before* valid storage using AES-128 (Fernet). Even database admins cannot read it without the key.
*   **Hashed Indexes**: Allows searching for unique IDs (like Citizen ID) without decrypting the entire database.
*   **Data Portability**: Users can export their full history via `/api/v1/export/my-data`.

### 🩺 For Patients
*   **Easy Recording**: Manual entry or AI Camera (OCR).
*   **Trends**: View stats (Avg, Min, Max).
*   **Doctor Access**: Grant or revoke access for doctors to view your data.

### 👨‍⚕️ For Doctors
*   **Patient List**: View all authorized patients.
*   **Access Request**: Request access to a patient's data by email/ID.
*   **Monitoring**: View patient graphs and history.

---

## 📡 Deployment Guide (Telegram Bot)

### Localhost Testing
You **do NOT** need a public IP or HTTPS to test locally because we use **Long Polling**.
1.  Ensure `TELEGRAM_BOT_TOKEN` is set in `.env`.
2.  Run `python3 -m app.bot.main`.
3.  The bot immediately starts receiving messages from Telegram servers.

### Server Deployment (Production)
For a real server (e.g., VPS, DigitalOcean, AWS):

**Option A: Long Polling (Simpler)**
*   **Pros**: Easiest setup, works behind NAT/Firewall.
*   **Cons**: Slightly slower than Webhooks for massive scale.
*   **How**: Just run the script as a background service (Systemd or Docker).

**Option B: Webhooks (Recommended for high traffic)**
*   **Pros**: Faster, serverless-friendly (like Lambda/Cloud Run).
*   **Cons**: Requires valid **HTTPS** certificate (SSL).
*   **How**:
    1.  You need a domain with SSL (e.g., `https://api.yourdomain.com`).
    2.  Set the webhook: `curl https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://api.yourdomain.com/bot-webhook`
    3.  You must modify `app/bot/main.py` to listen for requests instead of polling.
*   *Note: Current implementation calculates uses Pooling which is sufficient for < 1000 users.*

### Systemd Service Example (Linux)
Create `/etc/systemd/system/bp-bot.service`:
```ini
[Unit]
Description=BP Monitor Telegram Bot
After=network.target

[Service]
User=root
WorkingDirectory=/path/to/BP
ExecStart=/usr/bin/python3 -m app.bot.main
Restart=always
EnvironmentFile=/path/to/BP/app/.env

[Install]
WantedBy=multi-user.target
```
Then: `sudo systemctl enable --now bp-bot`

---

## 📂 Project Structure
```
BP/
├── app/                  # Backend & Bot
│   ├── bot/              # Telegram Logic
│   ├── routers/          # API Endpoints (Auth, Users, Records...)
│   ├── utils/            # Core Utility (OCR, Encryption)
│   ├── models.py         # DB Schema
│   └── main.py           # App Entry Point
├── frontend/             # Next.js Web App
│   ├── app/              # Pages & Layouts
│   ├── components/       # UI Components (Shadcn)
│   └── lib/              # API Client
└── tests/                # (Placeholder for tests)
```
