# SecureRotate AI — Technical Architecture Blueprint 🏗️

*Simplified Local Development Architecture (No Docker Required)*

This document details the software architecture, database design, ML risk modeling, secret vault abstraction, API blueprint, and security workflows for **SecureRotate AI**.

---

## 1. Local System Architecture

The local development setup runs natively on the developer machine across standard ports. It utilizes **one local MySQL server** (default port `3306`) running **two isolated databases**:
- `securerotate_db`: System metadata, secret reference tokens, risk metrics, RBAC users, and audit logs.
- `target_demo_db`: Target database instance used for practicing zero-downtime password rotation and post-rotation connection verification.

```
+------------------------------------------------------------------------------------+
|                                 Developer Machine                                  |
|                                                                                    |
|  +------------------------+                        +----------------------------+  |
|  |   React + Vite UI      | --- REST/WebSockets--> |    FastAPI Backend App     |  |
|  |  http://localhost:5173 |                        |   http://127.0.0.1:8000    |  |
|  +------------------------+                        +--------------+-------------+  |
|                                                                   |                |
|                                            +----------------------+                |
|                                            |                                       |
|                                            v                                       |
|   +----------------------------------------------------------------------------+   |
|   |                  FastAPI Embedded Business Engines                         |   |
|   |  +--------------------+  +----------------------+  +--------------------+  |   |
|   |  | APScheduler Engine |  | LocalSecretProvider  |  | scikit-learn Model |  |   |
|   |  | (Cron Expiry Scan) |  | (Fernet Auth Encrypt)|  | (ML Risk Predictor)|  |   |
|   |  +--------------------+  +----------------------+  +--------------------+  |   |
|   |  +--------------------+  +----------------------+  +--------------------+  |   |
|   |  | Expiry & Alert Svc |  | Dependency Analyzer  |  | Connection Verifier|  |   |
|   |  +--------------------+  +----------------------+  +--------------------+  |   |
|   +---------------------------------------+------------------------------------+   |
|                                           |                                        |
|                                           v                                        |
|   +----------------------------------------------------------------------------+   |
|   |                    Local MySQL Server (localhost:3306)                     |   |
|   |                                                                            |   |
|   |   +-----------------------------------+  +------------------------------+  |   |
|   |   |        securerotate_db            |  |       target_demo_db         |  |   |
|   |   | (Primary Metadata & Audit Trail)  |  | (Demo Rotation Sandbox Target)|  |   |
|   |   +-----------------------------------+  +------------------------------+  |   |
|   +----------------------------------------------------------------------------+   |
+------------------------------------------------------------------------------------+
```

---

## 2. Extensible Secret Vault Architecture (`LocalSecretProvider`)

To keep local setup easy for beginner teams while maintaining enterprise security best practices:

1. **Abstract Base Class (`BaseSecretProvider`):** Defines mandatory methods (`encrypt_secret`, `decrypt_secret`, `generate_secure_password`).
2. **`LocalSecretProvider` (Default for Dev):** Keeps `LocalSecretProvider` responsible for securely storing/retrieving the actual credential secret using Fernet authenticated encryption. Raw passwords are NEVER stored in plaintext in the database, disk, or logs.
3. **`VaultSecretProvider` (Future Enterprise Extension):** Stub class providing a seamless upgrade path to HashiCorp Vault or AWS Secrets Manager without refactoring core API routes.

```
                 +--------------------------+
                 |    BaseSecretProvider    |  (Abstract Base Class)
                 +------------+-------------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
+--------------------------+    +---------------------------+
|   LocalSecretProvider    |    |    VaultSecretProvider    |
|  (Fernet Authenticated   |    | (Future Enterprise Vault /|
|  Encryption Vault Dev)   |    |   AWS Secrets Manager)    |
+--------------------------+    +---------------------------+
```

---

## 3. Core Component Workflows (All Preserved)

### 3.1 Credential Expiry Monitoring & 7-Day Notifications
- **APScheduler** runs inside the FastAPI backend process as an async background scheduler.
- Executes daily scans against `credentials` in `securerotate_db`.
- Calculates `days_until_expiry`. If $\le 7$ days, triggers `NotificationService` to send console/email alerts to assigned stakeholder contacts.

### 3.2 AI Risk Prediction Model (`scikit-learn`)
- Evaluates credential feature vectors:
  - `days_until_expiry` (Numeric)
  - `credential_age_days` (Numeric)
  - `dependency_count` (Numeric - number of connected microservices/jobs)
  - `privilege_level` (Categorical: `SUPERUSER`, `READ_WRITE`, `READ_ONLY`)
  - `access_frequency_per_day` (Numeric)
- Output: Risk score $[0.0, 1.0]$ categorized as `LOW`, `MEDIUM`, or `HIGH`.

