# SecureRotate AI 🛡️🔄

> **AI-Powered Database Credential Lifecycle Management & Automated Zero-Downtime Rotation System**

SecureRotate AI is an enterprise-grade credential lifecycle management platform designed for database environments. It automatically identifies database credentials approaching password expiry, calculates AI risk scores, runs downstream dependency impact analysis, alerts stakeholders 7 days before expiry, enforces multi-role approvals (RBAC), performs secure automated password rotation on MySQL databases, verifies post-rotation database connectivity using transactional queries (`SELECT 1`), automatically rolls back on failure, and maintains an append-only audit trail.

---

## 🎯 1. Problem Statement & End-to-End Workflow

In modern database environments, database credentials (passwords, connection strings, service account keys) suffer from:
1. **Untracked Password Expirations:** Unexpected service outages caused by expired passwords.
2. **High Breach & Stale Credential Risk:** Infrequently rotated high-privilege credentials.
3. **Manual & Error-Prone Rotations:** Human errors during password updates causing downstream microservice failures.
4. **Lack of Dependency Visibility:** Rotating a credential without knowing which API services or background jobs rely on it.
5. **Missing Compliance & Auditability:** Inability to provide zero-trust audit trails for regulatory compliance.

### The End-to-End Lifecycle Workflow
```
Discover/Register ➔ Monitor Expiry ➔ Predict Risk ➔ Explain Risk ➔ Analyze Dependencies
         ➔ Notify Stakeholders ➔ Request Approval ➔ Rotate Credential
         ➔ Verify Connection ➔ Rollback on Failure ➔ Audit Everything
```

---

## 🏗️ 2. System Architecture & Component Design

```
                               ┌──────────────────────────────────────────────┐
                               │             FastAPI Backend (Py3.11)         │
                               │  - JWT Bearer Authentication                 │
                               │  - RBAC Middleware (Admin/DevOps/Auditor)    │
                               │  - Embedded React SPA Server                 │
                               └──────────────────────┬───────────────────────┘
                                                      │
              ┌───────────────────────────────────────┼───────────────────────────────────────┐
              ▼                                       ▼                                       ▼
   ┌──────────────────────┐                ┌──────────────────────┐                ┌──────────────────────┐
   │ Credential & Risk    │                │ Dependency Engine    │                │ Rotation & Rollback  │
   │ - ML Risk Classifier │                │ - Downstream Impact  │                │ - Secrets Module Pwd │
   │ - Expiry Scheduler   │                │ - Criticality Score  │                │ - MySQL ALTER USER   │
   │ - Fernet Vault       │                │                      │                │ - SELECT 1 Verifier  │
   └──────────┬───────────┘                └──────────┬───────────┘                └──────────┬───────────┘
              │                                       │                                       │
              └───────────────────────────────────────┼───────────────────────────────────────┘
                                                      │
                                                      ▼
                                       ┌──────────────────────────────┐
                                       │     MySQL 8.0 Engine         │
                                       │ - securerotate_db (Metadata) │
                                       │ - target_demo_db (Target)    │
                                       └──────────────────────────────┘
```

---

## 🔐 3. Authentication & Role-Based Access Control (RBAC)

SecureRotate AI implements real user authentication with **Argon2id password hashing** (`pwdlib`) and **JWT access tokens** (`PyJWT`). Plaintext passwords are never stored.

### Seeded Demo Accounts

| Username / Email | Role | Default Password | Access Level |
| :--- | :--- | :--- | :--- |
| `admin@securerotate.local` (`admin`) | **ADMIN** | `Admin123!` | Full system access + User Management (`/users`) |
| `devops@securerotate.local` (`devops`) | **DEVOPS** | `Devops123!` | Credential CRUD, Risk, Rotation Execution |
| `auditor@securerotate.local` (`auditor`) | **AUDITOR** | `Auditor123!` | Read-only security & audit view |

### RBAC Permission Matrix

| Endpoint / Feature | ADMIN | DEVOPS | AUDITOR |
| :--- | :---: | :---: | :---: |
| **Dashboard / Health Check** | ✅ | ✅ | ✅ |
| **View Credentials & Risk** | ✅ | ✅ | ✅ |
| **Create / Update Credentials** | ✅ | ✅ | ❌ (HTTP 403) |
| **Delete Credentials** | ✅ | ❌ (HTTP 403) | ❌ (HTTP 403) |
| **Request Credential Rotation** | ✅ | ✅ | ❌ (HTTP 403) |
| **Approve / Reject Rotation** | ✅ | ❌ (HTTP 403) | ❌ (HTTP 403) |
| **Execute Rotation & Rollback** | ✅ | ✅ | ❌ (HTTP 403) |
| **View Audit Trail & Logs** | ✅ | ✅ | ✅ |
| **User Management (`/users`)** | ✅ | ❌ (HTTP 403) | ❌ (HTTP 403) |

