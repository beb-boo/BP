# Telegram Bot User Guide - Blood Pressure Monitor

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Sign Up / Connect Account](#2-sign-up--connect-account)
3. [Record Blood Pressure](#3-record-blood-pressure)
4. [View Statistics & Charts](#4-view-statistics--charts)
5. [Settings (Language / Timezone)](#5-settings)
6. [Upgrade to Premium](#6-upgrade-to-premium)
7. [All Commands](#7-all-commands)
8. [Frequently Asked Questions (FAQ)](#8-faq)

---

## 1. Getting Started

### Find the Bot

Open the Telegram app and search for our Bot using the designated username, or click the link provided by the system.

### Type /start

Type `/start` to begin. The Bot will ask you to **share your phone number** via a button that appears on the screen.

> Click the "Share Contact" button to send your phone number to the Bot.

---

## 2. Sign Up / Connect Account

After sharing your phone number, there are 2 scenarios:

### Scenario A: Already have an account (registered via website)

The Bot will find the account linked to this phone number and ask for your password:

```text
An account registered with this number was found.
Please enter your password to connect your account:
```

Type the password you used to register on the website → Connection successful, ready to use.

### Scenario B: Don't have an account (register via Bot)

The Bot will guide you through the registration steps one by one:

| Step | Action | Example |
|------|--------|---------|
| 1 | Enter Full Name | `John Doe` |
| 2 | Enter Date of Birth (DD/MM/YYYY) | `15/06/1985` |
| 3 | Select Gender (press button) | Male / Female / Other |
| 4 | Select Role (press button) | Patient / Doctor |
| 5 | Set Password (8+ characters) | `MyP@ss1234` |

> **For Doctors:** The system will automatically verify your medical license.

Registration complete → Account is created and linked to Telegram immediately. Ready to use.

### Scenario C: Connect via Website Link

If you registered via the website, go to the Settings page on the web → click "Connect Telegram" → the system will generate a link to click → open it in Telegram → Connection successful without entering a password.

---

## 3. Record Blood Pressure

There are 3 methods:

### Method 1: Mini App (Recommended)

Type `/bp` → press the **"📝 Record BP"** button → Mini App opens inside Telegram.

Mini App features:
- BP input form (SYS/DIA/PULSE) + camera button (OCR)
- Average stats + AHA classification level
- 5 most recent records
- Advanced stats for Premium users (SD, PP, MAP, Trend)

> The Mini App button also appears after `/start` and `/stats`.

### Method 2: Take a Photo of the Monitor

**Steps:**

1. **Take a photo** of the blood pressure monitor screen.
2. **Send the photo** to the Bot (as a photo or a file).
3. The Bot will analyze the image using AI and display the extracted values:

```text
I read:
Sys: 120
Dia: 80
Pulse: 72
Date: 2026-03-15
Time: 14:30

Is this correct?
[✅ Correct] [✏️ Edit]
```

4. **If the values are correct** → press the "✅ Correct" button → Record saved.
5. **If the values are incorrect** → press the "✏️ Edit" button → Type the correct values manually (see Method 3).

> ⏳ **Auto-Save System:** If you send a photo and forget to press the confirm button, or if you close the chat, the system will assume the values are correct and **automatically save the data within 2 minutes** to prevent data loss.

**Supported file formats:** JPEG, PNG

**Tips for accurate AI reading:**
- Take the photo straight on, not tilted, with no shadows blocking the screen.
- Ensure all 3 numbers (SYS, DIA, Pulse) are visible.
- Make sure the monitor screen is bright enough.

### Method 3: Manual Input

If you press "✏️ Edit" after the AI reads the values, or if you just want to record values directly, use the following format:

```text
SYS/DIA PULSE
```

**Example:**

```text
120/80 72
```

Meaning: Systolic 120, Diastolic 80, Pulse 72.

**Other accepted formats:**

- `120 80 72` (using spaces — highly recommended, easiest as no need to switch keyboard symbols)
- `120/80 72`
- `120/80/72`
- `120-80-72`

---

## 4. View Statistics & Charts

### Type /stats

The Bot will display:

**1) Average Statistics + Classification**

```text
📊 Blood Pressure Statistics
Average (from 10 records):
120/80 mmHg (Pulse 72)
🟢 Classification: Normal
```

Blood pressure classification per AHA/ACC 2017 guidelines:

| Level | SBP | DBP | Symbol |
|-------|-----|-----|--------|
| Normal | < 120 | < 80 | 🟢 |
| Elevated | 120-129 | < 80 | 🟡 |
| Hypertension Stage 1 | 130-139 | 80-89 | 🟠 |
| Hypertension Stage 2 | >= 140 | >= 90 | 🔴 |
| Hypertensive Crisis | > 180 | > 120 | 🚨 |

**2) Advanced Statistics (Premium only)**

```text
Advanced Stats (Premium)
• SD: 120 ± 8.5 / 80 ± 6.2 mmHg
• Pulse Pressure: 40 mmHg
• MAP: 93 mmHg
• Trend: 📈 Increasing (+0.5 mmHg/day)
```

**Calculation formulas:**

| Value | Formula | Meaning |
|-------|---------|---------|
| **Mean (Average)** | `sum(values) / n` | Central tendency |
| **SD (Standard Deviation)** | `sqrt(sum((x - mean)^2) / (n-1))` | BP variability — high SD = unstable readings |
| **Pulse Pressure (PP)** | `avg_SBP - avg_DBP` | PP > 60 = arterial stiffness |
| **MAP (Mean Arterial Pressure)** | `(avg_SBP + 2 × avg_DBP) / 3` | MAP >= 65 = adequate perfusion |
| **CV (Coefficient of Variation)** | `(SD / Mean) × 100` (%) | Compare variability between individuals |
| **Median** | Middle value when sorted | Robust to outliers |
| **Trend** | Linear regression slope | slope > 0 = BP increasing over time |

**3) Recent Records**

```text
Recent entries: (10/25)
- 15/03/2026 14:30: 120/80 (72)
- 14/03/2026 10:15: 118/78 (70)
...
```

**4) Quick Buttons**

After /stats, buttons are shown:
- **📝 Record BP** → Opens Mini App
- **🌐 Dashboard** → Opens web Dashboard

**5) Blood Pressure Trend Chart**

If there are 2 or more entries, the Bot will automatically send a **Chart Image** showing:

- Red line: Systolic
- Blue line: Diastolic
- Dotted green line: Pulse
- Light red zone: High blood pressure range (> 140)
- Light blue zone: Elevated diastolic range (90-140)
- SYS/DIA values displayed at each point
- Pulse values displayed below the green points

---

## 5. Settings

### Type /settings

The Bot will show the current settings:

```text
⚙️ Settings

🌐 Language: English
🕐 Timezone: Asia/Bangkok

[🌐 Language] [🕐 Timezone]
```

### Change Language

Press "🌐 Language" → select:
- 🇬🇧 English
- 🇹🇭 Thai

All messages will instantly switch to the selected language.

### Change Timezone

Press "🕐 Timezone" → select from the list, e.g.:
- Asia/Bangkok (GMT+7)
- Asia/Tokyo (GMT+9)
- America/New_York (GMT-5)
- Europe/London (GMT+0)

> Timezone affects the Date/Time recorded for each entry.

---

## 6. Upgrade to Premium

### Differences between Free and Premium

| Feature | Free | Premium |
|---------|------|---------|
| Record blood pressure | ✅ | ✅ |
| View stats + charts | ✅ (last 30 entries) | ✅ (unlimited) |
| Advanced stats (SD, PP, MAP, Trend) | ❌ | ✅ |
| Export data (CSV/PDF) | ❌ | ✅ |
| Full history | ❌ (last 30 entries) | ✅ (unlimited) |

### How to Upgrade

1. Type `/upgrade`
2. Select a plan:
   - Monthly: 9 THB
   - 12 Months: 99 THB
3. The Bot will display **bank account details** for transfer.
4. Transfer the specified amount.
5. **Send the transfer slip image** to the Bot.
6. The system will automatically verify the slip.
7. Upgrade successful → Premium features are instantly available.

### Check Subscription Status

Type `/subscription` to see your current status:

```text
💎 Premium Member
Valid until: 15/04/2026
Remaining: 31 days
```

---

## 7. All Commands

| Command | Usage |
|---------|-------|
| `/start` | Start / Sign up / Connect account |
| `/bp` | Open Mini App to record blood pressure |
| `/stats` | View blood pressure statistics and charts |
| `/profile` | View and edit personal information |
| `/edit` | Edit the most recent blood pressure entries |
| `/delete` | Delete a blood pressure entry |
| `/settings` | Set language and timezone |
| `/password` | Change password |
| `/upgrade` | Upgrade to Premium |
| `/subscription` | Check subscription status |
| `/help` | Show all commands |
| `/cancel` | Cancel current operation |
| `/deactivate` | Delete user account (Warning!) |
| `/broadcast` | **[Admin Only]** Send announcement to all users |
| **Send Photo** | AI extracts blood pressure values from monitor photo |

---

## 8. FAQ

### What if I send a photo and the Bot extracts the wrong values?
Press "✏️ Edit" and type the correct values manually, e.g. `120 80 72`.

### What if I send a photo and the Bot can't extract any values at all?
- Try taking a clearer photo with no shadows blocking the numbers.
- Take the photo straight on, not too tilted.
- If it still fails, press "✏️ Edit" and type the numbers manually.

### What does "Duplicate Record" mean?
It means you have already saved the exact same entry (Date + Time + SYS/DIA/Pulse). The system will not save duplicates.

### I forgot my password, what should I do?
Currently, there is no password reset feature via the Bot. Please use the "Forgot Password" function on the website.

### How many people can use the Bot on one device?
1 Telegram account can be linked to 1 user account. You cannot link multiple accounts simultaneously.

### Is my blood pressure data secure?
Personal data (Name, Phone number, Citizen ID) is encrypted (Fernet Encryption) before being stored in the database. Even the system administrator cannot read this data without the encryption key.

### Can I change the timezone later?
Yes, you can change your timezone at any time using the `/settings` command.

### How do I cancel Premium?
Premium will automatically expire based on the purchased duration. There is no auto-renewal. When it expires, your account will automatically downgrade to Free (data is not lost, but you will only be able to view the last 30 entries).
