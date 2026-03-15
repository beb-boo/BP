# BP Project - Updated Deployment Plan
## ปรับปรุงล่าสุด: เลือก Stack แล้ว + แผนย้าย Repo

> **ใช้คู่กับ**: `plan/BP_Improvement_Plan.md` (แผนแก้ code)
> **ใช้คู่กับ**: `plan/BP_Assessment.md` (ผลสำรวจ)

---

## 1. Stack ที่ตัดสินใจแล้ว

```
┌──────────────────────────────────────────────────┐
│              Final Architecture                   │
├──────────────┬───────────────────────────────────┤
│ Frontend     │ Vercel (Next.js)                  │
│ Backend API  │ Vercel Serverless (FastAPI/Python) │
│ Telegram Bot │ Webhook mode (ผ่าน Backend)        │
│ Database     │ Neon PostgreSQL (free 0.5 GB)     │
│ Redis        │ Upstash Redis (free 10K cmd/day)  │
└──────────────┴───────────────────────────────────┘
```

### Redis: Upstash Redis ผ่าน Vercel Marketplace

Vercel ไม่มี Redis ในตัว (Vercel KV ยกเลิกแล้ว) แต่ Upstash Redis
integrate กับ Vercel ได้ง่ายผ่าน Marketplace

**วิธี setup**:
1. ไปที่ https://vercel.com/marketplace/upstash
2. เชื่อม Vercel project กับ Upstash
3. Upstash จะสร้าง Redis instance ให้
4. Environment variables (`UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`) จะถูกเพิ่มใน Vercel project อัตโนมัติ

