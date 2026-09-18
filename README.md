# Requify Agent Pro - Intelligent BA Suite

Requify Agent Pro is a high-intelligence multi-agent platform designed to replicate the comprehensive workflow of a Senior Business Analyst. It transforms raw requirements into engineering-ready backlogs using parallel reasoning, visual process mapping, and real-time Azure DevOps integration.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- **.NET 8.0 SDK** (for Playwright C# Test Automation)
- **Azure DevOps Project**
- **Required cloud credentials configured in environment variables**

---

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Configuration
Create a `.env` file in the `backend` directory:
```env
# AI Providers
GROQ_CREDENTIAL=<set_in_environment>

# Azure DevOps
ADO_ORG_URL=https://dev.azure.com/<your_org>
ADO_PROJECT=<your_project>
ADO_CREDENTIAL=<set_in_environment>
```

#### Running the Backend
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
#python -m uvicorn main:app --reload
```
The API will be available at `http://localhost:8000`.

---

### 3. Frontend Setup
```bash
cd frontend
npm install
```

#### Running the Frontend
```bash
npm run dev
```
The application will be available at `http://localhost:5173`.

---

### 4. Playwright C# Test Automation Setup & Execution
The repository includes an enterprise **Playwright C# Automation Framework** (.NET 8 / NUnit) under [`PlaywrightAutomation/`](file:///c:/Users/VMADMIN/Videos/SURYA/baagent/PlaywrightAutomation/):

#### Build & Install Browsers
```powershell
cd PlaywrightAutomation
dotnet build PlaywrightAutomation.sln
powershell -ExecutionPolicy Bypass -File src/PlaywrightAutomation.Tests/bin/Debug/net8.0/playwright.ps1 install
```

#### Run Automation Tests
```powershell
# Run all tests
dotnet test --logger "trx;LogFileName=test_results.trx"

# Run tests against Staging environment
$env:TEST_ENVIRONMENT="Staging"; dotnet test
```

For detailed framework documentation, POM templates, logging configuration, and coding standards, refer to [`PlaywrightAutomation/README.md`](file:///c:/Users/VMADMIN/Videos/SURYA/baagent/PlaywrightAutomation/README.md).

---

## 🧠 Key Features
- **Intelligent Extraction**: Uses Groq/Azure OpenAI for high-speed requirement capturing.
- **Expert Reviewers**: Unified Gap Analysis with QA, Security, and UX audits.
- **Visual Flow**: Automated Mermaid.js process visualization.
- **Release Strategist**: AI-driven MoSCoW prioritization and delivery roadmap.
- **ADO Control Platform**: Real-time bidirectional sync with Azure DevOps work items.
- **Capacity Planner**: Workload distribution and bottleneck detection.
- **Automation Framework**: Modular Playwright C# test automation framework with POM, Serilog logging, ExtentReports HTML reporting, and trace capture.

---

## 🛠 Tech Stack
- **Backend**: FastAPI, SQLAlchemy, Llama 3.1 70B (via Groq), Azure OpenAI.
- **Frontend**: React, Vite, Vanilla CSS (Glassmorphism), Mermaid.js.
- **Test Automation**: Playwright C#, .NET 8.0, NUnit, Serilog, ExtentReports, Polly.