### 3.3 Recommendation Engine & Approval Workflow
- **Low Risk ($\le 0.39$):** Recommendation is AUTO_APPROVE during standard off-peak maintenance windows.
- **Medium / High Risk ($\ge 0.40$):** Creates a pending approval entry in `rotation_approvals`. Requires manual sign-off by a user with `DEVOPS` or `ADMIN` RBAC role.

### 3.4 Dependency Impact Analysis Engine
- Maintains a directed graph of application dependencies connected to each database user.
- Computes "blast radius" (affected microservices, API background workers, reporting dashboards) to inform DevOps prior to approving rotation.

### 3.5 Password Rotation & Post-Rotation Connection Verification
1. `RotationEngine` generates a 32-character high-entropy secure password.
2. Connects to `target_demo_db` on local MySQL server and alters the user password using safe MySQL driver/database APIs (never constructing SQL queries by string concatenating the password).
3. Encrypts the new password using `LocalSecretProvider` (which securely stores/retrieves the credential secret) and updates `securerotate_db` with the resulting `secret_reference`.
4. **`ConnectionVerifier` Handshake:**
   - Opens a test connection to `target_demo_db` using `demo_user` and the NEW password.
   - Runs `SELECT 1;` health query.
   - If verification fails, automatically triggers emergency rollback restoring the previous password.
5. **Audit Trail:** Appends an immutable record to `audit_logs` table with action status (`SUCCESS` or `ROLLED_BACK`).

### 3.6 Strict Password Security & Zero-Leakage Policy
Generated passwords are strictly confidential and MUST NEVER BE:
- **Logged** (to stdout, stderr, or log files).
- **Returned through APIs** (API response DTOs and Pydantic schemas omit raw secret fields).
- **Displayed in React** (UI components show masked labels or status indicators only).
- **Stored in `audit_logs`** (only action status, credential ID, timestamp, latency, and success/failure flags are logged).
- **Included in error messages** (exception handlers catch and sanitize all database/network error messages before emitting responses).

---

## 4. Database Schema Specifications (`securerotate_db`)

```sql
-- Users and Roles for RBAC
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'VIEWER', -- ADMIN, DEVOPS, AUDITOR, VIEWER
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Monitored Credentials Table
CREATE TABLE credentials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    db_type VARCHAR(50) NOT NULL DEFAULT 'MYSQL',
    host VARCHAR(255) NOT NULL DEFAULT 'localhost',
    port INTEGER NOT NULL DEFAULT 3306,
    database_name VARCHAR(255) NOT NULL, -- e.g. target_demo_db
    username VARCHAR(255) NOT NULL,      -- e.g. demo_user
    secret_reference TEXT NOT NULL,     -- Fernet authenticated encryption ciphertext reference
    environment VARCHAR(50) NOT NULL DEFAULT 'DEVELOPMENT',
    privilege_level VARCHAR(50) NOT NULL DEFAULT 'READ_WRITE',
    last_rotated_at TIMESTAMP NULL,
    expires_at TIMESTAMP NOT NULL,
    rotation_interval_days INTEGER NOT NULL DEFAULT 90,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Service Dependencies
CREATE TABLE dependencies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    credential_id INTEGER REFERENCES credentials(id) ON DELETE CASCADE,
    service_name VARCHAR(255) NOT NULL,
    service_type VARCHAR(50) NOT NULL, -- MICROSERVICE, WORKER, ETL, DASHBOARD
    owner_email VARCHAR(255) NOT NULL,
    is_critical BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Rotation Approvals
CREATE TABLE rotation_approvals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    credential_id INTEGER REFERENCES credentials(id) ON DELETE CASCADE,
    requested_by_id INTEGER REFERENCES users(id),
    approved_by_id INTEGER REFERENCES users(id),
    risk_score FLOAT NOT NULL,
    risk_level VARCHAR(50) NOT NULL, -- LOW, MEDIUM, HIGH
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL
);

-- Audit Trail
CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    credential_id INTEGER REFERENCES credentials(id) ON DELETE SET NULL,
    action_type VARCHAR(100) NOT NULL, -- EXPIRY_SCAN, RISK_EVALUATED, NOTIFICATION_SENT, ROTATION_SUCCESS, ROTATION_FAILED, ROLLBACK_EXECUTED
    performed_by VARCHAR(255) NOT NULL DEFAULT 'SYSTEM_SCHEDULER',
    status VARCHAR(50) NOT NULL,
    details JSON,
    verification_latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. Summary of Beginner Local Setup Ports

- **React Frontend:** `http://localhost:5173`
- **FastAPI Backend:** `http://127.0.0.1:8000`
- **FastAPI OpenAPI Swagger Docs:** `http://127.0.0.1:8000/docs`
- **Local MySQL Server:** `localhost:3306` (hosting `securerotate_db` & `target_demo_db`)
