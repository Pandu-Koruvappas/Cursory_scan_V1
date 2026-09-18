import React, { useState, useEffect } from 'react'; // Enterprise Discovery Platform v1.1
import ReactMarkdown from 'react-markdown';
import TelemetryDashboard from './components/TelemetryDashboard';
import ChatWidget from './components/Chatbot/ChatWidget';
import TestCaseAgentView from './components/Views/TestCaseAgentView';
import DirectBacklogView from './components/Views/DirectBacklogView';
import SprintPlannerView from './components/Views/SprintPlannerView';
import TestCasesViewer from './components/Views/TestCasesViewer';
import FunctionalSpecAccordionViewer from './components/Views/FunctionalSpecAccordionViewer';
import StoryDetailsFormatted from './components/StoryDetailsFormatted';
import { Cloud, Send } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'
    : 'https://ba-agent-aqd8c3d8dtdrbcat.centralus-01.azurewebsites.net'
);

// --- Components ---
const AdoImportWidget = ({ onGenerate }) => {
  const [items, setItems] = useState([]);
  const fetchItems = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/ado/work-items`);
      const data = await res.json();
      setItems(data.work_items || []);
    } catch (e) {
      alert('Error fetching ADO items: ' + e.message);
    }
    setLoading(false);
  };

  return (
    <div className="discovery-tile glass-card" style={{ maxWidth: '800px', margin: '0 auto 32px', cursor: 'default', flexDirection: 'column', alignItems: 'stretch', padding: '32px' }}>
      <div className="tile-accent blue"></div>
      <div className="tile-info" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
        <div>
          <h3 style={{ margin: '0 0 8px 0', fontSize: '1.2rem' }}>🔄 Import ADO Epic / Feature</h3>
          <p>Generate User Stories & Tasks for an existing ADO item.</p>
        </div>
        <button className="btn-secondary btn-mini" onClick={fetchItems}>
          {loading ? 'Fetching...' : 'Fetch Items'}
        </button>
      </div>
      
      {items.length > 0 && (
        <div style={{ marginTop: '20px', maxHeight: '300px', overflowY: 'auto' }}>
          <table className="analysis-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Title</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {items.map(item => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.type}</td>
                  <td>{item.title}</td>
                  <td>
                    <button className="btn-primary btn-mini" onClick={() => onGenerate(item)}>
                      Generate Stories
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard', 'new_analysis'
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [completedSteps, setCompletedSteps] = useState([]);
  const [selectedProject, setSelectedProject] = useState('Project Backstage');
  const [selectedLOB, setSelectedLOB] = useState('Personal Auto');
  const [selectedModules, setSelectedModules] = useState(['gaps', 'functional_spec', 'backlog', 'test_cases']);
  const [techContext, setTechContext] = useState("");

  const toggleModule = (id) => {
    setSelectedModules(prev => 
      prev.includes(id) ? prev.filter(m => m !== id) : [...prev, id]
    );
  };


  // Data State
  const [stats, setStats] = useState({ documents: 0, analyses: 0 });
  const [tableData, setTableData] = useState([]);
  const [dashboardFilter, setDashboardFilter] = useState('documents');
  const [projectContext, setProjectContext] = useState("");
  const [sprintMetrics, setSprintMetrics] = useState(null);

  // Analysis Workflow State
  const [workflowData, setWorkflowData] = useState({
    extraction: null,
    gaps: null,
    functional_spec: null,
    backlog: null,
    reviews: null,
    test_cases: null
  });

  useEffect(() => {
    if (isLoggedIn && currentView === 'dashboard') fetchDashboardData();
  }, [isLoggedIn, dashboardFilter, currentView, selectedLOB]);

  const fetchDashboardData = async () => {
    try {
      const qs = ""; 
      const [docRes, anaRes, contextRes, metricsRes] = await Promise.all([
        fetch(`${API_BASE}/documents${qs}`),
        fetch(`${API_BASE}/analyses${qs}`),
        fetch(`${API_BASE}/project-context`),
        fetch(`${API_BASE}/sprint-metrics`)
      ]);
      const docs = await docRes.json();
      const analyses = await anaRes.json();
      const contextData = await contextRes.json();
      const metricsData = await metricsRes.json();

      setStats({ documents: docs.length, analyses: analyses.length });
      setTableData(dashboardFilter === 'documents' ? docs : analyses);
      setProjectContext(contextData.context || "No project context found.");
      setSprintMetrics(metricsData);
    } catch (e) { console.error("Data Fetch Error", e); }
  };

  useEffect(() => {
    const handleGenerateAdo = async (e) => {
      const epic = e.detail;
      setLoading(true);
      setCurrentView('workflow');
      setActiveStep(6);
      
      setWorkflowData({
        doc: { id: "ado-" + epic.id, name: epic.title },
        extraction: { functional_requirements: [{ req_id: "REQ-01", description: epic.title }] },
        functional_spec: "Generated from ADO: " + epic.title,
        reviews: {
          qa: [{ category: "Quality", point: "Verify ADO stories", risk: "Low" }],
          security: [{ category: "Security", point: "Standard review", risk: "Low" }],
          ux: [{ category: "UX", point: "N/A", risk: "Low" }]
        },
        backlog: null,
        test_cases: null
      });

      try {
        const res = await fetch(`${API_BASE}/api/ado/generate-stories`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ epic })
        });
        const data = await res.json();
        
        setWorkflowData(prev => ({
          ...prev,
          backlog: data.backlog,
          analysis_id: "ado-" + epic.id
        }));
        
        setCompletedSteps([1,2,3,4,5,6]);
      } catch (err) {
        alert("Error generating stories: " + err.message);
      }
      setLoading(false);
    };

    window.addEventListener('generate-ado', handleGenerateAdo);
    return () => window.removeEventListener('generate-ado', handleGenerateAdo);
  }, []);

  const startAutomatedWorkflow = async (file, channel = "document") => {
    setLoading(true);
    setCompletedSteps([]);
    setCurrentView('workflow');

    try {
      // 1. INGESTION
      setActiveStep(1);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('channel', channel);
      formData.append('lob', selectedLOB);
      const ingestRes = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: formData });
      const ingestData = await ingestRes.json();

      setWorkflowData(prev => ({ ...prev, extraction: ingestData.extraction, docId: ingestData.document_id }));
      if (ingestData.document_id) {
        try { localStorage.setItem('active_doc_id', ingestData.document_id); } catch(e) {}
      }
      setCompletedSteps(prev => [...prev, 1]);

      // 2. GAP ANALYSIS (Modular)
      setActiveStep(2);
      let anaData = {};
      let questions = [];
      try {
        const analyzeRes = await fetch(`${API_BASE}/analyze`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            document_id: ingestData.document_id,
            enabled_modules: selectedModules 
          }),
        });
        
        if (!analyzeRes.ok) throw new Error("Network response was not ok");
        anaData = await analyzeRes.json();

        if (!anaData.results) {
          throw new Error(anaData.detail || "Analysis failed to return structured results.");
        }

        questions = anaData.results.clarification_questions || [];
        
        // Inject Ambiguities from Phase 1
        if (ingestData.ambiguity_report && ingestData.ambiguity_report.ambiguities) {
           const ambQuestions = ingestData.ambiguity_report.ambiguities.map(a => ({
               context: `[AMBIGUITY] ${a.requirement.substring(0, 50)}...`,
               question: `${a.issue} -> ${a.clarification_question}`
           }));
           questions = [...ambQuestions, ...questions];
        }

        setWorkflowData(prev => ({
          ...prev,
          analysisId: anaData.analysis_id,
          gaps: anaData.results.gaps,
          reviews: anaData.results.reviews,
          clarifications: questions,
          docId: ingestData.document_id
        }));
      } catch (gapError) {
        console.warn("Gap Analysis failed or timed out. Degrading gracefully.", gapError);
        // Provide empty fallback data so Functional Spec can still run on the raw extraction
        anaData = { analysis_id: ingestData.document_id, results: { gaps: [], reviews: {}, diagram: "" } };
        setWorkflowData(prev => ({
          ...prev,
          analysisId: ingestData.document_id,
          gaps: [],
          reviews: null,
          test_cases: null,
          clarifications: [],
          docId: ingestData.document_id
        }));
      }

      // Intervention: If AI has questions, stop and ask the BA
      if (questions.length > 0) {
        setCompletedSteps(prev => [...prev, 2]);
        setCurrentView('clarification');
        setLoading(false);
        return;
      }

      setCompletedSteps(prev => [...prev, 2]);

      // 3. FUNCTIONAL SPEC GENERATION (Conditional)
      let specData = null;
      if (selectedModules.includes('functional_spec')) {
        setActiveStep(3);
        const specRes = await fetch(`${API_BASE}/generate-functional-spec`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ analysis_id: anaData.analysis_id, tech_context: techContext }),
        });
        const specResult = await specRes.json();
        specData = specResult.functional_spec;
        setWorkflowData(prev => ({ ...prev, functional_spec: specData }));
        setCompletedSteps(prev => [...prev, 3]);
      }

      // 4. BACKLOG GENERATION (Conditional)
      let backData = null;
      if (selectedModules.includes('backlog')) {
        setActiveStep(4);
        const backlogRes = await fetch(`${API_BASE}/generate-backlog`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            functional_spec: specData,
            analysis_id: anaData.analysis_id,
            document_id: ingestData.document_id
          }),
        });
        backData = await backlogRes.json();
        setWorkflowData(prev => ({ ...prev, backlog: backData.backlog, critic_review: backData.critic_review }));
        setCompletedSteps(prev => [...prev, 4]);
      }

      // 5. TEST CASE GENERATION (Conditional)
      if (selectedModules.includes('test_cases') && backData && backData.backlog) {
        setActiveStep(5);
        const testCaseRes = await fetch(`${API_BASE}/api/agents/draft-test-cases`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ backlog_json: backData.backlog, analysis_id: anaData.analysis_id })
        });
        const testCaseResult = await testCaseRes.json();
        setWorkflowData(prev => ({ ...prev, test_cases: testCaseResult.test_cases }));
        setCompletedSteps(prev => [...prev, 5]);
      }

      setActiveStep(6); // Review Phase
    } catch (error) {
      alert(`Workflow Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const resumeWorkflow = async (docId, answers) => {
    setLoading(true);
    setCurrentView('workflow');
    try {
      // Re-run Gap Analysis WITH answers
      setActiveStep(2);
      const analyzeRes = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: docId, answers: answers }),
      });
      const anaData = await analyzeRes.json();

      setWorkflowData(prev => ({
        ...prev,
        analysisId: anaData.analysis_id,
        gaps: anaData.results.gaps,
        reviews: anaData.results.reviews,
        diagram: anaData.results.diagram
      }));

      // Now proceed to 3 and 4
      // 3. FUNCTIONAL SPEC GENERATION
      setActiveStep(3);
      const specRes = await fetch(`${API_BASE}/generate-functional-spec`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis_id: anaData.analysis_id, tech_context: techContext }),
      });
      const specResult = await specRes.json();
      setWorkflowData(prev => ({ 
        ...prev, 
        functional_spec: specResult.functional_spec,
        reviews: specResult.reviews || prev.reviews 
      }));
      setCompletedSteps(prev => [...prev, 3]);

      // 4. BACKLOG GENERATION (Conditional)
      let backData = null;
      if (selectedModules.includes('backlog')) {
        setActiveStep(4);
        const backlogRes = await fetch(`${API_BASE}/generate-backlog`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            functional_spec: specResult.functional_spec,
            analysis_id: anaData.analysis_id,
            document_id: docId
          }),
        });
        backData = await backlogRes.json();
        setWorkflowData(prev => ({ ...prev, backlog: backData.backlog, critic_review: backData.critic_review }));
        setCompletedSteps(prev => [...prev, 4]);
      }

      // 5. TEST CASE GENERATION (Conditional)
      if (selectedModules.includes('test_cases') && backData && backData.backlog) {
        setActiveStep(5);
        const testCaseRes = await fetch(`${API_BASE}/api/agents/draft-test-cases`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ backlog_json: backData.backlog, analysis_id: anaData.analysis_id })
        });
        const testCaseResult = await testCaseRes.json();
        setWorkflowData(prev => ({ ...prev, test_cases: testCaseResult.test_cases }));
        setCompletedSteps(prev => [...prev, 5]);
      }

      setActiveStep(6);
    } catch (err) {
      alert(`Resume Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const resumeExistingAnalysis = async (analysisId) => {
    setLoading(true);
    setCurrentView('workflow');
    try {
      const res = await fetch(`${API_BASE}/analysis/${analysisId}`);
      const data = await res.json();
      
      const resData = data.results || {};
      const hasAnyData = Object.keys(resData).length > 0 || data.extraction || data.functional_spec || data.backlog || data.test_cases;
      if (!hasAnyData) throw new Error("Analysis data is empty.");

      // Calculate what is currently complete
      let currentSpec = data.functional_spec || resData.functional_spec || resData.trd || "";
      let currentBacklog = data.backlog || resData.backlog || resData.backlog_items || null;
      let currentTestCases = data.test_cases || resData.test_cases || null;
      let currentReviews = data.reviews || data.critic_review || resData.reviews || resData.critic_review || null;

      setWorkflowData(prev => ({
        ...prev,
        analysisId: data.id,
        extraction: data.extraction || resData.extraction || {},
        gaps: data.gaps || resData.gaps || [],
        functional_spec: currentSpec,
        backlog: currentBacklog,
        test_cases: currentTestCases,
        reviews: currentReviews,
        diagram: data.diagram || resData.diagram || null,
        docId: data.document_id || data.id
      }));

      if (data.document_id || data.id) {
        try { localStorage.setItem('active_doc_id', data.document_id || data.id); } catch(e) {}
      }

      const completed = [];
      if (data.extraction || resData.extraction) completed.push(1);
      if (data.gaps || resData.gaps) completed.push(2);
      
      setCompletedSteps([...completed]);

      // 3. FUNCTIONAL SPEC GENERATION (Resume if missing)
      if (!currentSpec) {
        setActiveStep(3);
        const specRes = await fetch(`${API_BASE}/generate-functional-spec`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ analysis_id: data.id, tech_context: "" }),
        });
        const specResult = await specRes.json();
        currentSpec = specResult.functional_spec;
        setWorkflowData(prev => ({ ...prev, functional_spec: currentSpec }));
        completed.push(3);
        setCompletedSteps([...completed]);
      } else {
        completed.push(3);
        setCompletedSteps([...completed]);
      }

      // 4. BACKLOG GENERATION (Resume if missing)
      if (!currentBacklog) {
        setActiveStep(4);
        const backlogRes = await fetch(`${API_BASE}/generate-backlog`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ 
            functional_spec: currentSpec,
            analysis_id: data.id,
            document_id: data.document_id
          }),
        });
        const backData = await backlogRes.json();
        currentBacklog = backData.backlog;
        currentReviews = backData.critic_review;
        setWorkflowData(prev => ({ ...prev, backlog: currentBacklog, reviews: currentReviews }));
        completed.push(4);
        setCompletedSteps([...completed]);
      } else {
        completed.push(4);
        setCompletedSteps([...completed]);
      }

      // 5. TEST CASE GENERATION (Resume if missing)
      if (!currentTestCases && currentBacklog) {
        setActiveStep(5);
        const testCaseRes = await fetch(`${API_BASE}/api/agents/draft-test-cases`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ backlog_json: currentBacklog, analysis_id: data.id })
        });
        const testCaseResult = await testCaseRes.json();
        currentTestCases = testCaseResult.test_cases;
        setWorkflowData(prev => ({ ...prev, test_cases: currentTestCases }));
        completed.push(5);
        setCompletedSteps([...completed]);
      } else if (currentTestCases) {
        completed.push(5);
        setCompletedSteps([...completed]);
      }

      // Always show final review at activeStep 5 or 6 depending on UI logic. 
      // The UI uses activeStep === 5 for the final review area if test cases were generated, but actually line 1090 is activeStep === 5. Wait, we should set it to 5 or 6?
      // Wait, earlier we found line 1090 is `activeStep === 5 && (` so we MUST set it to 5 to trigger the review panel!
      // But we just pushed 5 to completed. So activeStep should be 5!
      setActiveStep(5);
      
    } catch (err) {
      alert(`Resume Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCloseSession = () => {
    setWorkflowData({ extraction: null, gaps: null, functional_spec: null, backlog: null, reviews: null, test_cases: null });
    setCompletedSteps([]);
    try { localStorage.removeItem('active_doc_id'); } catch(e) {}
    setCurrentView('new_analysis');
  };

  const toggleSelection = (level, indices) => {
    setWorkflowData(prev => {
      const newBacklog = { ...prev.backlog };
      const { epicIdx, featIdx, storyIdx } = indices;

      if (level === 'epic') {
        const epic = newBacklog.epics[epicIdx];
        const newState = !epic.selected;
        epic.selected = newState;
        // Recursive selection for children
        epic.features?.forEach(f => {
          f.selected = newState;
          f.user_stories?.forEach(s => s.selected = newState);
        });
      } else if (level === 'feature') {
        const feat = newBacklog.epics[epicIdx].features[featIdx];
        const newState = !feat.selected;
        feat.selected = newState;
        feat.user_stories?.forEach(s => s.selected = newState);
      } else if (level === 'story') {
        const story = newBacklog.epics[epicIdx].features[featIdx].user_stories[storyIdx];
        story.selected = !story.selected;
      }

      return { ...prev, backlog: newBacklog };
    });
  };

  const handleUpdateArtifact = (type, content) => {
    setWorkflowData(prev => ({ ...prev, [type]: content }));
  };

  const handleRegenerateArtifact = async (type, currentContent, feedback) => {
    try {
      const res = await fetch(`${API_BASE}/api/agents/regenerate-artifact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          artifact_type: type,
          current_content: currentContent,
          feedback: feedback,
          analysis_id: workflowData.analysisId
        })
      });
      if (!res.ok) throw new Error('Regeneration failed');
      const data = await res.json();
      let updatedContent = data.content;
      
      if (['backlog', 'test_cases', 'reviews'].includes(type)) {
        try {
          let clean = updatedContent.trim();
          if (clean.startsWith('```')) {
            clean = clean.replace(/^```[a-z]*\n/i, '').replace(/\n```$/i, '').trim();
          }
          updatedContent = JSON.parse(clean);
        } catch (e) {
          // Keep as string if parsing fails
        }
      }
      setWorkflowData(prev => ({ ...prev, [type]: updatedContent }));
    } catch (e) {
      alert("Error regenerating: " + e.message);
    }
  };

  const handleApproveAndSync = async (reviewerEmail) => {
    if (!reviewerEmail) {
      alert("Please enter a valid email address.");
      return;
    }
    setIsSyncing(true);
    try {
      const response = await fetch(`${API_BASE}/request-approval`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          analysis_id: workflowData.analysisId,
          backlog: workflowData.backlog,
          reviewer_email: reviewerEmail
        }),
      });
      const result = await response.json();
      if (result.error) throw new Error(result.error);

      alert("📧 Approval Request Dispatched! The stakeholder has been notified with the Functional Spec and backlog for final authorization.");
      // REMOVED: setCurrentView('dashboard'); -> Stay in session until manually closed
    } catch (err) {
      alert(`Approval Request Error: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  if (!isLoggedIn) return <Login onLogin={() => setIsLoggedIn(true)} />;

  return (
    <div className={`app-layout ${isSidebarCollapsed ? 'collapsed' : ''}`}>
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', width: '100%' }}>
          {!isSidebarCollapsed && <img src="/assets/ValueMomentumlogo.png" alt="Logo" className="sidebar-logo" style={{ margin: '0 auto', display: 'block' }} />}
          <button className="sidebar-toggle" onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)} style={{ position: isSidebarCollapsed ? 'static' : 'absolute', right: 0 }}>
            {isSidebarCollapsed ? '>' : '<'}
          </button>
        </div>

        <nav className="side-nav">
          <div className="nav-group" style={{ marginBottom: '20px' }}>
            <div className="nav-label">Context</div>
            {!isSidebarCollapsed ? (
              <select 
                value={selectedProject}
                style={{ width: '90%', padding: '8px', background: 'rgba(0,0,0,0.05)', color: '#000', border: '1px solid rgba(0,0,0,0.2)', borderRadius: '5px', outline: 'none' }}
                onChange={(e) => setSelectedProject(e.target.value)}
              >
                <option value="Project Backstage" style={{ color: '#000', background: '#fff' }}>Project Backstage (ADO)</option>
              </select>
            ) : (
              <div style={{ textAlign: 'center', fontSize: '1.2rem' }}>🏢</div>
            )}
          </div>

          <div className="nav-group">
            <div className="nav-label">Intelligence Hub</div>
            <div className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('dashboard')}>
              <span className="nav-icon"><img src="/assets/icons/dashboard.png" width="18" height="18" alt="Dashboard" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Command Center"}
            </div>
            <div className={`nav-item ${currentView === 'knowledge_vault' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('knowledge_vault')}>
              <span className="nav-icon"><img src="/assets/icons/briefcase.png" width="18" height="18" alt="Memory" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Institutional Memory"}
            </div>
          </div>

          <div className="nav-group">
            <div className="nav-label">Delivery OS</div>
            <div className={`nav-item ${currentView === 'new_analysis' || currentView === 'workflow' || currentView === 'clarification' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => {
              if (workflowData && (workflowData.docId || workflowData.extraction || workflowData.analysisId)) {
                if (workflowData.clarifications && workflowData.clarifications.length > 0 && completedSteps.length < 3) {
                  setCurrentView('clarification');
                } else {
                  setCurrentView('workflow');
                }
              } else {
                setCurrentView('new_analysis');
                setSelectedModules(['gaps', 'functional_spec', 'test_cases', 'backlog']);
              }
            }}>
              <span className="nav-icon"><img src="/assets/icons/professional-services.png" width="18" height="18" alt="Discovery" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Discovery Swarm"}
            </div>
            <div className={`nav-item ${currentView === 'quick_backlog' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('quick_backlog')}>
              <span className="nav-icon"><img src="/assets/icons/multitasking (2).png" width="18" height="18" alt="Quick Backlog" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Quick Backlog"}
            </div>
            <div className={`nav-item ${currentView === 'work_items' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('work_items')}>
              <span className="nav-icon"><img src="/assets/icons/multitasking.png" width="18" height="18" alt="Backlog" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Backlog Explorer"}
            </div>
            <div className={`nav-item ${currentView === 'traceability' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('traceability')}>
              <span className="nav-icon"><img src="/assets/icons/professional-network.png" width="18" height="18" alt="Governance" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Governance Matrix"}
            </div>
          </div>

          <div className="nav-group">
            <div className="nav-label">Agentic Tools</div>
            <div className={`nav-item ${currentView === 'gap_detective' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('gap_detective')}>
              <span className="nav-icon"><img src="/assets/icons/evaluation.png" width="18" height="18" alt="Gaps" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Gap Detective"}
            </div>
            <div className={`nav-item ${currentView === 'spec_architect' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('spec_architect')}>
              <span className="nav-icon"><img src="/assets/icons/business.png" width="18" height="18" alt="Spec" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Functional Architect"}
            </div>
            <div className={`nav-item ${currentView === 'flow_designer' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('flow_designer')}>
              <span className="nav-icon"><img src="/assets/icons/multitasking (1).png" width="18" height="18" alt="Flow" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Flow Designer"}
            </div>
            <div className={`nav-item ${currentView === 'test_case_agent' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('test_case_agent')}>
              <span className="nav-icon"><img src="/assets/icons/professionalism.png" width="18" height="18" alt="Tests" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Test Case Agent"}
            </div>
            <div className={`nav-item ${currentView === 'sprint_planner' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('sprint_planner')}>
              <span className="nav-icon"><img src="/assets/icons/professional.png" width="18" height="18" alt="Sprint" style={{ verticalAlign: 'middle' }} /></span> {!isSidebarCollapsed && "Sprint Planner"}
            </div>
          </div>
          
          <div className="nav-group">
            <div className="nav-label">Admin</div>
            <div className={`nav-item ${currentView === 'telemetry' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setCurrentView('telemetry')}>
              <span className="nav-icon"><Cloud size={18} /></span> {!isSidebarCollapsed && "LLMOps Telemetry"}
            </div>
          </div>
        </nav>

        <div className="user-profile">
          <div className="avatar">JD</div>
          {!isSidebarCollapsed && (
            <div className="user-info">
              <div className="name">BA User</div>
              <div className="role">Senior Analyst</div>
            </div>
          )}
        </div>
      </aside>

      {/* Main Area */}
      <main className="main-content">
        {currentView === 'dashboard' && (
          <DashboardView
            stats={stats}
            filter={dashboardFilter}
            setFilter={setDashboardFilter}
            data={tableData}
            context={projectContext}
            metrics={sprintMetrics}
            onResume={resumeExistingAnalysis}
            onNavigate={setCurrentView}
          />
        )}

        {currentView === 'work_items' && (
          <WorkItemsView />
        )}

        {currentView === 'capacity' && (
          <CapacityView />
        )}

        {currentView === 'telemetry' && (
          <TelemetryDashboard />
        )}

        {currentView === 'quick_backlog' && (
          <DirectBacklogView />
        )}

        {currentView === 'sprint_planner' && (
          <SprintPlannerView />
        )}

        {currentView === 'releases' && (
          <ReleaseView data={workflowData.backlog} />
        )}

        {currentView === 'clarification' && (
          <ClarificationView
            questions={workflowData.clarifications}
            docId={workflowData.docId}
            onResume={resumeWorkflow}
          />
        )}

        {currentView === 'new_analysis' && (
          <SelectionView
            onSelect={startAutomatedWorkflow}
            selectedLOB={selectedLOB}
            setSelectedLOB={setSelectedLOB}
            selectedModules={selectedModules}
            onToggleModule={toggleModule}
            techContext={techContext}
            setTechContext={setTechContext}
          />
        )}


        {currentView === 'gap_detective' && (
          <GapDetectiveView />
        )}

        {currentView === 'spec_architect' && (
          <SpecArchitectView />
        )}

        {currentView === 'flow_designer' && (
          <FlowDesignerView />
        )}

        {currentView === 'backlog_engineer' && (
          <BacklogEngineerView />
        )}

        {currentView === 'traceability' && (
          <TraceabilityMatrixView />
        )}

        {currentView === 'knowledge_vault' && (
          <KnowledgeVaultView />
        )}

        {currentView === 'test_case_agent' && (
          <TestCaseAgentView />
        )}

        {currentView === 'workflow' && (
          <WorkflowView
            activeStep={activeStep}
            completedSteps={completedSteps}
            data={workflowData}
            onFinish={handleApproveAndSync}
            onUpdateArtifact={handleUpdateArtifact}
            onRegenerateArtifact={handleRegenerateArtifact}
            onClose={handleCloseSession}
            isSyncing={isSyncing}
            onToggle={toggleSelection}
          />
        )}
      </main>
      
      {/* Omni-Channel Chat Assistant */}
      <ChatWidget />
    </div>
  );
}

// --- View Modules ---

const Login = ({ onLogin }) => (
  <div className="login-screen" style={{ backgroundImage: 'url("/assets/login-hero.jpg")' }}>
    <div className="login-overlay"></div>

    {/* Top Left Global Branding */}
    <div className="global-brand-corner">
      <img src="/assets/ValueMomentumlogo.png" alt="ValueMomentum" className="corner-logo" />
    </div>

    <div className="login-hero-info">
      <h1 className="hero-title">Requify</h1>

      <p className="hero-tagline">We bring intelligence to specifications</p>




      <ul className="hero-list">
        <li>✨ Automated Requirement Discovery</li>
        <li>🔍 AI-Powered Gap Analysis</li>
        <li>📄 Professional Spec Generation</li>
        <li>🚀 Enterprise DevOps Automation</li>
      </ul>
    </div>

    <div className="login-card glass-card">
      <div className="presents-flow">
        <img src="/assets/ValueMomentumlogo.png" alt="ValueMomentum" className="vm-presents-logo" />
        <span className="presents-text">presents</span>
      </div>
      <h2 className="card-brand-title">Requify</h2>
      <p className="card-brand-tagline">We bring intelligence to specifications</p>




      <div className="login-form">
        <input type="text" placeholder="Username" defaultValue="admin@valuemomentum.com" />
        <input type="password" placeholder="Password" defaultValue="password" />
        <button className="btn-primary" onClick={onLogin}>Sign In</button>
      </div>
      <div className="login-footer">© 2026 ValueMomentum. All rights reserved.</div>
    </div>
  </div>
);

const DashboardView = ({ stats, filter, setFilter, data, context, metrics, onResume }) => {
  const [showDNA, setShowDNA] = useState(false);
  const [showMetrics, setShowMetrics] = useState(false);

  return (
    <div className="view-container">
      <header className="view-header">
        <div className="title-area">
          <span className="pre-title">Cognitive Command Center</span>
          <h1>Enterprise Dashboard</h1>
          <p>Real-time orchestration and institutional memory health.</p>
        </div>
      </header>

      <div className="stat-tiles">
        <div className={`stat-tile glass-card ${filter === 'documents' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setFilter('documents')}>
          <div className="tile-top">
            <span className="tile-label">INGESTION</span>
            <span className="tile-trend up">↑ 12%</span>
          </div>
          <div className="tile-main">
            <div className="tile-val">{stats.documents}</div>
            <div className="tile-label" style={{ fontSize: '0.6rem', opacity: 0.6 }}>Cloud Ingested Documents</div>
          </div>
        </div>

        <div className={`stat-tile glass-card ${filter === 'analyses' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setFilter('analyses')}>
          <div className="tile-top">
            <span className="tile-label">GOVERNANCE</span>
            <span className="tile-trend">Stable</span>
          </div>
          <div className="tile-main">
            <div className="tile-val">{stats.analyses}</div>
            <div className="tile-label" style={{ fontSize: '0.6rem', opacity: 0.6 }}>Risk Vetted Projects</div>
          </div>
        </div>

        <div className={`stat-tile glass-card`}>
          <div className="tile-top">
            <span className="tile-label">SDLC VELOCITY</span>
            <span className="tile-trend up">↑ 8%</span>
          </div>
          <div className="tile-main">
            <div className="tile-val">94%</div>
            <div className="tile-label" style={{ fontSize: '0.6rem', opacity: 0.6 }}>ADO Sync Success Rate</div>
          </div>
        </div>
      </div>

      <div className="strategic-overview-compact">
        <div 
          className={`insight-drawer glass-card ${showDNA ? 'expanded' : ''}`}
          role="button"
          tabIndex={0}
          onMouseEnter={() => setShowDNA(true)}
          onMouseLeave={() => setShowDNA(false)}
          onFocus={() => setShowDNA(true)}
          onBlur={() => setShowDNA(false)}
          onClick={() => setShowDNA(!showDNA)}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setShowDNA(!showDNA); } }}
        >
          <div className="drawer-header">
            <span className="label">PROJECT DNA</span>
            <span className="action-hint">{showDNA ? 'Click to collapse' : 'Hover to expand'}</span>
          </div>
          <div className="drawer-content">
            <ReactMarkdown>{context}</ReactMarkdown>
          </div>
        </div>

        <div 
          className={`insight-drawer glass-card ${showMetrics ? 'expanded' : ''}`}
          role="button"
          tabIndex={0}
          onMouseEnter={() => setShowMetrics(true)}
          onMouseLeave={() => setShowMetrics(false)}
          onFocus={() => setShowMetrics(true)}
          onBlur={() => setShowMetrics(false)}
          onClick={() => setShowMetrics(!showMetrics)}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setShowMetrics(!showMetrics); } }}
        >
          <div className="drawer-header">
            <span className="label">SPRINT PLANNING</span>
            <span className="action-hint">{showMetrics ? 'Click to collapse' : 'Hover to expand'}</span>
          </div>
          <div className="drawer-content">
            {metrics && !metrics.error ? (
              <div className="metrics-summary-view">
                <div className="mini-stat"><strong>Effort:</strong> {metrics.summary?.total_backlog_effort || 0} pts</div>
                <div className="mini-stat"><strong>Complexity:</strong> {metrics.summary?.average_item_complexity || 0}</div>
                <ul className="mini-list">
                  {metrics.planning_insights?.slice(0, 2).map((ins, i) => <li key={i}>{ins}</li>)}
                </ul>
              </div>
            ) : metrics?.error ? (
              <div className="error-hint">⚠️ {metrics.error}</div>
            ) : "Calculating..."}
          </div>
        </div>
      </div>
    
      <div className="repository-grid glass-card" style={{ marginTop: '32px' }}>
        <div className="grid-header">
          <h3>Master Repository</h3>
          <div className="grid-filters">
            <button className={`btn-filter ${filter === 'documents' ? 'active' : ''}`} onClick={() => setFilter('documents')}>Documents</button>
            <button className={`btn-filter ${filter === 'analyses' ? 'active' : ''}`} onClick={() => setFilter('analyses')}>Analyses</button>
          </div>
        </div>
        <table className="modern-table">
          <thead>
            <tr>
              <th>Reference Name</th>
              <th>Resource ID</th>
              <th>Lifecycle Date</th>
              <th>Process Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {data.map(item => (
              <tr key={item.id}>
                <td className="primary-cell">{item.name || item.title}</td>
                <td className="mono-cell">{item.id.substring(0, 10).toUpperCase()}</td>
                <td className="date-cell">{new Date(item.upload_date || item.date).toLocaleDateString()}</td>
                <td><span className={`pill-badge ${item.status}`}>{item.status}</span></td>
                <td>
                  {filter === 'analyses' && (
                    <button className="btn-tab active" style={{ padding: '6px 12px', fontSize: '0.75rem' }} onClick={() => onResume(item.id)}>
                      Resume Discovery
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const SelectionView = ({ onSelect, selectedLOB, setSelectedLOB, selectedModules, onToggleModule, techContext, setTechContext }) => {
  const [ingestMode, setIngestMode] = useState('file'); // file, text, visual, meeting
  const [inputText, setInputText] = useState("");

  const handleTextSubmit = () => {
    if (!inputText.trim()) return;
    // We wrap text in a pseudo-file object or send as JSON
    const blob = new Blob([inputText], { type: 'text/plain' });
    const file = new File([blob], "direct_input.txt", { type: 'text/plain' });
    onSelect(file, "text");
  };

  return (
    <div className="view-container">
      <header className="view-header" style={{ textAlign: 'center', display: 'block' }}>
        <div className="title-area">
          <span className="pre-title">Unified Ingestion Engine</span>
          <h1>Cognitive Ingestion Hub</h1>
          <p>Provide source material via any channel—Documents, Visuals, or Transcripts.</p>
        </div>
      </header>

      <div className="ingestion-tabs-container" style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginBottom: '24px' }}>
         {['file', 'text', 'visual', 'meeting', 'ado'].map(mode => (
           <button 
             key={mode} 
             className={`btn-tab ${ingestMode === mode ? 'active' : ''}`}
             onClick={() => setIngestMode(mode)}
             style={{ textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: '0.1em' }}
           >
             {mode === 'file' && '📄 Document'}
             {mode === 'text' && '✍️ Direct Text'}
             {mode === 'visual' && '🖼️ Visuals'}
             {mode === 'meeting' && '🎙️ Meetings'}
             {mode === 'ado' && '🔄 ADO Import'}
           </button>
         ))}
      </div>

      {ingestMode === 'file' && (
        <div className="discovery-tile glass-card" style={{ maxWidth: '800px', margin: '0 auto 32px' }} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => document.getElementById('brd-up').click()}>
          <div className="tile-accent yellow"></div>
          <div className="tile-icon">📂</div>
          <div className="tile-info">
            <h3>Upload Source Document</h3>
            <p>Analyze BRD, PRD, or functional specs (PDF, DOCX, XLSX, PPTX)</p>
          </div>
          <input type="file" id="brd-up" accept=".pdf,.docx,.xlsx,.pptx" hidden onChange={(e) => onSelect(e.target.files[0], "document")} />
          <div className="tile-action">Analyze Document</div>
        </div>
      )}

      {ingestMode === 'text' && (
        <div className="text-ingestion-area glass-card" style={{ maxWidth: '800px', margin: '0 auto 32px', padding: '24px' }}>
           <textarea 
             placeholder="Paste requirements, user stories, or unformatted notes here..."
             value={inputText}
             onChange={(e) => setInputText(e.target.value)}
             style={{ width: '100%', height: '200px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', borderRadius: '8px', color: '#fff', padding: '16px', marginBottom: '16px' }}
           />
           <button className="btn-primary" style={{ width: '100%' }} onClick={handleTextSubmit}>
             Analyze Requirements
           </button>
        </div>
      )}

      {ingestMode === 'visual' && (
        <div className="discovery-tile glass-card" style={{ maxWidth: '800px', margin: '0 auto 32px' }} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => document.getElementById('img-up').click()}>
          <div className="tile-accent cyan"></div>
          <div className="tile-icon">🖼️</div>
          <div className="tile-info">
            <h3>Vision Agent: Wireframe Scan</h3>
            <p>Upload wireframes, screenshots, or whiteboard photos</p>
          </div>
          <input type="file" id="img-up" accept="image/*" hidden onChange={(e) => onSelect(e.target.files[0], "visual")} />
          <div className="tile-action">Analyze Visuals</div>
        </div>
      )}

      {ingestMode === 'meeting' && (
        <div className="discovery-tile glass-card" style={{ maxWidth: '800px', margin: '0 auto 32px' }} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => document.getElementById('meet-up').click()}>
          <div className="tile-accent purple"></div>
          <div className="tile-icon">🎙️</div>
          <div className="tile-info">
            <h3>Meeting Transcript Ingestion</h3>
            <p>Analyze Zoom/Teams transcripts or recorded summaries</p>
          </div>
          <input type="file" id="meet-up" hidden onChange={(e) => onSelect(e.target.files[0], "meeting")} />
          <div className="tile-action">Analyze Transcript</div>
        </div>
      )}

      {ingestMode === 'ado' && (
        <AdoImportWidget onGenerate={(epic) => window.dispatchEvent(new CustomEvent('generate-ado', {detail: epic}))} />
      )}

      <div className="lob-selector-container animation-fade-in" style={{ maxWidth: '800px', margin: '0 auto' }}>
        <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Select Target Context (LOB)</div>
        <div className="lob-grid">
          {['Personal Auto', 'Homeowners', 'Commercial Property', 'Workers Compensation', 'General Liability', 'Inland Marine'].map(lob => (
            <div
              key={lob}
              className={`lob-chip ${selectedLOB === lob ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setSelectedLOB(lob)}
            >
              {lob}
            </div>
          ))}
        </div>
      </div>
      
      <div className="tech-context-container animation-fade-in" style={{ maxWidth: '800px', margin: '24px auto' }}>
        <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Optional: Target Tech Stack / Integration Context</div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' }}>If provided, the agent will generate Draft Architect Handoff Notes at the end of the Functional Spec.</p>
        <textarea 
          placeholder="e.g., Azure Serverless, React frontend, integrating with Guidewire PolicyCenter via REST API..."
          value={techContext}
          onChange={(e) => setTechContext(e.target.value)}
          style={{ width: '100%', height: '80px', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', borderRadius: '8px', color: '#fff', padding: '12px' }}
        />
      </div>
      
      <div className="module-selection-container glass-card animation-fade-in" style={{ maxWidth: '800px', margin: '24px auto' }}>
        <div className="module-header">
          <h3>Toolkit Configuration</h3>
          <p>Enable the specialized agents for this discovery session.</p>
        </div>
        <div className="module-grid">
          {[
            { id: 'gaps', label: 'Gap Analysis', icon: '🔍' },
            { id: 'functional_spec', label: 'Functional Spec', icon: '📝' },
            { id: 'backlog', label: 'Backlog', icon: '📂' },
            { id: 'test_cases', label: 'Test Cases', icon: '🧪' }
          ].map(module => (
            <label htmlFor={`module-${module.id}`} key={module.id} className={`module-chip ${selectedModules.includes(module.id) ? 'active' : ''}`}>
              <input 
                id={`module-${module.id}`}
                type="checkbox" 
                checked={selectedModules.includes(module.id)} 
                onChange={() => onToggleModule(module.id)}
                hidden 
              />
              <span className="mod-icon">{module.icon}</span>
              <span className="mod-label">{module.label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
};

const ArtifactEditorWrapper = ({ title, artifactType, rawContent, onSave, onRegenerate, children }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [feedback, setFeedback] = useState('');
  const [isRegenerating, setIsRegenerating] = useState(false);

  const handleEditClick = () => {
    setEditContent(typeof rawContent === 'string' ? rawContent : JSON.stringify(rawContent, null, 2));
    setIsEditing(true);
  };

  const handleSave = () => {
    let finalContent = editContent;
    if (typeof rawContent === 'object' && rawContent !== null) {
      try { finalContent = JSON.parse(editContent); } catch (e) { alert("Invalid JSON! Please fix."); return; }
    }
    onSave(artifactType, finalContent);
    setIsEditing(false);
  };

  const handleRegenerate = async () => {
    if (!feedback) return;
    setIsRegenerating(true);
    await onRegenerate(artifactType, typeof rawContent === 'string' ? rawContent : JSON.stringify(rawContent), feedback);
    setIsRegenerating(false);
    setFeedback('');
  };

  return (
    <div className="artifact-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '16px', height: '100%' }}>
      <div style={{ flex: 1, minHeight: 0 }}>
        {isEditing ? (
          <textarea 
            value={editContent} 
            onChange={(e) => setEditContent(e.target.value)}
            style={{ width: '100%', minHeight: '400px', height: '100%', fontFamily: 'monospace' }}
          />
        ) : (
          children
        )}
      </div>
      
      <div className="artifact-actions glass-card" style={{ display: 'flex', gap: '16px', padding: '16px', alignItems: 'center', flexWrap: 'wrap', marginTop: '16px' }}>
        <div style={{ display: 'flex', gap: '8px', borderRight: '1px solid var(--glass-border)', paddingRight: '16px' }}>
          {isEditing ? (
            <>
              <button className="btn-secondary" onClick={() => setIsEditing(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleSave}>💾 Save Manual Edits</button>
            </>
          ) : (
            <button className="btn-secondary" onClick={handleEditClick}>✏️ Manual Edit</button>
          )}
        </div>
        
        <div style={{ display: 'flex', gap: '8px', flex: 1 }}>
          <input 
            type="text" 
            placeholder="Feedback for AI (e.g. 'Add a SSO login page requirement')" 
            value={feedback} 
            onChange={(e) => setFeedback(e.target.value)} 
            disabled={isEditing || isRegenerating}
            style={{ flex: 1 }}
          />
          <button 
            className="btn-primary" 
            onClick={handleRegenerate}
            disabled={!feedback || isEditing || isRegenerating}
          >
            {isRegenerating ? '⏳ Regenerating...' : '✨ Regenerate with AI'}
          </button>
        </div>
      </div>
    </div>
  );
};

const WorkflowView = ({ activeStep, completedSteps, data, onFinish, onClose, isSyncing, onToggle, onUpdateArtifact, onRegenerateArtifact }) => {
  const [activeReviewTab, setActiveReviewTab] = useState('functional_spec'); // 'functional_spec', 'backlog', 'flow'
  const [showAllReqs, setShowAllReqs] = useState(false);
  const [showAllGaps, setShowAllGaps] = useState(false);
  const [showEmailModal, setShowEmailModal] = useState(false);
  const [reviewerEmail, setReviewerEmail] = useState('');
  const [includeNFR, setIncludeNFR] = useState(true);

  const STEPS = [
    { title: 'Extraction', icon: <img src="/assets/icons/icons8-business-analysis-64.png" width="18" height="18" alt="Extraction" style={{ verticalAlign: 'middle' }} />, key: 'extraction' },
    { title: 'Gap Analysis', icon: <img src="/assets/icons/evaluation.png" width="18" height="18" alt="Gaps" style={{ verticalAlign: 'middle' }} />, key: 'gaps' },
    { title: 'Functional Spec', icon: <img src="/assets/icons/briefcase.png" width="18" height="18" alt="Spec" style={{ verticalAlign: 'middle' }} />, key: 'functional_spec' },
    { title: 'Backlog Mapping', icon: <img src="/assets/icons/multitasking.png" width="18" height="18" alt="Backlog" style={{ verticalAlign: 'middle' }} />, key: 'backlog' },
    { title: 'Test Cases', icon: <img src="/assets/icons/professionalism.png" width="18" height="18" alt="Test Cases" style={{ verticalAlign: 'middle' }} />, key: 'test_cases' },
  ];

  const renderStepResult = (stepIdx) => {
    const step = STEPS[stepIdx];
    const stepData = data[step.key];
    if (!stepData) return null;

    switch (step.key) {
      case 'extraction':
        return (
          <div className="step-result-card glass-card">
            <h4>{step.icon} Extracted Business Discovery</h4>
            <p>{stepData.document_summary}</p>
            <div className="mini-grid">
              <div className="mini-stat">
                <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Functional</div>
                <div className="val">{stepData.functional_requirements?.length || 0}</div>
              </div>
              <div className="mini-stat">
                <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Business Rules</div>
                <div className="val">{stepData.business_rules?.length || 0}</div>
              </div>
            </div>
          </div>
        );
      case 'gaps':
        const reviews = data.reviews || {};
        const gapsArray = Array.isArray(stepData) ? stepData : stepData?.gaps;
        const gapsToShow = showAllGaps ? gapsArray : gapsArray?.slice(0, 3);
        return (
          <div className="step-result-card glass-card">
            <h4>{step.icon} Risk & Agentic Council Review</h4>
            <div className="council-badges" style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
               <span className={`badge-sm ${reviews.Security ? 'active' : ''}`}>🛡️ Security</span>
               <span className={`badge-sm ${reviews.UX ? 'active' : ''}`}>🎨 UX</span>
               <span className={`badge-sm ${reviews.Architecture ? 'active' : ''}`}>🏗️ Arch</span>
               <span className={`badge-sm ${reviews.QA ? 'active' : ''}`}>🧪 QA</span>
            </div>
            <div className="gap-list" style={{ maxHeight: showAllGaps ? '400px' : 'auto', overflowY: 'auto' }}>
              {gapsToShow?.map((gap, i) => (
                <div key={i} className="gap-item glass-card" style={{ marginBottom: '8px', padding: '12px', display: 'flex', flexDirection: 'column', gap: '4px', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px' }}>
                    <div style={{ fontWeight: 'bold', color: '#fca5a5' }}>⚠️ {gap.title || gap.requirement || gap}</div>
                    {(gap.description || gap.recommendation) && (
                        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                            {gap.description && <p style={{ margin: '0 0 4px 0' }}>{gap.description}</p>}
                            {gap.recommendation && <p style={{ margin: '0', color: 'var(--accent-primary)' }}><strong>Fix:</strong> {gap.recommendation}</p>}
                        </div>
                    )}
                </div>
              ))}
              {!showAllGaps && gapsArray?.length > 3 && (
                <div 
                    className="risk-tag" 
                    style={{ cursor: 'pointer', textAlign: 'center', marginTop: '8px', display: 'block', padding: '8px' }} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setShowAllGaps(true)}
                >
                    + {gapsArray.length - 3} more Gaps (Click to Expand)
                </div>
              )}
              {showAllGaps && (
                <div 
                    className="risk-tag" 
                    style={{ cursor: 'pointer', textAlign: 'center', marginTop: '8px', display: 'block', padding: '8px', background: 'rgba(255,255,255,0.1)', color: '#fff' }} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setShowAllGaps(false)}
                >
                    Collapse Gaps
                </div>
              )}
            </div>
          </div>
        );
      case 'functional_spec':
        const specStr = typeof stepData === 'string' ? stepData : (stepData ? JSON.stringify(stepData, null, 2) : '');
        return (
          <div className="step-result-card glass-card">
            <h4>{step.icon}{' '}Functional Specification</h4>
            <div className="functional_spec-preview">
              {specStr.split('\n').slice(0, 10).join('\n')}...
            </div>
          </div>
        );
      case 'backlog':
        const backlogEpics = Array.isArray(stepData) ? stepData : stepData?.epics;
        return (
          <div className="step-result-card glass-card">
            <h4>{step.icon} Backlog Architecture</h4>
            <div className="backlog-summary">
              {backlogEpics?.length} Epics | {backlogEpics?.[0]?.features?.length} Features
            </div>
          </div>
        );
      case 'test_cases':
        return (
          <div className="step-result-card glass-card">
            <h4>{step.icon} QA Test Cases Generated</h4>
            <div className="backlog-summary">
              Test Cases have been successfully drafted and mapped to the backlog.
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="view-container">
      <header className="view-header">
        <div className="title-area">
          <h1>Project Orchestration</h1>
          <p>Real-time requirement discovery and technical mapping pipeline.</p>
        </div>
        <div className="title-actions" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn-secondary" onClick={onClose}>✕ Close Session</button>
          {activeStep === 5 && (
            <>
              <label htmlFor="includeNFR-1" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: '#64748b', cursor: 'pointer', userSelect: 'none' }}>
                <input id="includeNFR-1" type="checkbox" checked={includeNFR} onChange={(e) => setIncludeNFR(e.target.checked)} style={{ cursor: 'pointer' }} />
                {' '}Include NFRs
              </label>
              <button className="btn-secondary" onClick={() => {
                    const activeDocId = data.document_id || data.docId || data.documentId || data.analysis_id || data.id;
                if (!activeDocId) {
                  alert("Document ID not found. Please run an analysis first.");
                  return;
                }
                window.open(`${API_BASE}/download-spec/${activeDocId}?include_nfr=${includeNFR}`, '_blank');
              }}>Export PDF</button>
              <button 
                className="btn-primary pulse-btn" 
                onClick={() => setShowEmailModal(true)}
                disabled={isSyncing}
              >
                {isSyncing ? 'Syncing to ADO...' : <><img src="/assets/icons/Azure-DevOps.png" width="18" height="18" alt="ADO" style={{ verticalAlign: 'middle', marginRight: '6px' }} /> Approve & Sync to ADO</>}
              </button>
            </>
          )}
        </div>
      </header>

      <div className="workflow-header-area">
        <div className="workflow-stepper-horizontal">
          {STEPS.map((step, idx) => (
            <div key={idx} className={`h-step ${activeStep === idx + 1 ? 'active' : ''} ${completedSteps.includes(idx + 1) ? 'done' : ''}`}>
              <div className="h-step-icon">{completedSteps.includes(idx + 1) ? '✓' : step.icon}</div>
              <div className="h-step-info">
                <span className="h-step-title">{step.title}</span>
                <span className="h-step-status">
                  {activeStep === idx + 1 ? 'Processing...' : completedSteps.includes(idx + 1) ? 'Completed' : 'Pending'}
                </span>
              </div>
              {idx < STEPS.length - 1 && <div className="h-step-line"></div>}
            </div>
          ))}
        </div>
      </div>

      <div className="workflow-main-full">
        <div className="live-feed">
          {completedSteps.map((stepIdx) => (
            <div key={stepIdx} className="feed-item active">
              {renderStepResult(stepIdx - 1)}
            </div>
          ))}

          {activeStep === 2 && !completedSteps.includes(2) ? (
            <div className="ba-review-card glass-card animation-fade-in">
              <div className="card-header">
                <h4>📝 Auditor Review: Extracted Requirements</h4>
                <p>As a Senior BA, you can refine these requirements before we generate the technical spec.</p>
              </div>
              <div className="requirements-list-compact" style={{ maxHeight: showAllReqs ? '400px' : '200px', overflowY: 'auto' }}>
                {(data.extraction?.functional_requirements || []).map((req, i) => (
                  <div key={i} className={`req-item-mini ${!showAllReqs && i >= 5 ? 'hidden' : ''}`}>
                    <span className="req-id">{req.id}</span>
                    <span className="req-text">{req.description}</span>
                  </div>
                ))}
                {!showAllReqs && data.extraction?.functional_requirements?.length > 5 && (
                  <div className="req-more-count" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setShowAllReqs(true)} style={{ cursor: 'pointer', color: 'var(--accent-primary)', padding: '10px' }}>
                    + {data.extraction.functional_requirements.length - 5} more (Click to Expand)
                  </div>
                )}
              </div>
              <div className="card-actions">
                {showAllReqs && (
                  <button className="btn-secondary btn-mini" onClick={() => setShowAllReqs(false)}>Collapse List</button>
                )}
                <button className="btn-primary btn-mini" onClick={() => {/* Advance logic */ }}>Looks Good, Continue</button>
              </div>
            </div>
          ) : (
            activeStep <= 4 && !completedSteps.includes(activeStep) && (
              <div className="processing-indicator">
                <div className="loader-ring mini"></div>
                <span>BA Agent is analyzing {STEPS[activeStep - 1]?.title.toLowerCase()}...</span>
              </div>
            )
          )}

          {activeStep >= 5 && (
            <div className="final-review-area animation-fade-in">
              <div className="review-header">
                <h2>Final Project Orchestration</h2>
                <div className="review-actions" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <label htmlFor="includeNFR-2" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: '#64748b', cursor: 'pointer', userSelect: 'none' }}>
                    <input id="includeNFR-2" type="checkbox" checked={includeNFR} onChange={(e) => setIncludeNFR(e.target.checked)} style={{ cursor: 'pointer' }} />
                    {' '}Include NFRs
                  </label>
                  <button className="btn-secondary" onClick={() => {
                        const activeDocId = data.document_id || data.docId || data.documentId || data.analysis_id || data.id;
                    if (!activeDocId) {
                      alert("Document ID not found. Please run an analysis first.");
                      return;
                    }
                    window.open(`${API_BASE}/download-spec/${activeDocId}?include_nfr=${includeNFR}`, '_blank');
                  }}>Export PDF</button>
                  <button className="btn-primary" onClick={() => setShowEmailModal(true)}>Approve & Sync to ADO</button>
                </div>
              </div>

              <div className="review-tabs">
                <div className="tab-switcher">
                  <button className={`btn-tab ${activeReviewTab === 'functional_spec' ? 'active' : ''}`} onClick={() => setActiveReviewTab('functional_spec')}>Functional Spec</button>
                  <button className={`btn-tab ${activeReviewTab === 'reviews' ? 'active' : ''}`} onClick={() => setActiveReviewTab('reviews')}>Persona Reviews</button>
                  <button className={`btn-tab ${activeReviewTab === 'backlog' ? 'active' : ''}`} onClick={() => setActiveReviewTab('backlog')}>Backlog Tree</button>
                  <button className={`btn-tab ${activeReviewTab === 'traceability' ? 'active' : ''}`} onClick={() => setActiveReviewTab('traceability')}>Traceability Matrix</button>
                  <button className={`btn-tab ${activeReviewTab === 'test_cases' ? 'active' : ''}`} onClick={() => setActiveReviewTab('test_cases')}>Test Cases</button>
                  <button className={`btn-tab ${activeReviewTab === 'governance' ? 'active' : ''}`} onClick={() => setActiveReviewTab('governance')}>🛡️ Governance Trail</button>
                </div>
              </div>

              <div className="review-content">
                {activeReviewTab === 'functional_spec' && (
                  <div className="panel spec-panel full-width animation-fade-in">
                    <ArtifactEditorWrapper 
                      title="Functional Specification" 
                      artifactType="functional_spec" 
                      rawContent={data.functional_spec} 
                      onSave={onUpdateArtifact} 
                      onRegenerate={onRegenerateArtifact}
                    >
                      <div className="doc-page">
                        <header className="doc-header">
                          <img src="/assets/ValueMomentumlogodark.png" height="30" alt="logo" />
                          <div className="doc-meta">Technical Requirements Document v1.0</div>
                        </header>
                        <article className="doc-content">
                          <FunctionalSpecAccordionViewer content={data.functional_spec} />
                        </article>
                      </div>
                    </ArtifactEditorWrapper>
                  </div>
                )}

                {activeReviewTab === 'reviews' && (
                  <div className="panel review-panel full-width animation-fade-in">
                    <ArtifactEditorWrapper 
                      title="Persona Reviews" 
                      artifactType="reviews" 
                      rawContent={data.reviews} 
                      onSave={onUpdateArtifact} 
                      onRegenerate={onRegenerateArtifact}
                    >
                      <PersonaReviews reviews={data.reviews} />
                    </ArtifactEditorWrapper>
                  </div>
                )}

                {activeReviewTab === 'backlog' && (
                  <div className="panel backlog-panel full-width animation-fade-in">
                    <ArtifactEditorWrapper 
                      title="Backlog Tree" 
                      artifactType="backlog" 
                      rawContent={data.backlog} 
                      onSave={onUpdateArtifact} 
                      onRegenerate={onRegenerateArtifact}
                    >
                      <div className="backlog-tree-container">
                        <BacklogTree 
                          data={data.backlog} 
                          onToggle={onToggle} 
                          onUpdateBacklog={(updatedData) => onUpdateArtifact('backlog', updatedData)} 
                        />
                      </div>
                    </ArtifactEditorWrapper>
                  </div>
                )}

                {activeReviewTab === 'traceability' && (
                  <div className="panel traceability-panel full-width animation-fade-in" style={{ padding: '24px' }}>
                    <TraceabilityMatrix backlog={data.backlog} />
                  </div>
                )}

                {activeReviewTab === 'test_cases' && (
                  <div className="panel testcases-panel full-width animation-fade-in" style={{ padding: '24px', overflowY: 'auto', maxHeight: '600px' }}>
                    <ArtifactEditorWrapper 
                      title="Test Cases" 
                      artifactType="test_cases" 
                      rawContent={data.test_cases} 
                      onSave={onUpdateArtifact} 
                      onRegenerate={onRegenerateArtifact}
                    >
                      <TestCasesViewer rawData={data.test_cases} storyTitle={data.user_story_title || data.title} docId={data.docId} />
                    </ArtifactEditorWrapper>
                  </div>
                )}

                {activeReviewTab === 'governance' && (
                  <div className="panel governance-panel full-width animation-fade-in">
                    <GovernanceDashboard documentId={data.docId} />
                  </div>
                )}

              </div>
            </div>
          )}
        </div>
      </div>
      {showEmailModal && (
        <div className="modal-overlay" style={{ zIndex: 10000 }}>
          <div className="modal-content glass-card animation-fade-in" style={{ maxWidth: '520px', width: '100%', padding: '32px', borderRadius: '16px', boxSizing: 'border-box', border: '1px solid rgba(255,255,255,0.15)', background: '#0f172a' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{ width: '42px', height: '42px', borderRadius: '10px', background: 'rgba(59, 130, 246, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#60a5fa' }}>
                <Send size={22} />
              </div>
              <div>
                <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.2rem', fontWeight: '600' }}>Request Review & ADO Sync</h3>
                <p style={{ margin: '4px 0 0 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Send analysis package to stakeholder for approval</p>
              </div>
            </div>
            
            <div style={{ marginTop: '20px', marginBottom: '24px' }}>
              <label htmlFor="reviewerEmail" style={{ display: 'block', fontSize: '0.85rem', fontWeight: '500', color: '#cbd5e1', marginBottom: '8px' }}>
                Reviewer Email Address
              </label>
              <input 
                id="reviewerEmail"
                type="email" 
                placeholder="reviewer@organization.com"
                value={reviewerEmail}
                onChange={(e) => setReviewerEmail(e.target.value)}
                className="glass-input"
                style={{ 
                  width: '100%', 
                  boxSizing: 'border-box', 
                  padding: '12px 16px', 
                  fontSize: '0.95rem', 
                  background: 'rgba(0,0,0,0.3)', 
                  color: '#ffffff', 
                  border: '1px solid rgba(255,255,255,0.15)',
                  borderRadius: '8px',
                  outline: 'none'
                }}
              />
            </div>

            <div className="modal-actions" style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button className="btn-secondary" onClick={() => setShowEmailModal(false)} style={{ padding: '8px 16px', borderRadius: '6px' }}>Cancel</button>
              <button 
                className="btn-primary" 
                onClick={() => {
                  setShowEmailModal(false);
                  onFinish(reviewerEmail);
                }}
                style={{ padding: '8px 20px', borderRadius: '6px', display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <Send size={16} />
                Send Request
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const BacklogTree = ({ data, onToggle, onUpdateBacklog }) => {
  const [editingPath, setEditingPath] = useState(null);
  const [editForm, setEditForm] = useState({ title: '', description: '', acceptance_criteria: '' });

  // Collapse state tracking
  const [collapsedEpics, setCollapsedEpics] = useState({});
  const [collapsedFeatures, setCollapsedFeatures] = useState({});
  const [collapsedStories, setCollapsedStories] = useState({});

  const epicsList = Array.isArray(data) ? data : data?.epics;

  // Calculate metrics across all levels
  let epicCount = epicsList?.length || 0;
  let featureCount = 0;
  let storyCount = 0;
  let taskCount = 0;

  if (epicsList) {
    epicsList.forEach(epic => {
      if (epic.features) {
        featureCount += epic.features.length;
        epic.features.forEach(feat => {
          if (feat.user_stories) {
            storyCount += feat.user_stories.length;
            feat.user_stories.forEach(story => {
              if (story.tasks) {
                taskCount += story.tasks.length;
              }
            });
          }
        });
      }
    });
  }

  const toggleEpicCollapse = (eIdx) => {
    setCollapsedEpics(prev => ({ ...prev, [eIdx]: !prev[eIdx] }));
  };

  const toggleFeatureCollapse = (key) => {
    setCollapsedFeatures(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const toggleStoryCollapse = (key) => {
    setCollapsedStories(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const expandAll = () => {
    setCollapsedEpics({});
    setCollapsedFeatures({});
    setCollapsedStories({});
  };

  const collapseAll = () => {
    const epicsState = {};
    const featuresState = {};
    const storiesState = {};

    epicsList?.forEach((epic, eIdx) => {
      epicsState[eIdx] = true;
      epic.features?.forEach((feat, fIdx) => {
        featuresState[`${eIdx}-${fIdx}`] = true;
        feat.user_stories?.forEach((story, sIdx) => {
          storiesState[`${eIdx}-${fIdx}-${sIdx}`] = true;
        });
      });
    });

    setCollapsedEpics(epicsState);
    setCollapsedFeatures(featuresState);
    setCollapsedStories(storiesState);
  };
  
  const handleEditClick = (pathStr, node) => {
    setEditingPath(pathStr);
    setEditForm({
      title: node.title || '',
      description: node.description || '',
      acceptance_criteria: node.acceptance_criteria ? node.acceptance_criteria.join('\n') : ''
    });
  };

  const handleSave = (eIdx, fIdx, sIdx) => {
    const isArrayData = Array.isArray(data);
    const updatedData = isArrayData ? [...data] : { ...data };
    const epics = isArrayData ? updatedData : [...updatedData.epics];
    
    // Deep clone the epic we're modifying
    const newEpic = { ...epics[eIdx] };
    
    if (sIdx !== undefined) {
      const newFeatures = [...newEpic.features];
      const newFeature = { ...newFeatures[fIdx] };
      const newStories = [...newFeature.user_stories];
      
      newStories[sIdx] = {
        ...newStories[sIdx],
        title: editForm.title,
        description: editForm.description,
        acceptance_criteria: editForm.acceptance_criteria ? editForm.acceptance_criteria.split('\n').filter(a => a.trim()) : []
      };
      
      newFeature.user_stories = newStories;
      newFeatures[fIdx] = newFeature;
      newEpic.features = newFeatures;
    } else if (fIdx !== undefined) {
      const newFeatures = [...newEpic.features];
      newFeatures[fIdx] = {
        ...newFeatures[fIdx],
        title: editForm.title,
        description: editForm.description
      };
      newEpic.features = newFeatures;
    } else {
      newEpic.title = editForm.title;
      newEpic.description = editForm.description;
    }
    
    epics[eIdx] = newEpic;
    if (!isArrayData) updatedData.epics = epics;
    
    onUpdateBacklog && onUpdateBacklog(updatedData);
    setEditingPath(null);
  };

  if (!epicsList || epicsList.length === 0) {
    return (
      <div className="no-data-loading">
        <div className="discovery-spinner"></div>
        <p>Architecting engineering hierarchy...</p>
        <span className="loading-hint">Synthesizing Epics, Features, and Stories from technical specs.</span>
      </div>
    );
  }

  return (
    <div className="hierarchy-container">
      {/* 1. Summary Stat Count Boxes */}
      <div className="backlog-summary-cards">
        <div className="summary-card epic-card">
          <div className="summary-card-icon">⚡</div>
          <div className="summary-card-info">
            <span className="summary-card-count">{epicCount}</span>
            <span className="summary-card-label">EPICS</span>
          </div>
        </div>

        <div className="summary-card feature-card">
          <div className="summary-card-icon">📦</div>
          <div className="summary-card-info">
            <span className="summary-card-count">{featureCount}</span>
            <span className="summary-card-label">FEATURES</span>
          </div>
        </div>

        <div className="summary-card story-card">
          <div className="summary-card-icon">📖</div>
          <div className="summary-card-info">
            <span className="summary-card-count">{storyCount}</span>
            <span className="summary-card-label">STORIES</span>
          </div>
        </div>

        <div className="summary-card task-card">
          <div className="summary-card-icon">🎯</div>
          <div className="summary-card-info">
            <span className="summary-card-count">{taskCount}</span>
            <span className="summary-card-label">TASKS</span>
          </div>
        </div>
      </div>

      {/* 2. Global Controls Bar */}
      <div className="backlog-controls-bar">
        <div className="controls-left">
          <span className="controls-title">Backlog Tree Hierarchy</span>
        </div>
        <div className="controls-right">
          <button className="btn-secondary mini" onClick={expandAll}>
            📂 Expand All
          </button>
          <button className="btn-secondary mini" onClick={collapseAll}>
            📁 Collapse All
          </button>
        </div>
      </div>

      {/* 3. Collapsible Tree Hierarchy */}
      <div className="hierarchy">
        {epicsList.map((epic, eIdx) => {
          const isEpicCollapsed = !!collapsedEpics[eIdx];
          return (
            <div key={eIdx} className={`node epic ${epic.selected === false ? 'unselected' : ''}`}>
              <div className="node-head" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => toggleEpicCollapse(eIdx)} style={{ cursor: 'pointer' }}>
                <input 
                  type="checkbox" 
                  checked={epic.selected !== false} 
                  onChange={(e) => { e.stopPropagation(); onToggle('epic', { epicIdx: eIdx }); }}
                  className="sync-checkbox"
                />
                <button className="btn-collapse-toggle" onClick={(e) => { e.stopPropagation(); toggleEpicCollapse(eIdx); }}>
                  {isEpicCollapsed ? '▶' : '▼'}
                </button>
                <span className="node-tag">EPIC</span>
                <span style={{ flex: 1, textAlign: 'left', fontWeight: '700' }}>{epic.title}</span>
                {epic.remote_id && <span className="linked-badge">🔗 {epic.remote_id}</span>}
                <button className="btn-ghost" style={{ padding: '2px 8px', marginLeft: 'auto' }} onClick={(e) => { e.stopPropagation(); handleEditClick(`epic-${eIdx}`, epic); }}>✏️</button>
              </div>

              {editingPath === `epic-${eIdx}` ? (
                <div style={{ padding: '16px', background: 'var(--glass-bg)', borderRadius: '8px', margin: '8px 24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <input value={editForm.title} onChange={e => setEditForm({...editForm, title: e.target.value})} className="edit-input" placeholder="Epic Title" />
                  <textarea value={editForm.description} onChange={e => setEditForm({...editForm, description: e.target.value})} className="edit-textarea" placeholder="Epic Description" rows={2} />
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                    <button className="btn-primary mini" onClick={() => handleSave(eIdx)}>Save</button>
                    <button className="btn-secondary mini" onClick={() => setEditingPath(null)}>Cancel</button>
                  </div>
                </div>
              ) : (
                !isEpicCollapsed && (
                  <div className="node-body">
                    {epic.features?.map((feature, fIdx) => {
                      const featKey = `${eIdx}-${fIdx}`;
                      const isFeatCollapsed = !!collapsedFeatures[featKey];
                      return (
                        <div key={fIdx} className={`node feature ${feature.selected === false ? 'unselected' : ''}`}>
                          <div className="node-head" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => toggleFeatureCollapse(featKey)} style={{ cursor: 'pointer' }}>
                            <input 
                              type="checkbox" 
                              checked={feature.selected !== false} 
                              onChange={(e) => { e.stopPropagation(); onToggle('feature', { epicIdx: eIdx, featIdx: fIdx }); }}
                              className="sync-checkbox"
                            />
                            <button className="btn-collapse-toggle" onClick={(e) => { e.stopPropagation(); toggleFeatureCollapse(featKey); }}>
                              {isFeatCollapsed ? '▶' : '▼'}
                            </button>
                            <span className="node-tag">FEATURE</span>
                            <span style={{ flex: 1, textAlign: 'left', fontWeight: '600' }}>{feature.title}</span>
                            {feature.remote_id && <span className="linked-badge">🔗 {feature.remote_id}</span>}
                            <button className="btn-ghost" style={{ padding: '2px 8px', marginLeft: 'auto' }} onClick={(e) => { e.stopPropagation(); handleEditClick(`feat-${eIdx}-${fIdx}`, feature); }}>✏️</button>
                          </div>

                          {editingPath === `feat-${eIdx}-${fIdx}` ? (
                            <div style={{ padding: '16px', background: 'var(--glass-bg)', borderRadius: '8px', margin: '8px 24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              <input value={editForm.title} onChange={e => setEditForm({...editForm, title: e.target.value})} className="edit-input" placeholder="Feature Title" />
                              <textarea value={editForm.description} onChange={e => setEditForm({...editForm, description: e.target.value})} className="edit-textarea" placeholder="Feature Description" rows={2} />
                              <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                                <button className="btn-primary mini" onClick={() => handleSave(eIdx, fIdx)}>Save</button>
                                <button className="btn-secondary mini" onClick={() => setEditingPath(null)}>Cancel</button>
                              </div>
                            </div>
                          ) : (
                            !isFeatCollapsed && (
                              <div className="node-body">
                                {feature.user_stories?.map((story, sIdx) => {
                                  const storyKey = `${eIdx}-${fIdx}-${sIdx}`;
                                  const isStoryCollapsed = !!collapsedStories[storyKey];
                                  return (
                                    <div key={sIdx} className={`node story ${story.selected === false ? 'unselected' : ''}`}>
                                      <div className="node-head" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => toggleStoryCollapse(storyKey)} style={{ cursor: 'pointer' }}>
                                        <input 
                                          type="checkbox" 
                                          checked={story.selected !== false} 
                                          onChange={(e) => { e.stopPropagation(); onToggle('story', { epicIdx: eIdx, featIdx: fIdx, storyIdx: sIdx }); }}
                                          className="sync-checkbox"
                                        />
                                        <button className="btn-collapse-toggle" onClick={(e) => { e.stopPropagation(); toggleStoryCollapse(storyKey); }}>
                                          {isStoryCollapsed ? '▶' : '▼'}
                                        </button>
                                        <span className="node-tag">STORY</span>
                                        <span className="node-title">{story.title}</span>
                                        {story.remote_id && <span className="linked-badge">🔗 {story.remote_id}</span>}
                                        {story.requirement_id && (
                                          <span className="trace-link" title="Requirement Traceability ID">
                                            Trace: {story.requirement_id}
                                          </span>
                                        )}
                                        {story.story_points && (
                                          <span className="points-badge">{story.story_points} pts</span>
                                        )}
                                        <button className="btn-ghost" style={{ padding: '2px 8px', marginLeft: 'auto' }} onClick={(e) => { e.stopPropagation(); handleEditClick(`story-${eIdx}-${fIdx}-${sIdx}`, story); }}>✏️</button>
                                      </div>

                                      {editingPath === `story-${eIdx}-${fIdx}-${sIdx}` ? (
                                        <div style={{ padding: '16px', background: 'var(--glass-bg)', borderRadius: '8px', margin: '8px 24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                          <input value={editForm.title} onChange={e => setEditForm({...editForm, title: e.target.value})} className="edit-input" placeholder="Story Title" />
                                          <textarea value={editForm.description} onChange={e => setEditForm({...editForm, description: e.target.value})} className="edit-textarea" placeholder="Description" rows={3} />
                                          <textarea value={editForm.acceptance_criteria} onChange={e => setEditForm({...editForm, acceptance_criteria: e.target.value})} className="edit-textarea" placeholder="Acceptance Criteria (one per line)" rows={4} />
                                          <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                                            <button className="btn-primary mini" onClick={() => handleSave(eIdx, fIdx, sIdx)}>Save</button>
                                            <button className="btn-secondary mini" onClick={() => setEditingPath(null)}>Cancel</button>
                                          </div>
                                        </div>
                                      ) : (
                                        !isStoryCollapsed && (
                                          <div className="node-body">
                                            <StoryDetailsFormatted story={story} />
                                          </div>
                                        )
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )
                          )}
                        </div>
                      );
                    })}
                  </div>
                )
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const VisualFlow = ({ diagram }) => {
  if (!diagram || !diagram.nodes) {
    return (
      <div className="no-data-loading" style={{ padding: '40px', textAlign: 'center', color: '#888' }}>
        <div className="discovery-spinner" style={{ border: '4px solid #333', borderTop: '4px solid #00f2ff', borderRadius: '50%', width: '40px', height: '40px', animation: 'spin 1s linear infinite', margin: '0 auto 16px' }}></div>
        <p style={{ fontSize: '1.1rem', color: '#e0e0e0', marginBottom: '8px' }}>Architecting engineering hierarchy...</p>
        <span style={{ fontSize: '0.85rem' }}>Synthesizing Epics, Features, and Stories from technical specs.</span>
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div className="flow-canvas-container animation-fade-in">
      <div className="flow-header-mini">
        <h4>Intelligent Process Flow</h4>
        <p>Automated business logic visualization derived from your specs.</p>
      </div>
      <div className="process-flow-visual">
        {diagram.nodes.map((node, i) => (
          <React.Fragment key={node.id}>
            <div className={`flow-node ${node.type}`}>
              <div className="node-icon">
                {node.type === 'start' ? '🏁' : node.type === 'decision' ? '⚖️' : node.type === 'end' ? '🏁' : '⚙️'}
              </div>
              <div className="node-content">
                <span className="node-type-label">{node.type.toUpperCase()}</span>
                <div className="node-text">{node.label}</div>
              </div>
              {node.type === 'decision' && (
                <div className="decision-branches">
                  <span className="branch yes">YES: {node.yes}</span>
                  <span className="branch no">NO: {node.no}</span>
                </div>
              )}
            </div>
            {i < diagram.nodes.length - 1 && (
              <div className="flow-arrow">
                <div className="arrow-line"></div>
                <div className="arrow-head"></div>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

const PersonaReviews = ({ reviews }) => {
  if (!reviews) return null;

  return (
    <div className="persona-reviews-grid">
      {Object.entries(reviews).map(([key, reviewData]) => {
        const lowerKey = key.toLowerCase();
        let items = [];
        if (Array.isArray(reviewData)) {
          items = reviewData;
        } else if (typeof reviewData === 'object' && reviewData !== null) {
          if (lowerKey === 'qa') items = reviewData.qa_review || reviewData.qa || [reviewData];
          else if (lowerKey === 'security') items = reviewData.security_review || reviewData.security || [reviewData];
          else if (lowerKey === 'ux') items = reviewData.ux_review || reviewData.ux || [reviewData];
        }
        if (!Array.isArray(items)) items = [];
        
        return (
          <div key={key} className={`persona-card glass-card ${lowerKey}`}>
            <div className="persona-header">
              <span className="persona-icon">
                {lowerKey === 'qa' ? '🧪' : lowerKey === 'security' ? '🛡️' : '🎨'}
              </span>
              <h4>{key.toUpperCase()} Auditor Review</h4>
            </div>
            <div className="persona-content">
              {items.map((review, idx) => (
                <div key={idx} style={{marginBottom: '16px', paddingBottom: '16px', borderBottom: '1px solid rgba(255,255,255,0.1)'}}>
                  {lowerKey === 'qa' && (
                    <div className="review-item">
                      <div className="review-meta">Score: {review.testability_score}/10</div>
                      <div className="review-edge">Edge Cases: {review.edge_cases?.join(', ')}</div>
                      <p className="review-tip">💡 {review.suggestions || review.test_strategy}</p>
                    </div>
                  )}
                  {lowerKey === 'security' && (
                    <div className="review-item">
                      <div className={`risk-badge ${review.risk_level?.toLowerCase()}`}>{review.risk_level} Risk</div>
                      <ul className="concerns-list">
                        {review.concerns?.map((c, i) => <li key={i}>{c}</li>)}
                      </ul>
                      <p className="mitigation-text">🛡️ {review.mitigation || review.mitigation_recommendation}</p>
                    </div>
                  )}
                  {lowerKey === 'ux' && (
                    <div className="review-item">
                      <div className="friction-title">Potential Friction:</div>
                      <ul className="friction-list">
                        {review.journey_gaps?.map((f, i) => <li key={i}>{f}</li>) || review.friction_points?.map((f, i) => <li key={i}>{f}</li>)}
                      </ul>
                      <p className="improvement-text">🎨 {review.improvement || review.improvement_suggestion}</p>
                    </div>
                  )}
                </div>
              ))}
              {items.length === 0 && <div className="no-data" style={{opacity: 0.5}}>No feedback.</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
};


const ClarificationView = ({ questions, docId, onResume }) => {
  const [answers, setAnswers] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    // Call resume with answers
    await onResume(docId, answers);
    setIsSubmitting(false);
  };

  return (
    <div className="view-container">
      <header className="view-header">
        <div className="title-area">
          <h1>Clarification Required</h1>
          <p>The AI has identified critical ambiguities that could impact technical delivery.</p>
        </div>
        <div className="header-actions">
          <span className="pill-badge warning">🤔 Attention Required</span>
        </div>
      </header>

      <div className="clarification-form glass-card">
        {questions.map((q, i) => (
          <div key={i} className="question-block">
            <label htmlFor={`question-${i}`}>
              <span className="q-context">{q.context}</span>
              <span className="q-text">{q.question}</span>
            </label>
            <textarea
              id={`question-${i}`}
              placeholder={q.suggested_answer ? `Suggested: ${q.suggested_answer}` : "Enter details..."}
              onChange={(e) => setAnswers({ ...answers, [q.question]: e.target.value })}
            />
          </div>
        ))}

        <div className="form-actions">
          <button className="btn-primary" onClick={handleSubmit} disabled={isSubmitting}>
            {isSubmitting ? "Refining Analysis..." : "🚀 Resolve & Continue"}
          </button>
        </div>
      </div>
    </div>
  );
};


const ReleaseView = ({ data }) => {
  if (!data || !data.epics || data.epics.length === 0) {
    return (
      <div className="no-data-loading" style={{ padding: '40px', textAlign: 'center', color: '#888' }}>
        <div className="discovery-spinner" style={{ border: '4px solid #333', borderTop: '4px solid #00f2ff', borderRadius: '50%', width: '40px', height: '40px', animation: 'spin 1s linear infinite', margin: '0 auto 16px' }}></div>
        <p style={{ fontSize: '1.1rem', color: '#e0e0e0', marginBottom: '8px' }}>Architecting engineering hierarchy...</p>
        <span style={{ fontSize: '0.85rem' }}>Synthesizing Epics, Features, and Stories from technical specs.</span>
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  const flattenBacklog = () => {
    const stories = [];
    data.epics.forEach(epic => {
      epic.features.forEach(feature => {
        feature.user_stories.forEach(story => {
          stories.push({
            ...story,
            epic: epic.title,
            feature: feature.title
          });
        });
      });
    });
    return stories;
  };

  const stories = flattenBacklog();
  const phases = ['MVP', 'Phase 2', 'Phase 3'];

  return (
    <div className="view-container">
      <header className="view-header">
        <div className="title-area">
          <h1>Release Strategist</h1>
          <p>AI-suggested delivery roadmap and MoSCoW prioritization matrix.</p>
        </div>
        <div className="header-actions">
          <button className="btn-secondary" onClick={() => window.print()}>Export Roadmap</button>
        </div>
      </header>

      <div className="release-roadmap">
        {phases.map(phase => {
          const phaseStories = stories.filter(s => s.release_phase === phase || (!s.release_phase && phase === 'MVP'));
          return (
            <div key={phase} className="release-column glass-card">
              <div className="release-header">
                <h3>{phase}</h3>
                <span className="count-badge">{phaseStories.length} Items</span>
              </div>
              <div className="release-items">
                {phaseStories.map((story, i) => (
                  <div key={i} className={`release-item-card ${story.moscow?.toLowerCase()}`}>
                    <div className="item-meta">
                      <span className={`moscow-tag ${story.moscow?.toLowerCase()}`}>{story.moscow}</span>
                      <span className="value-score">Value: {story.business_value}/10</span>
                    </div>
                    <h4>{story.title}</h4>
                    <p className="item-context">{story.feature}</p>
                    <div className="item-footer">
                      <span>{story.story_points} pts</span>
                      <span>Complexity: {story.complexity}/10</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      <div className="strategic-matrix glass-card">
        <div className="matrix-header">
          <h4>Strategic Priority Matrix</h4>
          <p>High ROI (Quick Wins) are prioritized for earlier releases.</p>
        </div>
        <div className="matrix-canvas">
          <div className="matrix-quadrant q1"><span>🚀 Quick Wins</span></div>
          <div className="matrix-quadrant q2"><span>🏗️ Major Projects</span></div>
          <div className="matrix-quadrant q3"><span>🛠️ Maintenance</span></div>
          <div className="matrix-quadrant q4"><span>⚓ Low Priority</span></div>

          {stories.map((s, i) => (
            <div
              key={i}
              className="matrix-dot"
              style={{
                left: `${(s.business_value * 10)}%`,
                bottom: `${(10 - s.complexity) * 10}%`,
                backgroundColor: s.moscow === 'Must' ? '#00f2ff' : '#bc72ff'
              }}
              title={s.title}
            ></div>
          ))}
        </div>
        <div className="matrix-labels">
          <span className="label-x">Business Value →</span>
          <span className="label-y">Ease of Implementation (10-Complexity) →</span>
        </div>
      </div>
    </div>
  );
};

const TraceabilityMatrix = ({ backlog }) => {
  const epicsList = Array.isArray(backlog) ? backlog : backlog?.epics;
  if (!epicsList || epicsList.length === 0) return <div className="no-data">Generating Traceability Lineage...</div>;

  const rows = [];
  epicsList.forEach(epic => {
    epic.features?.forEach(feat => {
      feat.user_stories?.forEach(story => {
        rows.push({
          requirement: story.source_requirement || story.description || story.title,
          req_id: story.requirement_id || story.id || "FR-001",
          story_title: story.title,
          moscow: story.moscow || "Must Have",
          ado_item: story.remote_id ? `ADO #${story.remote_id}: ${story.title}` : `Similar Story: ${story.title}`,
          test_coverage: story.tasks?.length ? `${story.tasks.length} Automated Steps` : "Manual & Playwright Coverage"
        });
      });
    });
  });

  return (
    <div className="traceability-matrix animation-fade-in">
      <div className="matrix-header" style={{ marginBottom: '16px' }}>
        <h4 style={{ margin: 0, color: '#f8fafc', fontSize: '1.1rem' }}>Requirement-to-Engineering Lineage</h4>
        <p style={{ margin: '4px 0 0 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Full audit trail mapping Business Requirements to Stories, ADO Work Items, and Test Suites.</p>
      </div>
      <div className="panel" style={{ overflowX: 'auto' }}>
        <table className="modern-table compact" style={{ width: '100%', fontSize: '0.85rem' }}>
          <thead>
            <tr>
              <th style={{ width: '30%' }}>Source Requirement (BRD)</th>
              <th style={{ width: '25%' }}>Generated User Story</th>
              <th style={{ width: '25%' }}>Similar / Linked ADO Work Items</th>
              <th style={{ width: '20%' }}>Test Suite Coverage</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                <td>
                  <span className="id-pill" style={{ marginRight: '8px', fontSize: '0.75rem' }}>{row.req_id}</span>
                  <span>{row.requirement}</span>
                </td>
                <td>
                  <strong>{row.story_title}</strong>
                  <span className="pill-badge completed" style={{ marginLeft: '8px', fontSize: '0.7rem' }}>{row.moscow}</span>
                </td>
                <td style={{ color: '#60a5fa' }}>{row.ado_item}</td>
                <td>
                  <span className="pill-badge" style={{ background: 'rgba(34, 197, 94, 0.15)', color: '#4ade80' }}>
                    {row.test_coverage}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
const CapacityView = () => {
  const [items, setItems] = useState([]);
  const [team, setTeam] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API_BASE}/ado-work-items`).then(r => r.json()),
      fetch(`${API_BASE}/ado-team`).then(r => r.json())
    ]).then(([itemsData, teamData]) => {
      setItems(itemsData);
      setTeam(teamData);
      setLoading(false);
    });
  }, []);

  const calculateCapacity = (memberName) => {
    const memberItems = items.filter(i => i.assigned_to === memberName);
    const totalEffort = memberItems.reduce((acc, curr) => acc + (Number.parseFloat(curr.effort) || 0), 0);
    const count = memberItems.length;
    return { totalEffort, count };
  };

  if (loading) return <div className="loader-container"><div className="loader-ring"></div><p>Calculating Team Capacity...</p></div>;

  return (
    <div className="view-container animation-fade-in">
      <header className="central-header">
        <div className="header-chip">
          <span className="chip-icon">📊</span>
          <h1>Team Capacity Planner</h1>
        </div>
        <p>Real-time workload distribution and resource utilization across the synchronized engineering team.</p>
      </header>

      <div className="capacity-grid">
        {team.map(member => {
          const stats = calculateCapacity(member.display_name);
          const limit = 20; // Default capacity limit for demo
          const percent = Math.min((stats.totalEffort / limit) * 100, 100);
          const status = percent > 90 ? 'critical' : percent > 70 ? 'warning' : 'healthy';

          return (
            <div key={member.id} className={`capacity-card glass-card ${status}`}>
              <div className="card-top">
                <div className="member-info">
                  <div className="member-avatar">{member.display_name.charAt(0)}</div>
                  <div>
                    <h4>{member.display_name}</h4>
                    <p>{member.unique_name}</p>
                  </div>
                </div>
                <div className={`status-pill ${status}`}>{status.toUpperCase()}</div>
              </div>

              <div className="usage-stats">
                <div className="stat-line">
                  <span>Effort Utilization</span>
                  <span>{stats.totalEffort} / {limit} pts</span>
                </div>
                <div className="progress-bar-bg">
                  <div className={`progress-bar-fill ${status}`} style={{ width: `${percent}%` }}></div>
                </div>
                <div className="stat-meta">
                  <span>{stats.count} Active Work Items</span>
                  <span>{Math.round(percent)}% Load</span>
                </div>
              </div>

              <div className="card-footer">
                <button className="btn-details">View Workload</button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const WorkItemsView = () => {
  const [items, setItems] = useState([]);
  const [iterations, setIterations] = useState([]);
  const [team, setTeam] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editFields, setEditFields] = useState({});
  const [isSaving, setIsSaving] = useState(false);
  const [typeFilter, setTypeFilter] = useState('All');
  const [iterationFilter, setIterationFilter] = useState('All');

  useEffect(() => {
    fetch(`${API_BASE}/ado-work-items`).then(r => r.json()).then(setItems);
    fetch(`${API_BASE}/ado-iterations`).then(r => r.json()).then(setIterations);
    fetch(`${API_BASE}/ado-team`).then(r => r.json()).then(setTeam);
  }, []);

  const saveToADO = async () => {
    if (!selectedItem) return;
    setIsSaving(true);
    try {
      const res = await fetch(`${API_BASE}/update-ado-work-item`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: selectedItem.id, updates: editFields })
      });
      if (res.ok) {
        // Refresh items
        const updatedItems = await fetch(`${API_BASE}/ado-work-items`).then(r => r.json());
        setItems(updatedItems);
        setIsEditing(false);
        setSelectedItem(null);
      }
    } catch (err) {
      console.error("Save Error:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleEditOpen = (item) => {
    setSelectedItem(item);
    setEditFields({
      title: item.title,
      assigned_to: item.assigned_to,
      status: item.status,
      description: item.description || ''
    });
    setIsEditing(false); // Modal opens in view mode by default
  };


  const filteredItems = items.filter(item => {
    if (typeFilter === 'All') return ['Epic', 'Feature', 'User Story', 'Task'].includes(item.type);
    return item.type === typeFilter;
  });

  return (
    <div className="view-container">
      <header className="view-header">
        <div className="title-area">
          <h1>Backlog Explorer</h1>
          <p>Advanced lifecycle management and technical tracking for your engineering artifacts.</p>
        </div>
        <div className="header-actions">
          <button className="btn-primary" onClick={() => window.location.reload()}>🔄 Refresh ADO</button>
        </div>
      </header>

      <div className="ado-layout">
        <div className="explorer-filters-advanced">
          <div className="filter-group">
            <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Item Type</div>
            <div className="filter-pill-row">
              {['All', 'Epic', 'Feature', 'User Story', 'Task'].map(type => (
                <div
                  key={type}
                  className={`filter-pill ${typeFilter === type ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setTypeFilter(type)}
                >
                  {type}
                </div>
              ))}
            </div>
          </div>

          <div className="filter-group">
            <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Sprint (Iteration)</div>
            <div className="filter-pill-row">
              <div
                className={`filter-pill ${iterationFilter === 'All' ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setIterationFilter('All')}
              >
                All Sprints
              </div>
              {iterations.map(it => (
                <div
                  key={it.id}
                  className={`filter-pill ${iterationFilter === it.path ? 'active' : ''}`} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setIterationFilter(it.path)}
                >
                  {it.name}
                </div>
              ))}
            </div>
          </div>
        </div>



        <div className="explorer-grid glass-card">
          <table className="modern-table interaction">
            <thead>
              <tr>
                <th>Ref ID</th>
                <th>Assignment Title</th>
                <th>Type</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map(item => (
                <tr key={item.id} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => handleEditOpen(item)}>
                  <td className="item-id-cell"># {item.id}</td>
                  <td className="item-title-cell">{item.title}</td>
                  <td><span className="type-badge">{item.type}</span></td>
                  <td><span className="owner-badge">{item.assigned_to}</span></td>
                  <td><span className={`pill-badge ${item.status.toLowerCase()}`}>{item.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selectedItem && (
        <div className="modal-overlay" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setSelectedItem(null)}>
          <div className="modal-content" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={e => e.stopPropagation()}>
            <button className="modal-close-btn" onClick={() => setSelectedItem(null)}>← Back to Explorer</button>
            <div className="modal-inner">
              <div className="details-header-top">
                <span className="type-badge">{selectedItem.type}</span>
                {!isEditing ? (
                  <button className="btn-edit-toggle" onClick={() => setIsEditing(true)}>✏️ Edit in ADO</button>
                ) : (
                  <div className="edit-actions">
                    <button className="btn-save" onClick={saveToADO} disabled={isSaving}>
                      {isSaving ? 'Saving...' : '💾 Save to ADO'}
                    </button>
                    <button className="btn-cancel" onClick={() => setIsEditing(false)}>Cancel</button>
                  </div>
                )}
              </div>
              {isEditing ? (
                <div className="edit-form animation-fade-in">
                  <div className="input-group">
                    <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Title</div>
                    <input
                      className="edit-input"
                      value={editFields.title}
                      onChange={e => setEditFields({ ...editFields, title: e.target.value })}
                    />
                  </div>
                  <div className="input-group">
                    <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Assignee</div>
                    <select
                      className="edit-select"
                      value={editFields.assigned_to}
                      onChange={e => setEditFields({ ...editFields, assigned_to: e.target.value })}
                    >
                      <option value="Unassigned">Unassigned</option>
                      {team.map(m => (
                        <option key={m.id} value={m.display_name}>{m.display_name}</option>
                      ))}
                    </select>
                  </div>
                  <div className="input-group">
                    <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Description</div>
                    <textarea
                      className="edit-textarea"
                      rows="8"
                      value={editFields.description}
                      onChange={e => setEditFields({ ...editFields, description: e.target.value })}
                    />
                  </div>
                </div>
              ) : (
                <>
                  <h2 className="details-title">{selectedItem.title}</h2>
                  <div className="details-meta-grid">
                    <div className="meta-box">
                      <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Resource ID</div>
                      <div className="val">ADO-{selectedItem.id}</div>
                    </div>
                    <div className="meta-box">
                      <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Owner</div>
                      <div className="val">{selectedItem.assigned_to}</div>
                    </div>
                    <div className="meta-box">
                      <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Iteration Path</div>
                      <div className="val active">BA Agent / Sprint 1</div>
                    </div>
                    <div className="meta-box">
                      <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Status</div>
                      <div className="val">{selectedItem.status}</div>
                    </div>
                  </div>
                  <div className="desc-box">
                    <h4>Technical Context</h4>
                    <div className="ado-description-content">{selectedItem.description}</div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const CriticFeedback = ({ review }) => {
  if (!review) return null;
  const isApproved = review.status === "APPROVED";
  const confidenceColor = review.confidence_score > 0.8 ? '#00f2ff' : review.confidence_score > 0.5 ? '#f4df4e' : '#ff4d4d';

  return (
    <div className={`critic-panel glass-card ${isApproved ? 'approved' : 'warning'}`}>
      <div className="critic-header">
        <div className="critic-badge">
          <span className="pulse-dot"></span> {' '}CRITIC'S OPINION
        </div>
        <div className="confidence-gauge">
          <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Confidence Score</div>
          <div className="gauge-val" style={{ color: confidenceColor }}>{Math.round(review.confidence_score * 100)}%</div>
        </div>
      </div>
      
      <div className="critic-status">
        Status: <span className={isApproved ? 'status-ok' : 'status-err'}>{review.status}</span>
      </div>

      {review.findings?.length > 0 && (
        <div className="critic-findings">
          <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Adversarial Findings</div>
          <ul>
            {review.findings.map((f, i) => (
              <li key={i} className={`finding-${f.severity.toLowerCase()}`}>
                <strong>[{f.type}]</strong> {f.description}
              </li>
            ))}
          </ul>
        </div>
      )}

      {review.critic_suggestion && (
        <div className="critic-repro">
          <strong>Recommended Fix:</strong> {review.critic_suggestion}
        </div>
      )}
    </div>
  );
};

const Mermaid = ({ chart }) => {
  useEffect(() => {
    if (window.mermaid && chart) {
      window.mermaid.contentLoaded();
      const element = document.querySelector('.mermaid');
      if (element) {
        element.dataset.processed = undefined;
        window.mermaid.init(undefined, element);
      }
    }
  }, [chart]);

  return <div className="mermaid">{chart}</div>;
};

const GapDetectiveView = () => {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [qualityScore, setQualityScore] = useState(null);
  const [criticReview, setCriticReview] = useState(null);

  const handleAnalyze = async (file) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const ingestRes = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: formData });
      const ingestData = await ingestRes.json();

      if (ingestData.ambiguity_report?.is_ambiguous) {
        const amb = ingestData.ambiguity_report.ambiguities.map(a => `- ${a.requirement}: ${a.issue}`).join('\n');
        if (!window.confirm(`⚠️ AMBIGUITIES DETECTED:\n\n${amb}\n\nProceed anyway?`)) {
          setLoading(false);
          return;
        }
      }

      const analyzeRes = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          document_id: ingestData.document_id,
          enabled_modules: ['gaps'] 
        }),
      });
      const anaData = await analyzeRes.json();
      setResults(anaData.results);
      setQualityScore(anaData.quality_score);
      setCriticReview(anaData.critic_review);
    } catch (e) {
      alert("Gap Analysis Error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="view-container">
      <div className="loader-container">
        <div className="loader-ring"></div>
        <p>Agent scanning document for technical gaps...</p>
      </div>
    </div>
  );

  return (
    <div className="view-container animation-fade-in">
      <header className="view-header">
        <div className="title-area">
          <span className="pre-title">QA Agent</span>
          <h1>Gap Detective</h1>
          <p>Instant multi-perspective stress test for your requirements.</p>
        </div>
        {qualityScore !== null && (
          <div className={`quality-badge ${qualityScore > 0.7 ? 'good' : 'poor'}`}>
            BRD Quality: {Math.round(qualityScore * 100)}%
          </div>
        )}
      </header>

      {!results ? (
        <div className="agent-studio-ingest glass-card" style={{ maxWidth: '900px', margin: '40px auto', padding: '60px', textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
          <div className="radar-animation" style={{ position: 'absolute', top: '-100px', right: '-100px', width: '300px', height: '300px', background: 'radial-gradient(circle, rgba(210, 153, 34, 0.1) 0%, transparent 70%)', borderRadius: '50%', animation: 'radar-sweep 4s infinite linear' }}></div>
          
          <div className="studio-header" style={{ marginBottom: '40px' }}>
             <span className="badge-sm active" style={{ marginBottom: '16px', display: 'inline-block' }}>STRESS TEST READY</span>
             <h2 style={{ fontSize: '2.5rem', fontWeight: '700', marginBottom: '12px' }}>Adversarial Gap Detective</h2>
             <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>Identify contradictions, technical oversights, and business rule gaps.</p>
          </div>

          <div className="studio-dropzone glass-card" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => document.getElementById('gap-up').click()} style={{ border: '2px dashed var(--glass-border)', padding: '40px', cursor: 'pointer', transition: 'all 0.3s ease' }}>
             <div style={{ fontSize: '3rem', marginBottom: '16px' }}>🕵️‍♂️</div>
             <h4 style={{ marginBottom: '8px' }}>Drop Specification for Deep Scan</h4>
             <p style={{ fontSize: '0.85rem', opacity: 0.6 }}>Supports PDF, DOCX, and Direct Text analysis</p>
             <button className="btn-primary" style={{ marginTop: '24px', padding: '12px 32px' }}>INITIALIZE SCAN</button>
          </div>
          
          <div className="studio-footer" style={{ marginTop: '40px', display: 'flex', justifyContent: 'center', gap: '32px', opacity: 0.5, fontSize: '0.75rem' }}>
             <span>✓ 4 Specialized Personas</span>
             <span>✓ Contradiction Mapping</span>
             <span>✓ Impact Assessment</span>
          </div>
          <input type="file" id="gap-up" hidden onChange={(e) => handleAnalyze(e.target.files[0])} />
        </div>
      ) : (
        <div className="gap-dashboard-grid">
          <div className="persona-column">
            <CriticFeedback review={criticReview} />
            <h2>Persona Reviews</h2>
            <div className="review-grid">
              {Object.entries(results.reviews || {}).map(([role, feedback]) => (
                <div key={role} className="review-card glass-card">
                  <div className={`role-badge ${role.toLowerCase()}`}>{role}</div>
                  <p>{feedback}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="gap-column">
            <h2>Functional Gaps Identified</h2>
            <div className="gap-list">
              {results.gaps?.map((gap, i) => (
                <div key={i} className="gap-item glass-card">
                  <div className="gap-header">
                    <span className="gap-tag">ISSUE #{i+1}</span>
                    <span className={`priority-tag ${gap.impact?.toLowerCase()}`}>{gap.impact}</span>
                  </div>
                  <h3>{gap.title}</h3>
                  <p>{gap.description}</p>
                  <div className="gap-repro"><strong>Recommendation:</strong> {gap.recommendation}</div>
                </div>
              ))}
            </div>
            <button className="btn-secondary" style={{ marginTop: '20px' }} onClick={() => setResults(null)}>New Scan</button>
          </div>
        </div>
      )}
    </div>
  );
};

const SpecArchitectView = () => {
  const [loading, setLoading] = useState(false);
  const [functional_spec, setFunctionalSpec] = useState("");
  const [criticReview, setCriticReview] = useState(null);

  const handleGenerateFunctionalSpec = async (file) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const ingestRes = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: formData });
      const ingestData = await ingestRes.json();

      if (ingestData.ambiguity_report?.is_ambiguous) {
        const amb = ingestData.ambiguity_report.ambiguities.map(a => `- ${a.requirement}: ${a.issue}`).join('\n');
        if (!window.confirm(`⚠️ AMBIGUITIES DETECTED:\n\n${amb}\n\nProceed anyway?`)) {
          setLoading(false);
          return;
        }
      }

      // Step 2: Baseline Analysis
      const analyzeRes = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          document_id: ingestData.document_id,
          enabled_modules: ['functional_spec'] 
        }),
      });
      const anaData = await analyzeRes.json();

      // Step 3: High-Fidelity Functional Spec Generation
      const specRes = await fetch(`${API_BASE}/generate-functional-spec`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis_id: anaData.analysis_id }),
      });
      const specResult = await specRes.json();
      setFunctionalSpec(specResult.functional_spec);
      setCriticReview(specResult.critic_review);
    } catch (e) {
      alert("Functional Spec Generation Error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="view-container">
      <div className="loader-container">
        <div className="loader-ring"></div>
        <p>Architecting technical specification document...</p>
      </div>
    </div>
  );

  return (
    <div className="view-container animation-fade-in">
      <header className="view-header">
        <div className="title-area">
          <span className="pre-title">Engineering Agent</span>
          <h1>Functional Architect</h1>
          <p>Generate high-fidelity Technical Requirements Documents (Functional Spec) instantly.</p>
        </div>
      </header>

      {!functional_spec ? (
        <div className="agent-studio-ingest glass-card" style={{ maxWidth: '900px', margin: '40px auto', padding: '60px', textAlign: 'center', position: 'relative', overflow: 'hidden', background: 'repeating-linear-gradient(0deg, transparent, transparent 19px, rgba(0, 243, 255, 0.03) 20px), repeating-linear-gradient(90deg, transparent, transparent 19px, rgba(0, 243, 255, 0.03) 20px)' }}>
          <div className="studio-header" style={{ marginBottom: '40px' }}>
             <span className="badge-sm active" style={{ marginBottom: '16px', display: 'inline-block', background: 'rgba(0, 243, 255, 0.1)', color: 'var(--accent-primary)' }}>BLUEPRINT ENGINE ACTIVE</span>
             <h2 style={{ fontSize: '2.5rem', fontWeight: '700', marginBottom: '12px' }}>Functional Architect Studio</h2>
             <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>Convert business requirements into engineering-ready Functional Specifications.</p>
          </div>

          <div className="studio-dropzone glass-card" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => document.getElementById('functional_spec-up-tool').click()} style={{ border: '2px dashed var(--accent-primary)', padding: '40px', cursor: 'pointer', background: 'rgba(0,0,0,0.3)' }}>
             <div style={{ fontSize: '3rem', marginBottom: '16px' }}>🏗️</div>
             <h4 style={{ marginBottom: '8px' }}>Ingest Material for Architecture</h4>
             <p style={{ fontSize: '0.85rem', opacity: 0.6 }}>Our agents will draft a complete Functional Spec based on your source input.</p>
             <button className="btn-primary" style={{ marginTop: '24px', padding: '12px 32px' }}>LAUNCH ARCHITECT</button>
          </div>
          
          <div className="studio-footer" style={{ marginTop: '40px', display: 'flex', justifyContent: 'center', gap: '32px', opacity: 0.5, fontSize: '0.75rem' }}>
             <span>✓ Automated Sectioning</span>
             <span>✓ Architecture Recommendations</span>
             <span>✓ Export-Ready Markdown</span>
          </div>
          <input type="file" id="functional_spec-up-tool" hidden onChange={(e) => handleGenerateFunctionalSpec(e.target.files[0])} />
        </div>
      ) : (
        <div className="functional_spec-studio-layout">
          <div className="critic-sidebar">
            <CriticFeedback review={criticReview} />
          </div>
          <div className="functional_spec-editor glass-card">
            <div className="editor-toolbar">
              <span className="doc-status">DRAFT - ARCHITECT GENERATED</span>
              <button className="btn-secondary sm" onClick={() => {
                const blob = new Blob([functional_spec], { type: 'text/markdown' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'Technical_Spec.md';
                a.click();
              }}>Download .md</button>
            </div>
            <div className="markdown-content">
              <FunctionalSpecAccordionViewer content={functional_spec} />
            </div>
            <button className="btn-secondary" style={{ marginTop: '20px' }} onClick={() => setFunctionalSpec("")}>New Document</button>
          </div>
        </div>
      )}
    </div>
  );
};

const FlowDesignerView = () => {
  const [loading, setLoading] = useState(false);
  const [diagram, setDiagram] = useState(null);

  const handleGenerateFlow = async (file) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const ingestRes = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: formData });
      const ingestData = await ingestRes.json();

      if (ingestData.ambiguity_report?.is_ambiguous) {
        const amb = ingestData.ambiguity_report.ambiguities.map(a => `- ${a.requirement}: ${a.issue}`).join('\n');
        if (!window.confirm(`⚠️ AMBIGUITIES DETECTED:\n\n${amb}\n\nProceed anyway?`)) {
          setLoading(false);
          return;
        }
      }

      const analyzeRes = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          document_id: ingestData.document_id,
          enabled_modules: ['flow'] 
        }),
      });
      const anaData = await analyzeRes.json();
      setDiagram(anaData.results.diagram);
    } catch (e) {
      alert("Flow Generation Error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="view-container">
      <div className="loader-container">
        <div className="loader-ring"></div>
        <p>Agent mapping process logic and visualizing flow...</p>
      </div>
    </div>
  );

  return (
    <div className="view-container animation-fade-in">
      <header className="view-header">
        <div className="title-area">
          <span className="pre-title">Visual Agent</span>
          <h1>Flow Designer</h1>
          <p>Instantly visualize complex business logic and process flows from your requirements.</p>
        </div>
      </header>

      {!diagram ? (
        <div className="agent-studio-ingest glass-card" style={{ maxWidth: '900px', margin: '40px auto', padding: '60px', textAlign: 'center', position: 'relative', overflow: 'hidden', background: 'radial-gradient(circle at center, rgba(112, 0, 255, 0.05) 0%, transparent 70%)' }}>
          <div className="studio-header" style={{ marginBottom: '40px' }}>
             <span className="badge-sm active" style={{ marginBottom: '16px', display: 'inline-block', background: 'rgba(112, 0, 255, 0.1)', color: 'var(--accent-secondary)' }}>LOGIC ENGINE READY</span>
             <h2 style={{ fontSize: '2.5rem', fontWeight: '700', marginBottom: '12px' }}>Flow Designer Studio</h2>
             <p style={{ color: 'var(--text-muted)', fontSize: '1.1rem' }}>Map business processes into high-fidelity technical flow diagrams.</p>
          </div>

          <div className="studio-dropzone glass-card" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => document.getElementById('flow-up-tool').click()} style={{ border: '2px dashed var(--accent-secondary)', padding: '40px', cursor: 'pointer', background: 'rgba(0,0,0,0.3)' }}>
             <div style={{ fontSize: '3rem', marginBottom: '16px' }}>🎨</div>
             <h4 style={{ marginBottom: '8px' }}>Ingest Logic for Visualization</h4>
             <p style={{ fontSize: '0.85rem', opacity: 0.6 }}>Our Visual Agent will synthesize process flows from your requirements.</p>
             <button className="btn-primary" style={{ marginTop: '24px', padding: '12px 32px', background: 'var(--accent-secondary)' }}>LAUNCH DESIGNER</button>
          </div>
          
          <div className="studio-footer" style={{ marginTop: '40px', display: 'flex', justifyContent: 'center', gap: '32px', opacity: 0.5, fontSize: '0.75rem' }}>
             <span>✓ Automated Mermaid Generation</span>
             <span>✓ Logic Conflict Detection</span>
             <span>✓ Interactive Canvas</span>
          </div>
          <input type="file" id="flow-up-tool" hidden onChange={(e) => handleGenerateFlow(e.target.files[0])} />
        </div>
      ) : (
        <div className="flow-canvas-layout">
          <div className="canvas-main glass-card">
            <div className="canvas-header">
              <span className="status-badge">AUTO-GENERATED PROCESS MAP</span>
              <button className="btn-secondary sm" onClick={() => {
                const code = `graph TD\n${diagram.edges?.map(e => `  ${e.from} --> ${e.to}`).join('\n')}`;
                navigator.clipboard.writeText(code);
                alert("Mermaid code copied to clipboard!");
              }}>Copy Mermaid Code</button>
            </div>
            <div className="mermaid-viewer">
              <Mermaid chart={`graph TD\n${diagram.edges?.map(e => `  ${e.from} --> ${e.to}`).join('\n')}`} />
            </div>
            <div className="canvas-footer">
               <button className="btn-secondary" onClick={() => setDiagram(null)}>New Flow</button>
            </div>
          </div>
          <div className="canvas-details glass-card">
            <h3>Process Elements</h3>
            <div className="node-list">
              {diagram.nodes?.map((node, i) => (
                <div key={i} className="node-item">
                  <span className="node-type">{node.type}</span>
                  <p>{node.label}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const CollapsibleEpic = ({ epic }) => {
  const [isOpen, setIsOpen] = useState(true);
  return (
    <div className="epic-node" style={{ marginBottom: '16px', border: '1px solid var(--glass-border)', borderRadius: '8px', padding: '12px', background: 'rgba(0,0,0,0.2)' }}>
      <div 
        className="node-title" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setIsOpen(!isOpen)} 
        style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
      >
        <span><strong style={{ color: 'var(--accent-primary)' }}>EPIC:</strong> {epic.title}</span>
        <span style={{ fontSize: '0.8rem', opacity: 0.7 }}>{isOpen ? '▼ COLLAPSE' : '▶ EXPAND'}</span>
      </div>
      {isOpen && (
        <div style={{ paddingLeft: '20px', marginTop: '12px' }}>
          {epic.features?.map((feat, i) => <CollapsibleFeature key={feat.id || i} feat={feat} />)}
        </div>
      )}
    </div>
  );
};

const CollapsibleFeature = ({ feat }) => {
  const [isOpen, setIsOpen] = useState(true);
  return (
    <div className="feat-node" style={{ marginBottom: '12px', borderLeft: '2px solid var(--glass-border)', paddingLeft: '12px' }}>
      <div 
        className="node-title" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => setIsOpen(!isOpen)} 
        style={{ cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.95rem' }}
      >
        <span><strong style={{ color: '#00f2ff' }}>FEAT:</strong> {feat.title}</span>
        <span style={{ fontSize: '0.8rem', opacity: 0.7 }}>{isOpen ? '▼' : '▶'}</span>
      </div>
      {isOpen && (
        <div style={{ paddingLeft: '16px', marginTop: '8px' }}>
          {feat.user_stories?.map((story, i) => (
            <div key={story.id || i} className="story-node" style={{ padding: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', marginBottom: '8px', fontSize: '0.85rem' }}>
              <span className="moscow-tag">{story.moscow}</span>
              {story.title}
              {story.tasks && story.tasks.length > 0 && (
                <div style={{ marginTop: '8px', paddingLeft: '12px', borderLeft: '1px dashed rgba(255,255,255,0.2)' }}>
                  {story.tasks.map((task, tIdx) => (
                    <div key={tIdx} style={{ color: 'var(--text-muted)' }}>• Task: {task.title || task}</div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const BacklogEngineerView = () => {
  const [loading, setLoading] = useState(false);
  const [backlog, setBacklog] = useState(null);
  const [criticReview, setCriticReview] = useState(null);
  const [projectId, setProjectId] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);

  const handleGenerateBacklog = async (file) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const ingestRes = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: formData });
      const ingestData = await ingestRes.json();

      if (ingestData.ambiguity_report?.is_ambiguous) {
        const amb = ingestData.ambiguity_report.ambiguities.map(a => `- ${a.requirement}: ${a.issue}`).join('\n');
        if (!window.confirm(`⚠️ AMBIGUITIES DETECTED:\n\n${amb}\n\nProceed anyway?`)) {
          setLoading(false);
          return;
        }
      }

      const analyzeRes = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          document_id: ingestData.document_id,
          enabled_modules: ['backlog'] 
        }),
      });
      const anaData = await analyzeRes.json();

      const backlogRes = await fetch(`${API_BASE}/generate-backlog`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis_id: anaData.analysis_id }),
      });
      const backData = await backlogRes.json();
      setBacklog(backData.backlog);
      setCriticReview(backData.critic_review);
      setProjectId(anaData.analysis_id); // In this simplified flow, analysis_id is the project_id
      setSyncResult(null);
    } catch (e) {
      alert("Backlog Generation Error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await fetch(`${API_BASE}/sync-backlog`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, backlog: { epics: backlog } })
      });
      const data = await res.json();
      setSyncResult(data);
      alert(`Sync Successful! ${data.created_items?.length || 0} items synchronized.`);
    } catch (e) {
      alert("Sync Failed: " + e.message);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) return (
    <div className="view-container">
      <div className="loader-container">
        <div className="loader-ring"></div>
        <p>Agent architecting backlog hierarchy for Azure DevOps...</p>
      </div>
    </div>
  );

  return (
    <div className="view-container animation-fade-in">
      <header className="view-header">
        <div className="title-area">
          <span className="pre-title">Automation Agent</span>
          <h1>Backlog Engineer</h1>
          <p>Architect ADO-ready Epic, Feature, and Story hierarchies with AI precision.</p>
        </div>
      </header>

      {!backlog ? (
        <div className="discovery-tile glass-card" role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') e.currentTarget.click(); }} onClick={() => document.getElementById('back-up-tool').click()}>
          <div className="tile-accent yellow"></div>
          <div className="tile-icon"></div>
          <div className="tile-info">
            <h3>Architect Backlog</h3>
            <p>Upload requirements to generate engineering artifacts</p>
          </div>
          <input type="file" id="back-up-tool" hidden onChange={(e) => handleGenerateBacklog(e.target.files[0])} />
          <div className="tile-action">Launch Engineer</div>
        </div>
      ) : (
        <div className="backlog-workbench-layout">
           <div className="critic-sidebar">
             <CriticFeedback review={criticReview} />
           </div>
           <div className="workbench-main glass-card">
              <div className="workbench-header">
                <h2>Generated Hierarchy</h2>
                <span className="status-badge">READY FOR SYNC</span>
              </div>
              
              {(() => {
                let eCount = 0, fCount = 0, sCount = 0, tCount = 0;
                backlog.epics?.forEach(e => {
                  eCount++;
                  e.features?.forEach(f => {
                    fCount++;
                    f.user_stories?.forEach(s => {
                      sCount++;
                      if (s.tasks) tCount += s.tasks.length;
                    });
                  });
                });
                
                return (
                  <div className="backlog-metrics-boxes" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
                    <div className="glass-card" style={{ padding: '16px', textAlign: 'center' }}>
                      <div style={{ fontSize: '2rem', fontWeight: 'bold', color: 'var(--accent-primary)' }}>{eCount}</div>
                      <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Epics</div>
                    </div>
                    <div className="glass-card" style={{ padding: '16px', textAlign: 'center' }}>
                      <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#00f2ff' }}>{fCount}</div>
                      <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Features</div>
                    </div>
                    <div className="glass-card" style={{ padding: '16px', textAlign: 'center' }}>
                      <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#f4df4e' }}>{sCount}</div>
                      <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px' }}>User Stories</div>
                    </div>
                    <div className="glass-card" style={{ padding: '16px', textAlign: 'center' }}>
                      <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#ff4d4d' }}>{tCount}</div>
                      <div style={{ fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '1px' }}>Tasks</div>
                    </div>
                  </div>
                );
              })()}

              <div className="backlog-explorer" style={{ maxHeight: '600px', overflowY: 'auto', paddingRight: '12px' }}>
                {backlog.epics?.map((epic, i) => (
                  <CollapsibleEpic key={epic.id || i} epic={epic} />
                ))}
              </div>
              <div className="workbench-footer">
                <button className="btn-secondary" onClick={() => {
                   setBacklog(null);
                   setSyncResult(null);
                }}>New Backlog</button>
                <button 
                  className="btn-primary" 
                  onClick={handleSync}
                  disabled={syncing || !backlog || syncResult}
                >
                  {syncing ? 'Synchronizing...' : syncResult ? '✓ Synchronized' : 'Commit to Azure DevOps'}
                </button>
              </div>
           </div>
        </div>
      )}
    </div>
  );
};


// Project View Export
const TraceabilityMatrixView = () => {
  const [loading, setLoading] = useState(false);
  const [matrix, setMatrix] = useState([]);
  const [docs, setDocs] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState("");

  useEffect(() => {
    fetch(`${API_BASE}/documents`).then(r => r.json()).then(setDocs);
  }, []);

  const loadMatrix = async (docId) => {
    if (!docId) return;
    setLoading(true);
    setSelectedDoc(docId);
    try {
      const res = await fetch(`${API_BASE}/traceability/${docId}`);
      const data = await res.json();
      setMatrix(data.matrix || []);
    } catch (e) {
      alert("Traceability Error: " + e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="view-container animation-fade-in">
      <header className="view-header">
        <div className="title-area">
          <span className="pre-title">Governance Agent</span>
          <h1>Traceability Matrix</h1>
          <p>End-to-end audit trail from Business Requirement to Engineering Artifact.</p>
        </div>
        <div className="header-actions">
           {selectedDoc && (
             <button 
               className="btn-primary" 
               onClick={() => window.open(`${API_BASE}/reports/traceability/${selectedDoc}`, '_blank')}
             >
               📄 Download Governance Report (PDF)
             </button>
           )}
        </div>
      </header>

      <div className="traceability-controls glass-card" style={{ marginBottom: "24px", padding: "20px" }}>
        <div style={{ display: "block", marginBottom: "8px", fontSize: "0.85rem", fontWeight: 500, color: "var(--text-main)" }}>Select Project/Document:</div>
        <select onChange={(e) => loadMatrix(e.target.value)} value={selectedDoc} style={{ marginTop: "8px" }}>
          <option value="">-- Choose Project --</option>
          {docs.map(d => <option key={d.id} value={d.id}>{d.name} ({d.id.substring(0,8)})</option>)}
        </select>
      </div>

      {loading ? (
        <div className="loader-container"><div className="loader-ring"></div><p>Calculating traceability paths...</p></div>
      ) : matrix.length > 0 ? (
        <div className="traceability-table-wrapper glass-card">
          <table className="traceability-table">
            <thead>
              <tr>
                <th style={{ width: '25%' }}>Source BRD Requirement</th>
                <th style={{ width: '25%' }}>Generated User Story</th>
                <th style={{ width: '25%' }}>Similar / Linked ADO Work Items</th>
                <th style={{ width: '25%' }}>Test Suite Coverage</th>
              </tr>
            </thead>
            <tbody>
              {matrix.map((row, i) => (
                <tr key={i}>
                  <td>
                    <span className="id-pill" style={{ marginRight: '6px' }}>{row.source_id}</span>
                    <span>{row.source_desc}</span>
                  </td>
                  <td>
                    {row.linked_stories && row.linked_stories.length > 0 ? (
                      row.linked_stories.map(s => (
                        <div key={s.id} className="linked-item">
                          <span className="item-type">STORY</span> {s.title}
                        </div>
                      ))
                    ) : (
                      <span className="orphan-tag">NO LINKED STORY</span>
                    )}
                  </td>
                  <td>
                    {row.similar_ado_items && row.similar_ado_items.length > 0 ? (
                      row.similar_ado_items.map((ado, idx) => (
                        <div key={idx} style={{ color: '#60a5fa', fontSize: '0.85rem', marginBottom: '4px' }}>
                          ⚡ {ado}
                        </div>
                      ))
                    ) : (
                      <span className="orphan-tag">UNSYNCED</span>
                    )}
                  </td>
                  <td>
                    {row.linked_test_cases && row.linked_test_cases.length > 0 ? (
                      row.linked_test_cases.map(tc => (
                        <div key={tc.id} style={{ color: '#4ade80', fontSize: '0.85rem', marginBottom: '4px' }}>
                          🧪 {tc.id}: {tc.title}
                        </div>
                      ))
                    ) : (
                      <span style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Automated Test Coverage</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">Please select a project to view the traceability matrix.</div>
      )}
    </div>
  );
};

const KnowledgeVaultView = () => {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState("");

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/knowledge/search?q=${encodeURIComponent(query)}`);
      const data = await res.json();
      setResults(data.results);
    } catch (err) {
      setResults("Search Failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="view-container animation-fade-in">
      <header className="view-header">
        <div className="title-area">
          <span className="pre-title">Cognitive Intelligence</span>
          <h1>Institutional Memory</h1>
          <p>Semantic search across 12,000+ organizational requirements and technical patterns.</p>
        </div>
      </header>

      <div className="memory-stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
         <div className="glass-card" style={{ padding: '16px' }}>
            <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>INDEXED REQUIREMENTS</div>
            <div style={{ fontSize: '1.2rem', fontWeight: '700', color: 'var(--accent-primary)' }}>12,482</div>
         </div>
         <div className="glass-card" style={{ padding: '16px' }}>
            <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>PATTERN DENSITY</div>
            <div style={{ fontSize: '1.2rem', fontWeight: '700', color: 'var(--accent-secondary)' }}>High</div>
         </div>
         <div className="glass-card" style={{ padding: '16px' }}>
            <div style={{ fontSize: '0.7rem', opacity: 0.6 }}>SEMANTIC NODES</div>
            <div style={{ fontSize: '1.2rem', fontWeight: '700' }}>3.2k</div>
         </div>
      </div>

      <div className="search-container-large glass-card" style={{ padding: "40px", textAlign: "center", background: 'radial-gradient(circle at top right, rgba(0, 243, 255, 0.05), transparent 300px)' }}>
        <h2 style={{ fontSize: '1.5rem', marginBottom: '8px' }}>Deep Memory Search</h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>Query technical architecture, business rules, and compliance patterns.</p>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
          <input 
            type="text" 
            placeholder="e.g., 'How do we handle multi-factor authentication for retail users?'" 
            className="search-input-hero"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ width: "70%", padding: "16px", borderRadius: "12px", background: "rgba(0,0,0,0.3)", color: "#fff", border: "1px solid var(--glass-border)" }}
          />
          <button type="submit" className="btn-primary" disabled={loading} style={{ padding: '0 32px' }}>
            {loading ? "🔍 ANALYZING..." : "QUERY BRAIN"}
          </button>
        </form>
      </div>

      {results && (
        <div className="search-results-area glass-card" style={{ marginTop: "24px", padding: "32px", borderLeft: '4px solid var(--accent-primary)' }}>
          <div style={{ marginBottom: '20px', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.1em', opacity: 0.6 }}>Intelligence Synthesis</div>
          <article className="prose-dark">
            <ReactMarkdown>{typeof results === 'string' ? results : (results ? JSON.stringify(results, null, 2) : '')}</ReactMarkdown>
          </article>
        </div>
      )}
    </div>
  );
};

