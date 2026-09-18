# 🚀 BA Agent Pro: Manual Deployment Guide (Render Web Service)

This guide outlines how to deploy the unified **BA Agent Pro** platform to Render as a standard **Web Service**, which is compatible with both free and paid tiers.

## 📦 Prerequisites
- A **GitHub** account with your code pushed to a repository.
- A **Render** account.
- Required cloud credentials configured in the Render environment settings.

---

## 🛠️ Step 1: Create the Database
Since we are not using Blueprints, we'll create the database first:
1. In Render Dashboard, click **New** ➔ **PostgreSQL**.
2. Name it `ba-agent-db`.
3. Select the **Free** or **Starter** plan.
4. Once created, copy the **Internal Database URL** (it looks like `postgres://user:pass@host/db`).

---

## 🌐 Step 2: Create the Web Service
1. Click **New** ➔ **Web Service**.
2. Connect your GitHub repository.
3. **Name**: `ba-agent-pro`
4. **Environment**: `Docker` (Render will automatically detect your `Dockerfile`).
5. **Plan**: Select your preferred plan (Starter or Free).

---

## 🔑 Step 3: Configure Environment Variables
In the **Environment** tab of your new Web Service, add the following variables:

| Key | Value |
| :--- | :--- |
| `DATABASE_URL` | Paste the **Internal Database URL** from Step 1 |
| `GROQ_CREDENTIAL` | Set in environment / secret store |
| `OPENAI_CREDENTIAL` | Set in environment / secret store |
| `ADO_ORGANIZATION` | Your Azure DevOps Organization name |
| `ADO_PROJECT` | Your Azure DevOps Project name |
| `ADO_CREDENTIAL` | Set in environment / secret store |
| `PORT` | `8000` |

---

## ✅ Step 4: Verify Deployment
Once the "Build Successful" and "Deploying" logs finish:
1. Open your Render URL (e.g., `https://ba-agent-pro.onrender.com`).
2. **Test the Resilience Pillars**:
    - Upload a BRD to see the **Quality Score**.
    - Run an analysis to see the **Critic's Opinion**.
    - Click **"Commit to ADO"** to test the **Human-in-the-Loop** sync.

---

## 🛠️ Maintenance
To update:
`git push origin main` ➔ Render will automatically redeploy the new container.