**สำหรับ code ของเรา**: ใช้ `REDIS_URL` (standard redis:// protocol) ไม่ใช่ REST API
ตั้งค่าใน Vercel ENV: `REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379`
(ดูค่าจริงใน Upstash Console > Redis > Details > Connection String)

### Database: Neon PostgreSQL

**วิธี setup**:
1. สมัครที่ https://neon.tech
2. สร้าง project + database
3. Copy connection string
4. ตั้ง `DATABASE_URL=postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/bp_db?sslmode=require`

### Telegram Bot: Webhook Mode

Bot จะรัน**ภายใน Backend** เป็น FastAPI endpoint `/bot/webhook`
Telegram จะส่ง HTTP POST มาที่ endpoint นี้เมื่อมี message ใหม่

ไม่ต้อง deploy Bot แยก ไม่ต้องมี long-running process

---

## 2. แผนย้าย Git Repository

### สถานะปัจจุบัน

| Repo | URL | สถานะ |
|------|-----|-------|
| Original | `https://github.com/beb-boo/BP.git` | ใช้อยู่ (origin) |
| Fork | `https://github.com/kaebmoo/BP.git` | Fork มาแล้ว ยังไม่ใช้ |

### เป้าหมาย

- ระหว่าง dev/fix: push ไปที่ `beb-boo/BP` ตามปกติ
- ก่อนขึ้น Vercel: เปลี่ยน origin เป็น `kaebmoo/BP`
- Deploy Vercel จาก `kaebmoo/BP`

### คำสั่ง Claude Code สำหรับย้าย Remote

เมื่อพร้อมจะย้าย (หลังแก้ code เสร็จ ก่อน deploy Vercel):

```bash
cd /Users/seal/Documents/GitHub/BP

# ดู remotes ปัจจุบัน
git remote -v

# เปลี่ยนชื่อ origin เดิมเป็น beb-boo (เก็บไว้อ้างอิง)
git remote rename origin beb-boo

# เพิ่ม kaebmoo เป็น origin ใหม่
git remote add origin https://github.com/kaebmoo/BP.git

# ตรวจสอบ
git remote -v
# ควรเห็น:
#   beb-boo   https://github.com/beb-boo/BP.git (fetch/push)
#   origin    https://github.com/kaebmoo/BP.git (fetch/push)

# Sync fork ให้ตรงกับ beb-boo ก่อน (ถ้า fork เก่ากว่า)
git fetch beb-boo
git checkout main
git merge beb-boo/main

# Push ไปที่ kaebmoo (origin ใหม่)
git push -u origin main

# ถ้า kaebmoo/BP มี history ต่างจาก beb-boo (เพราะ fork มาตอนที่ยังไม่ได้ filter-repo)
# อาจต้อง force push:
git push --force -u origin main
```

### ระหว่างนี้ (ก่อนย้าย)

ยัง push ไป `beb-boo/BP` ตามปกติ เมื่อแก้ code เสร็จแล้วค่อยทำขั้นตอนข้างบน

### หลังย้ายแล้ว

ถ้าไม่ต้องการ push ไป beb-boo อีก:
```bash
git remote remove beb-boo
```

หรือเก็บไว้ก็ได้ ไม่เกะกะ push ปกติจะไป origin (kaebmoo) เท่านั้น

---

## 3. ก่อน Push ขึ้น GitHub - Security Checklist

### 3.1 ตรวจ Secrets ใน Git History

```bash
cd /Users/seal/Documents/GitHub/BP

# ตรวจว่า app/.env เคยถูก commit หรือไม่
git log --all --full-history -- "app/.env"
git log --all --full-history -- "app/.env.bak"

# ตรวจ bp_data/ (ข้อมูลผู้ป่วย)
git log --all --full-history -- "bp_data/"
```

ถ้าเจอ commit → ต้อง clean ด้วย `git filter-repo` ก่อน push

### 3.2 อัพเดต .gitignore

เพิ่มในไฟล์ `.gitignore`:

```gitignore
# === Sensitive Data ===
bp_data/
app/*.db

# === Environment ===
.venv/
venv/
.pytest_cache/

# === IDE / Tools ===
.vscode/
.claude/
.idea/

# === Logs & Temp ===
bp_prompt_log.txt
logs/

# === Images (case-insensitive) ===
*.jpg
*.jpeg
*.png
```

### 3.3 ลบไฟล์ที่ไม่ควรอยู่ออกจาก Git Tracking

```bash
git rm --cached -r bp_data/ 2>/dev/null
git rm --cached -r .venv/ 2>/dev/null
git rm --cached -r .pytest_cache/ 2>/dev/null
git rm --cached -r .claude/ 2>/dev/null
git rm --cached -r .vscode/ 2>/dev/null
git rm --cached bp_prompt_log.txt 2>/dev/null
git commit -m "Remove sensitive/unnecessary files from tracking"
```

### 3.4 ตรวจว่า Repo เป็น Private

ทั้ง `beb-boo/BP` และ `kaebmoo/BP` ต้องเป็น **Private** repo
(GitHub Settings → Danger Zone → Change visibility)

---

## 4. Vercel Deployment Steps

### Step 1: Deploy Frontend ก่อน (ง่ายที่สุด)

1. ไปที่ vercel.com → Import Git Repository → เลือก `kaebmoo/BP`
2. ตั้ง Root Directory: `frontend`
3. Framework Preset: Next.js (auto-detect)
4. ตั้ง Environment Variables:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.vercel.app/api/v1
   NEXT_PUBLIC_API_KEY=<your-api-key>
   ```
5. Deploy

### Step 2: Deploy Backend

1. สร้างอีก Vercel project จาก repo เดียวกัน
2. Root Directory: `.` (root)
3. ต้องมี `vercel.json` ที่ root:
   ```json
   {
     "builds": [
       { "src": "app/main.py", "use": "@vercel/python" }
     ],
     "routes": [
       { "src": "/(.*)", "dest": "app/main.py" }
     ]
   }
   ```
4. ตั้ง Environment Variables ทั้งหมด:
   ```
   DATABASE_URL=postgresql://...@neon.tech/bp_db?sslmode=require
   REDIS_URL=rediss://default:xxx@xxx.upstash.io:6379
   SECRET_KEY=<new-strong-random-key>
   ENCRYPTION_KEY=<new-fernet-key>
   API_KEYS=<your-custom-api-keys>
   GOOGLE_AI_API_KEY=<gemini-key>
   TELEGRAM_BOT_TOKEN=<bot-token>
   TELEGRAM_BOT_USERNAME=<bot-username>
   BOT_MODE=webhook
   WEBHOOK_URL=https://your-backend.vercel.app
   WEBHOOK_SECRET=<random-secret>
   APP_TIMEZONE=Asia/Bangkok
   AUTO_CREATE_TABLES=true
   ALLOWED_ORIGINS=https://your-frontend.vercel.app
   BYPASS_OTP=false
   ```

### Step 3: Setup Telegram Webhook

หลัง Backend deploy เสร็จ เรียกครั้งเดียว:
```
GET https://your-backend.vercel.app/bot/set-webhook?secret=<WEBHOOK_SECRET>
```

### Step 4: Setup Neon Database

1. สมัคร neon.tech → สร้าง project
2. Copy connection string → ใส่ใน `DATABASE_URL`
3. Deploy แรก ตั้ง `AUTO_CREATE_TABLES=true` เพื่อสร้าง tables
4. หลังจากนั้น เปลี่ยนเป็น `AUTO_CREATE_TABLES=false`

### Step 5: Setup Upstash Redis

1. ไป vercel.com/marketplace/upstash → เชื่อมกับ Backend project
2. หรือสมัครตรงที่ upstash.com → สร้าง Redis database
3. Copy connection string → ใส่ใน `REDIS_URL`

---

## 5. ลำดับการทำงาน (Updated)

```
Phase 0: Security & Git Cleanup
├── ตรวจ git history สำหรับ secrets
├── อัพเดต .gitignore
├── ลบไฟล์ที่ไม่ควรอยู่ออกจาก tracking
├── ตรวจว่า repo เป็น Private
└── Push ไป beb-boo/BP

Phase 1: Bug Fixes (ตาม BP_Improvement_Plan.md)
├── แก้ bugs 1.1 - 1.9
└── Push ไป beb-boo/BP

Phase 2: Dual-Mode Storage (ตาม BP_Improvement_Plan.md)
├── OTP Service → Memory + Redis
├── Rate Limiter → Centralize + Redis
├── Database → Pool settings for PostgreSQL
└── Push ไป beb-boo/BP

Phase 3: Telegram Bot Webhook (ตาม BP_Improvement_Plan.md)
├── Refactor build_application()
├── สร้าง webhook.py
├── แก้ main.py เพิ่ม webhook router
└── Push ไป beb-boo/BP

Phase 4: Frontend Improvements (ตาม BP_Improvement_Plan.md)
├── DoctorView fetch real data
├── Patient manage doctors
├── Auth middleware
└── Push ไป beb-boo/BP

Phase 5: Deployment Config (ตาม BP_Improvement_Plan.md)
├── สร้าง vercel.json
├── อัพเดต .env.example
├── อัพเดต CLAUDE.md
└── Push ไป beb-boo/BP

Phase 6: ย้าย Repo + Deploy
├── ย้าย origin จาก beb-boo → kaebmoo
├── Push ไป kaebmoo/BP
├── สร้าง Neon PostgreSQL
├── สร้าง Upstash Redis
├── Deploy Frontend บน Vercel
├── Deploy Backend บน Vercel
├── Setup Telegram Webhook
└── ทดสอบทุก flow
```

---

## 6. คำสั่ง Claude Code

ให้ Claude Code ทำตาม Phase 0-5 ใน `plan/BP_Improvement_Plan.md`
โดยเพิ่ม Phase 0 (Security) จากไฟล์นี้เป็นขั้นตอนแรก

Phase 6 (ย้าย Repo + Deploy) ทำเองหลังจาก code พร้อม

---

*Updated: 2026-03-15*