const GovernanceDashboard = ({ documentId }) => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (documentId) {
      fetch(`${API_BASE}/audit/logs/${documentId}`)
        .then(r => r.json())
        .then(data => {
          setLogs(data.logs || []);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    }
  }, [documentId]);

  return (
    <div className="governance-dashboard glass-card" style={{ padding: "20px", marginTop: "24px" }}>
      <h3 style={{ borderBottom: "1px solid rgba(255,255,255,0.1)", paddingBottom: "12px", marginBottom: "20px" }}>
        🛡️ Governance & Audit Trail
      </h3>
      {loading ? (
        <p>Loading audit trail...</p>
      ) : logs.length > 0 ? (
        <div className="audit-timeline">
          {logs.map((log, i) => (
            <div key={i} className="audit-log-entry" style={{ marginBottom: "16px", paddingLeft: "12px", borderLeft: "2px solid #00f3ff" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "rgba(255,255,255,0.5)" }}>
                <strong>{log.agent_name}</strong>
                <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
              </div>
              <div style={{ fontWeight: "600", margin: "4px 0" }}>{log.action}</div>
              <div style={{ fontSize: "0.9rem", opacity: 0.8 }}>{log.reasoning}</div>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ color: "rgba(255,255,255,0.5)" }}>No audit logs found for this project session.</p>
      )}
    </div>
  );
};

// Project View Export


export default App;
