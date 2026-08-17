# SecureRotate AI — Beginner Windows Local Setup Guide 🪟

This guide provides step-by-step instructions for setting up and running **SecureRotate AI** directly on a Windows developer machine **without Docker**.

---

## 📋 Prerequisites

Before starting, ensure the following software is installed on your Windows machine:

1. **Python 3.11 or 3.12:** [Download Python for Windows](https://www.python.org/downloads/)
   - *Important:* Check the box **"Add python.exe to PATH"** during installation!
2. **Node.js (v18 or v20 LTS):** [Download Node.js](https://nodejs.org/)
3. **MySQL Community Server (v8.0+):** [Download MySQL Community Installer](https://dev.mysql.com/downloads/installer/)
   - Remember the password you set for the default `root` user.
   - Default port is `3306`.
4. **MySQL Workbench:** Included in the MySQL Installer or downloadable separately.

---

## 🗄️ Step 1: Set Up Local MySQL Databases

SecureRotate AI uses **one local MySQL server** with **two databases**:
1. `securerotate_db` — Stores application metadata, risk scores, users, and audit logs.
2. `target_demo_db` — Acts as the demo target database to test password rotations safely.

### Using MySQL Workbench (GUI) / MySQL Client
1. Install MySQL Community Server.
2. Install MySQL Workbench if needed.
3. Start the MySQL service (via `services.msc` or MySQL Installer).
4. Open **MySQL Workbench**.
5. Connect to `localhost:3306` using your `root` account.
6. Create system database:
   ```sql
   CREATE DATABASE securerotate_db;
   ```
7. Create target demo database:
   ```sql
   CREATE DATABASE target_demo_db;
   ```
8. Create demo user:
   ```sql
   CREATE USER 'demo_user'@'localhost' IDENTIFIED BY 'CHANGE_ME';
   ```
9. Grant appropriate privileges to demo_user for target_demo_db:
   ```sql
   GRANT ALL PRIVILEGES ON target_demo_db.* TO 'demo_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

---

## 🐍 Step 2: Set Up Backend (Python FastAPI)

1. Open PowerShell or Command Prompt and navigate to the project directory:
   ```cmd
   cd c:\Users\PC\OneDrive\Desktop\CTS_NPN
   ```

2. Copy `.env.example` to create your local `.env` file:
   ```cmd
   copy .env.example .env
   ```

3. Navigate to the `backend` folder:
   ```cmd
   cd backend
   ```

4. Create a Python virtual environment:
   ```cmd
   python -m venv venv
   ```

5. Activate the virtual environment:
   - On PowerShell:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - On Command Prompt (cmd):
     ```cmd
     venv\Scripts\activate.bat
     ```

6. Install all backend dependencies:
   ```cmd
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

7. Start the FastAPI backend server:
   ```cmd
   uvicorn app.main:app --reload --port 8000
   ```
   - Your backend is now running at `http://127.0.0.1:8000`
   - Interactive Swagger API docs: `http://127.0.0.1:8000/docs`

---

## ⚛️ Step 3: Set Up Frontend (React + Vite)

1. Open a **NEW** PowerShell or Command Prompt window.
2. Navigate to the `frontend` folder:
   ```cmd
   cd c:\Users\PC\OneDrive\Desktop\CTS_NPN\frontend
   ```

3. Install frontend dependencies:
   ```cmd
   npm install
   ```

4. Start the React development server:
   ```cmd
   npm run dev
   ```
   - Your frontend application is now running at `http://localhost:5173`

---

## 🛠️ Step 4: Verification Check

To verify your local setup:
- **Frontend Dashboard:** Open `http://localhost:5173` in your browser.
- **Backend API Docs:** Open `http://127.0.0.1:8000/docs`.
- **Database Connection:** Backend will automatically create required tables in `securerotate_db` on startup.

---

## ❓ Troubleshooting Common Issues

- **Execution Policy Error in PowerShell:**
  If PowerShell blocks activating the virtual environment (`...cannot be loaded because running scripts is disabled`), run:
  ```powershell
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
- **MySQL Connection Refused:**
  Ensure the MySQL Windows Service is running. Open `services.msc`, locate `MySQL80` (or `MySQL`), and ensure Status is **Running**.
- **Port 8000 or 5173 already in use:**
  Close any other running Python/Node processes or change the port in `.env` and `vite.config.js`.
