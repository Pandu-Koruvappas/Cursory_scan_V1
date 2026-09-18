# Azure Deployment Guide: Code-Based Architecture 🚀

This guide explains how to deploy the **BA Agent Pro** platform WITHOUT Docker:
1. **Frontend**: Azure Static Web App
2. **Backend**: Azure App Service (Python Runtime)

---

## 1. Backend Deployment (Azure App Service)

### A. Deployment Method
1. Create a **Web App** in Azure with:
   - **Runtime Stack**: `Python 3.11` (or 3.12)
   - **Operating System**: `Linux`
2. **Deployment Center**: Link your GitHub repository.
   - **IMPORTANT**: Set the build to look in the `/backend` folder or ensure your Startup Command points there.

### B. App Service Configuration
In **Settings > Configuration > General Settings**, set the **Startup Command**:
```bash
gunicorn --bind=0.0.0.0 --timeout 600 --workers 4 --worker-class uvicorn.workers.UvicornWorker main:app
```

### C. Application Settings
Add these in **Settings > Configuration > Application settings**:

| Key | Value | Reason |
|-----|-------|--------|
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Tells Azure to run pip install |
| `DATABASE_URL` | `postgresql://...` | DB Connection String |
| `OPENAI_CREDENTIAL` | `<set_in_environment>` | AI Reasoning/Vision |
| `GROQ_CREDENTIAL` | `<set_in_environment>` | AI Speed |
| `ADO_CREDENTIAL` | `<set_in_environment>` | Azure DevOps Access |

---

## 2. Frontend Deployment (Azure Static Web App)

### A. Point to the Backend
Ensure your frontend knows the Backend's URL.
1. In the **Azure Static Web App** portal, go to **Settings > Configuration**.
2. Add an environment variable:
   - **Name**: `VITE_API_BASE_URL`
   - **Value**: `https://<your-backend-app-name>.azurewebsites.net`

### B. Deployment
1. Link your GitHub repository.
2. **Build Details**:
   - **Build Preset**: `Vite`
   - **App location**: `/frontend`
   - **Output location**: `dist`

---

## 3. Security (CORS)
In your **Backend App Service**:
1. Go to **Settings > CORS**.
2. Add your Frontend URL: `https://<your-static-app-name>.azurestaticapps.net`
3. Check "Enable Access-Control-Allow-Credentials".
4. Click **Save**.

> [!IMPORTANT]
> **RESTART REQUIRED**: Every time you update an Environment Variable in the Azure Portal, you MUST manually **Restart** the App Service for the changes to take effect.
