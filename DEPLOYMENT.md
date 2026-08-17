# SecureRotate AI — Production Deployment Guide 🚀

This document provides step-by-step instructions for deploying **SecureRotate AI** to production cloud platforms (**No Docker Required!**).

---

## 🌟 Method 1: Render.com (Recommended — 100% Free & Automatic, No Docker Needed)

Render can automatically build and host Python applications directly from your GitHub repository using standard Python!

### Step 1: Push Project Code to GitHub
Ensure all repository files (including `backend/requirements.txt`, `Procfile`, and `render.yaml`) are committed to GitHub.

### Step 2: Deploy on Render
1. Go to **[Render.com Dashboard](https://dashboard.render.com)**.
2. Click **New +** ➔ **Blueprint** (or **Web Service**).
3. Select your GitHub repository.
4. Render automatically reads `render.yaml` and sets up:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
5. Fill in your MySQL Database Environment Variables:
   - `MYSQL_SERVER`: *(Your cloud MySQL host e.g. Aiven / PlanetScale / AWS RDS)*
   - `MYSQL_USER`: *(Your MySQL username)*
   - `MYSQL_PASSWORD`: *(Your MySQL password)*
6. Click **Apply**.

Render will deploy your live website with a secure HTTPS URL: `https://securerotate-ai.onrender.com`.

---

## 🚂 Method 2: Railway.app (Automatic Git Deployment — No Docker Needed)

1. Go to **[Railway.app](https://railway.app)** ➔ Click **New Project** ➔ **Deploy from GitHub repo**.
2. Select your `CTS_NPN` repository.
3. Railway automatically detects Python and uses `Procfile`:
   `python -m uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
4. Add a free **MySQL Service** on Railway to connect `securerotate_db` and `target_demo_db`.
5. Set environment variables in Railway Variables tab (`JWT_SECRET_KEY`, `VAULT_ENCRYPTION_KEY`, `MYSQL_SERVER`, etc.).
6. Railway will generate a live URL: `https://<your-app>.up.railway.app`.

---

## 💻 Method 3: Cloud Linux VPS Deployment (DigitalOcean / EC2 / Linode)

If deploying to a virtual machine server without Docker:

```bash
# 1. Install Python on Linux server
sudo apt update && sudo apt install python3-pip python3-venv mysql-server -y

# 2. Clone repository & install dependencies
git clone https://github.com/your-username/CTS_NPN.git
cd CTS_NPN/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Start web server using Gunicorn / Uvicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000
```

---

## 📋 Required Production Environment Variables Checklist

Ensure these variables are configured in your cloud environment:

| Variable Name | Value / Purpose |
| :--- | :--- |
| `APP_ENV` | `production` |
| `DEBUG` | `False` |
| `MYSQL_SERVER` | Your production MySQL database host |
| `MYSQL_PORT` | `3306` |
| `MYSQL_USER` | MySQL admin username |
| `MYSQL_PASSWORD` | MySQL admin password |
| `SYSTEM_DB_NAME` | `securerotate_db` |
| `TARGET_DEMO_DB_NAME` | `target_demo_db` |
| `JWT_SECRET_KEY` | Secret 32+ byte string for signing JWT tokens |
| `JWT_ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` |
| `VAULT_ENCRYPTION_KEY` | Fernet key for credential password encryption |
| `SECRET_PROVIDER_TYPE` | `LOCAL` |