---

## ⚡ 4. Quick Start / Local Setup Guide

### Step 1: Database Setup (MySQL 8.0)
Connect to your local MySQL server (`localhost:3306`) as root and create the application and target databases:
```sql
CREATE DATABASE securerotate_db;
CREATE DATABASE target_demo_db;

CREATE USER 'demo_user'@'localhost' IDENTIFIED BY 'DemoPass123!';
GRANT ALL PRIVILEGES ON target_demo_db.* TO 'demo_user'@'localhost';
FLUSH PRIVILEGES;
```

---

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env` in the project root:
```powershell
copy .env.example .env
```
*(Ensure `MYSQL_PASSWORD` in `.env` matches your local MySQL root password)*

---

### Step 3: Run the FastAPI Application
Open PowerShell in the project root directory:
```powershell
# 1. Activate Python virtual environment
& "$env:USERPROFILE\venvs\securerotate\Scripts\Activate.ps1"

# 2. Navigate to backend directory
cd backend

# 3. Start Uvicorn server
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

### Step 4: Open Application UI
Open your browser at:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📡 5. API Documentation Summary

| Endpoint | Method | Role Required | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/health` | `GET` | Public | System and database health status |
| `/api/v1/auth/login` | `POST` | Public | Authenticates user (username/email), returns JWT token |
| `/api/v1/auth/me` | `GET` | Authenticated | Retrieves current authenticated user profile |
| `/api/v1/credentials` | `GET` / `POST` | Authenticated / DevOps+ | Lists or creates database credentials |
| `/api/v1/credentials/seed-demo-data` | `POST` | Admin / DevOps | Resets & seeds 24 enterprise demo databases |
| `/api/v1/risk/overview` | `GET` | Authenticated | Fetches ML risk summary & distribution |
| `/api/v1/credentials/{id}/impact` | `GET` | Authenticated | Downstream service impact analysis |
| `/api/v1/rotation-requests` | `POST` | DevOps+ | Submits a credential rotation request |
| `/api/v1/approvals/{id}/approve` | `POST` | Admin | Approves pending rotation request |
| `/api/v1/rotation/{id}` | `POST` | DevOps+ | Executes target database rotation & verification |
| `/api/v1/audit-logs` | `GET` | Authenticated | Fetches append-only audit trail logs |
| `/api/v1/users` | `GET` / `POST` | Admin | Lists or creates system user accounts |

---

## 🎬 6. 13-Step Live Hackathon Presentation Script

1. **Sign In**: Navigate to `http://localhost:8000` and click the **Admin** demo pill (`admin@securerotate.local`).
2. **Dashboard Overview**: View the summary of **24 Managed DB Credentials** (18 Healthy, 3 Warning, 2 Critical, 1 Expired).
3. **Review Alert**: Click **Review & Rotate** on the Critical Warning banner for **Payment Production DB**.
4. **AI Risk Engine**: Review the **94% CRITICAL** risk score and explainable risk factors (Production environment, high privilege, 7 dependent services, expiring in 2 days).
5. **Dependency Impact**: View the **Dependency Graph** mapping blast radius across connected microservices (Payment API, Invoice Worker, etc.).
6. **Notifications**: Inspect the **Notification Center** demonstrating automated 7-day stakeholder alerts.
7. **Submit Request**: Click **1. Submit Rotation Request** (Status updates to `PENDING`).
8. **Approve Request**: Click **2. Approve Rotation** (Admin sign-off - Status updates to `APPROVED`).
9. **Execute Rotation**: Click **3. Execute Rotation**.
10. **Real-Time Verification**: Observe sequential execution: Secure password generation via `secrets` module ➔ Target MySQL `ALTER USER` ➔ Fernet vault key update ➔ `SELECT 1` post-rotation query check.
11. **Completion**: Observe the **✅ Rotation Successful** indicator and updated expiration date.
12. **Audit Trail**: Open **Audit Logs** to inspect append-only security logs: `ROTATION_REQUESTED`, `ROTATION_APPROVED`, `ROTATION_STARTED`, `VERIFICATION_PASSED`, `ROTATION_SUCCESS`.
13. **Rollback Demonstration**: Execute a controlled failure to demonstrate automated target database restoration, logging `VERIFICATION_FAILED` and `ROLLBACK_EXECUTED`.

---

## 🛡️ 7. Security & Best Practices

- **Zero Password Exposure**: Raw database passwords are encrypted via `LocalSecretProvider` (Fernet authenticated encryption) and are **never** returned in API responses, displayed in the UI, or logged in audit details.
- **Append-Only Audit Logs**: Operations are recorded in `audit_logs` table without recording JWT tokens, secrets, or sensitive headers.
- **Environment Isolation**: Production secrets and database connections are driven entirely by environment variables (`.env`).
