import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CheckCircle, Code } from 'lucide-react';

const renderReactChild = (val) => {
  if (val === null || val === undefined) return '';
  if (typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean') return String(val);
  if (Array.isArray(val)) {
    return val.map(item => typeof item === 'object' ? JSON.stringify(item) : String(item)).join(' | ');
  }
  return JSON.stringify(val, null, 2);
};

const parseMarkdownTestCases = (text) => {
  if (!text || typeof text !== 'string') return [];
  if (text.includes('"test_cases"') || text.includes('"test_case_id"')) return [];

  // Split by "Test Case X:" or "### Test Case" or "TC-"
  const blocks = text.split(/(?=(?:Test Case\s*\d+:?|###\s*Test Case|TC-\d+:?))/i).filter(b => b.trim());
  const cases = [];

  blocks.forEach((block, idx) => {
    if (!block.toLowerCase().includes('test case') && !block.includes('TC-')) return;

    const tcIdMatch = block.match(/(?:Test Case ID|TC ID|ID):\s*([^\n*]+)/i) || block.match(/(TC-\d+)/i);
    const storyIdMatch = block.match(/(?:User Story ID|Story ID):\s*([^\n*]+)/i);
    const storyTitleMatch = block.match(/(?:User Story Title|Story Title):\s*([^\n*]+)/i);
    const titleMatch = block.match(/(?:Title|Name):\s*([^\n*]+)/i) || block.match(/Test Case\s*\d+:?\s*([^\n*]+)/i);
    const testTypeMatch = block.match(/(?:Test Type|Type):\s*([^\n*]+)/i);
    const descMatch = block.match(/(?:Description|Objective):\s*([^\n*]+)/i);
    const testDataMatch = block.match(/(?:Test Data|Data):\s*([^\n]+)/i);

    // Extract steps
    const steps = [];
    const stepLines = block.split('\n');
    stepLines.forEach(line => {
      const stepMatch = line.match(/^\s*\d+\.\s*(.+)/);
      if (stepMatch) {
        steps.push(stepMatch[1].trim());
      }
    });

    // Extract preconditions
    const preconditions = [];
    //const preMatch = block.match(/Preconditions:\s*\n((?:[ \t]*[\u2022\u25cb\-*][ \t]*[^\n]+(?:\n|$))+)/i);
    const preMatch = block.match(/Preconditions:\s*([\s\S]*?)(?=(?:\n\s*(?:Steps|Test Steps|Expected|Postconditions|Notes|Test Data|Data|TC-|Test Case|###)|$))/i);
    if (preMatch) {
      preMatch[1].split('\n').forEach(l => {
        const cleaned = l.replace(/^[\s\u2022\u25cb\-*]+/, '').trim();
        //if (cleaned) preconditions.push(cleaned);
        if (cleaned && !/^none$/i.test(cleaned)) preconditions.push(cleaned);
      });
    }

    if (titleMatch || tcIdMatch) {
      cases.push({
        test_case_id: tcIdMatch ? tcIdMatch[1].trim() : `TC-${String(idx + 1).padStart(3, '0')}`,
        user_story_id: storyIdMatch ? storyIdMatch[1].trim() : undefined,
        user_story_title: storyTitleMatch ? storyTitleMatch[1].trim() : undefined,
        title: titleMatch ? titleMatch[1].trim() : `Test Case ${idx + 1}`,
        test_type: testTypeMatch ? testTypeMatch[1].trim() : 'Functional',
        description: descMatch ? descMatch[1].trim() : block.split('\n')[0],
        preconditions: preconditions.length > 0 ? preconditions : undefined,
        test_data: testDataMatch ? testDataMatch[1].trim() : undefined,
        steps: steps.length > 0 ? steps : ['Execute test scenario per description']
      });
    }
  });

  return cases;
};

const parseTestCasesData = (data) => {
  if (!data) return { test_cases: [], playwright_script: '' };

  let input = data;
  let script = '';

  // If input is a JSON string, try parsing it first
  if (typeof input === 'string') {
    let cleanStr = input.trim();
    if (cleanStr.includes('```')) {
      const firstTick = cleanStr.indexOf('```');
      const nlIdx = cleanStr.indexOf('\n', firstTick);
      const lastTick = cleanStr.lastIndexOf('```');
      if (nlIdx !== -1 && lastTick > nlIdx) {
        cleanStr = cleanStr.substring(nlIdx + 1, lastTick).trim();
      }
    }

    // 1. Repair unescaped raw newlines/tabs inside double-quoted string values (e.g. playwright_script)
    let repairedStr = cleanStr.replaceAll(/"(?:[^"\\]|\\.)*"/g, (m) => {
      return m.replaceAll('\n', '\\n').replaceAll('\r', '\\r').replaceAll('\t', '\\t');
    });
    // 2. Repair nested stringified json inside test_data fields: "test_data": "{\"key\": \"val\"}" -> "test_data": {"key": "val"}
    repairedStr = repairedStr.replaceAll(/("(?:test_data|test_inputs|payload|data|preconditions)")\s*:\s*"(?:\\")?(\s*\{[\s\S]*?\}\s*)"/g, (match, keyPart, innerObj) => {
      const cleanObj = innerObj.replaceAll('\\"', '"');
      return `${keyPart}: ${cleanObj}`;
    });
    // 3. Repair invalid backslash escapes in Windows paths or regexes before JSON.parse
    repairedStr = repairedStr.replaceAll(/\\(?![\\"/bfnrt]|u[0-9a-fA-F]{4})/g, "\\\\");

    try {
      input = JSON.parse(repairedStr);
    } catch (e) {
      // Extract exact JSON object between first { / [ and last } / ] to ignore trailing prose
      let startIdx = repairedStr.indexOf('{');
      let endIdx = repairedStr.lastIndexOf('}');
      if (startIdx === -1 || (repairedStr.indexOf('[') !== -1 && repairedStr.indexOf('[') < startIdx)) {
        startIdx = repairedStr.indexOf('[');
        endIdx = repairedStr.lastIndexOf(']');
      }
      if (startIdx !== -1 && endIdx > startIdx) {
        try {
          input = JSON.parse(repairedStr.substring(startIdx, endIdx + 1));
        } catch (e2) {
          const markdownCases = parseMarkdownTestCases(cleanStr);
          if (markdownCases.length > 0) return { test_cases: markdownCases, playwright_script: '' };
        }
      } else {
        const markdownCases = parseMarkdownTestCases(cleanStr);
        if (markdownCases.length > 0) return { test_cases: markdownCases, playwright_script: '' };
      }
    }
  }

  // If input is an Array of test cases
  if (Array.isArray(input)) {
    return { test_cases: input, playwright_script: script };
  }

  // If input is an Object
  if (typeof input === 'object' && input !== null) {
    // If input is an error wrapper object containing a raw output string, recover from raw!
    if (input.raw && typeof input.raw === 'string') {
      const recovered = parseTestCasesData(input.raw);
      if (recovered.test_cases && recovered.test_cases.length > 0) {
        return recovered;
      }
    }

    let cases = input.test_cases || input.cases || input.items || [];
    script = input.playwright_script || input.playwright_code || input.script || '';

    // If inner cases is a string, recursively parse inner string!
    if (typeof cases === 'string') {
      const inner = parseTestCasesData(cases);
      cases = inner.test_cases;
      if (!script && inner.playwright_script) script = inner.playwright_script;
    }

    if (Array.isArray(cases)) {
      return { test_cases: cases, playwright_script: script };
    }
  }

  return { test_cases: [], playwright_script: script };
};

const TestCasesViewer = ({ rawData, storyTitle, docId }) => {
  const [viewMode, setViewMode] = useState('manual'); // 'manual' or 'code'
  const [isPushing, setIsPushing] = useState(false);
  const [pushStatus, setPushStatus] = useState('');
  const [showImportModal, setShowImportModal] = useState(false);
  const [importedSpecs, setImportedSpecs] = useState([]);
  const [loadingImport, setLoadingImport] = useState(false);
  const [selectedSpecIndex, setSelectedSpecIndex] = useState(0);

  const parsedData = parseTestCasesData(rawData);
  const errorMsg = (!parsedData.test_cases || parsedData.test_cases.length === 0) ? "Unable to parse structured test cases. Displaying raw output instead." : null;

  const handlePushPlaywright = async () => {
    if (!parsedData.playwright_script) {
      alert("No Playwright script available to push.");
      return;
    }
    setIsPushing(true);
    setPushStatus('');
    try {
      const res = await fetch(`http://127.0.0.1:8000/playwright/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: docId || 'session-doc',
          filename: `e2e_${(docId || 'suite').substring(0,8)}.spec.ts`,
          script_code: parsedData.playwright_script
        })
      });
      const data = await res.json();
      if (res.ok) {
        setPushStatus(`✅ ${data.message || 'Pushed to Playwright repository!'}`);
      } else {
        setPushStatus(`❌ ${data.detail || 'Push failed'}`);
      }
    } catch (e) {
      setPushStatus(`❌ Push error: ${e.message}`);
    } finally {
      setIsPushing(false);
    }
  };

  const handlePullPlaywright = async () => {
    setShowImportModal(true);
    setLoadingImport(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/playwright/import`);
      const data = await res.json();
      setImportedSpecs(data.specs || []);
    } catch (e) {
      console.error("Error importing specs:", e);
    } finally {
      setLoadingImport(false);
    }
  };

  if (errorMsg || !parsedData.test_cases?.length) {
    const rawMarkdownStr = typeof rawData === 'string' ? rawData : (rawData ? JSON.stringify(rawData, null, 2) : '');
    return (
      <div className="markdown-body">
        {errorMsg && <div style={{ color: 'var(--warning)', marginBottom: '10px' }}>{errorMsg}</div>}
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{rawMarkdownStr || "*No Test Cases generated for this session.*"}</ReactMarkdown>
      </div>
    );
  }

  const API_BASE = import.meta.env.VITE_API_BASE_URL || (
    window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      ? 'http://127.0.0.1:8000'
      : 'https://ba-agent-aqd8c3d8dtdrbcat.centralus-01.azurewebsites.net'
  );

  const handleDownloadPdf = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/qa/export-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: storyTitle || 'QA Test Suite',
          test_cases: rawData
        })
      });
      if (res.ok) {
        const htmlContent = await res.text();
        const printWindow = window.open('', '_blank');
        if (printWindow) {
          printWindow.document.write(htmlContent);
          printWindow.document.close();
        } else {
          alert("Please allow popups for this site to view and save the PDF.");
        }
      } else {
        alert("Failed to generate PDF document.");
      }
    } catch (e) {
      alert("Error exporting PDF: " + e.message);
    }
  };

  return (
    <div className="test-cases-viewer">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button 
            className="btn-primary mini"
            onClick={handleDownloadPdf}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 14px', fontSize: '0.85rem', background: 'linear-gradient(135deg, #0284c7 0%, #0369a1 100%)' }}
          >
            📄 Download PDF Spec
          </button>
          <button 
            className="btn-secondary mini" 
            onClick={handlePullPlaywright}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '0.85rem' }}
          >
            📥 Pull Existing Playwright Specs
          </button>
          <button 
            className="btn-primary mini" 
            onClick={handlePushPlaywright}
            disabled={isPushing || !parsedData.playwright_script}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 14px', fontSize: '0.85rem' }}
          >
            🚀 {isPushing ? 'Pushing...' : 'Push to Playwright Repo'}
          </button>
          {docId && (
            <button 
              className="btn-secondary mini"
              onClick={() => window.open(`http://127.0.0.1:8000/playwright/download/${docId}`, '_blank')}
              style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '6px 12px', fontSize: '0.85rem' }}
            >
              📄 Export .spec.ts
            </button>
          )}
          {pushStatus && <span style={{ fontSize: '0.85rem', color: '#60a5fa', fontWeight: '500' }}>{pushStatus}</span>}
        </div>

        <div style={{ display: 'flex', background: 'var(--glass-border)', padding: '4px', borderRadius: '8px' }}>
          <button 
            className={`btn-ghost ${viewMode === 'manual' ? 'active' : ''}`}
            onClick={() => setViewMode('manual')}
            style={{ padding: '4px 12px', background: viewMode === 'manual' ? 'var(--secondary-bg)' : 'transparent', borderRadius: '4px', border: 'none', cursor: 'pointer' }}
          >
            <CheckCircle size={16} style={{marginRight: '6px'}}/> Manual Cases
          </button>
          <button 
            className={`btn-ghost ${viewMode === 'code' ? 'active' : ''}`}
            onClick={() => setViewMode('code')}
            style={{ padding: '4px 12px', background: viewMode === 'code' ? 'var(--secondary-bg)' : 'transparent', borderRadius: '4px', border: 'none', cursor: 'pointer' }}
          >
            <Code size={16} style={{marginRight: '6px'}}/> Playwright Spec
          </button>
        </div>
      </div>

      {viewMode === 'manual' ? (
        <div className="manual-cases-list" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {(() => {
            const totalCount = parsedData.test_cases.length;
            const coveredCount = parsedData.test_cases.filter(tc => tc.coverage_status === 'ALREADY_COVERED').length;
            const newCount = totalCount - coveredCount;
            const coveredPct = totalCount > 0 ? Math.round((coveredCount / totalCount) * 100) : 0;
            const newPct = totalCount > 0 ? 100 - coveredPct : 0;

            return (
              <div style={{
                background: 'rgba(0, 242, 255, 0.05)',
                border: '1px solid rgba(0, 242, 255, 0.2)',
                borderRadius: '8px',
                padding: '12px 16px',
                display: 'flex',
                justify: 'space-between',
                alignItems: 'center',
                fontSize: '0.85rem',
                color: 'var(--text-main)',
                marginBottom: '4px'
              }}>
                <div>
                  <strong>📊 Existing Test Coverage Audit:</strong>{' '}
                  <span style={{ color: '#4ade80', fontWeight: '600' }}>{coveredCount} Covered in Repo ({coveredPct}%)</span>{' '}
                  <span style={{ color: '#aaa' }}>|</span>{' '}
                  <span style={{ color: '#00f2ff', fontWeight: '600' }}>{newCount} New Coverage Required ({newPct}%)</span>
                </div>
                <span style={{ color: '#aaa' }}>Total Scenarios: {totalCount}</span>
              </div>
            );
          })()}

          {parsedData.test_cases.map((tc, idx) => {
            const displayStoryName = tc.user_story_title || tc.user_story_name || storyTitle || tc.user_story_id || tc.requirement_id || null;
            
            // Format Gherkin placeholders if quotes are empty
            let gherkinText = tc.gherkin_scenario || '';
            if (gherkinText && tc.scenario_outline && Array.isArray(tc.scenario_outline.headers)) {
              tc.scenario_outline.headers.forEach(h => {
                gherkinText = gherkinText.replace(/''|""/, `"<${h}>"`);
              });
            }

            return (
              <div key={idx} className="glass-card" style={{ padding: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', margin: '0 0 8px 0', flexWrap: 'wrap' }}>
                      <h4 style={{ margin: 0, color: 'var(--accent-primary)', fontSize: '1.1rem' }}>{tc.test_case_id}</h4>
                      <span style={{ 
                        padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: '600',
                        background: tc.coverage_status === 'ALREADY_COVERED' ? 'rgba(34, 197, 94, 0.15)' : 'rgba(0, 242, 255, 0.15)',
                        color: tc.coverage_status === 'ALREADY_COVERED' ? '#4ade80' : '#00f2ff',
                        border: `1px solid ${tc.coverage_status === 'ALREADY_COVERED' ? 'rgba(34, 197, 94, 0.4)' : 'rgba(0, 242, 255, 0.4)'}`
                      }}>
                        {tc.coverage_status === 'ALREADY_COVERED' ? '🟢 Covered in Repo' : '🆕 New Coverage Required'}
                      </span>
                      {displayStoryName && (
                        <span style={{ 
                          background: 'var(--glass-bg)', border: '1px solid var(--glass-border)', 
                          padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', color: 'var(--accent-primary)',
                          fontWeight: '600'
                        }}>
                          🔗 {displayStoryName}
                        </span>
                      )}
                    </div>
                  <div className="test-case-desc-content" style={{ margin: '0 0 10px 0', fontSize: '0.9rem', color: 'var(--text-main)' }}>
                    {typeof tc.description === 'string' ? (
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {tc.description.replace(/([^\s])\s*(\*\*(?:Test Objective|Test Type Classification|Execution Steps Details|Expected Verification Point|Objective & Scope|Prerequisites|Test Data|Verification)[^*]*?:\*\*)/gi, '$1\n\n$2')}
                      </ReactMarkdown>
                    ) : renderReactChild(tc.description)}
                  </div>

                  {/* Gherkin Scenario Syntax Block */}
                  {gherkinText && (
                    <div style={{ margin: '10px 0', background: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '8px', padding: '12px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: '600', color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'block', marginBottom: '6px' }}>
                        🥒 Gherkin BDD Scenario
                      </span>
                      <pre style={{ margin: 0, color: '#e2e8f0', fontFamily: 'Consolas, monospace', fontSize: '0.85rem', whiteSpace: 'pre-wrap', lineHeight: '1.4' }}>
                        {gherkinText}
                      </pre>
                    </div>
                  )}

                  {/* Scenario Outline Examples Table */}
                  {tc.scenario_outline && tc.scenario_outline.headers && tc.scenario_outline.examples && (
                    <div style={{ margin: '10px 0', background: 'rgba(0,0,0,0.2)', border: '1px solid var(--glass-border)', borderRadius: '8px', padding: '12px' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: '600', color: 'var(--accent-primary)', textTransform: 'uppercase', display: 'block', marginBottom: '6px' }}>
                        📊 Scenario Outline Examples Table
                      </span>
                      <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', fontSize: '0.8rem', borderCollapse: 'collapse' }}>
                          <thead>
                            <tr style={{ background: 'rgba(255,255,255,0.05)' }}>
                              {tc.scenario_outline.headers.map((h, hIdx) => (
                                <th key={hIdx} style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>{h}</th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {tc.scenario_outline.examples.map((row, rIdx) => (
                              <tr key={rIdx} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                {row.map((cell, cIdx) => (
                                  <td key={cIdx} style={{ padding: '6px 10px', color: '#ccc' }}>{renderReactChild(cell)}</td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
                <span style={{ 
                  padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem', fontWeight: '600',
                  background: (tc.test_type || tc.type || '').toLowerCase().includes('positive') ? 'rgba(25,128,56,0.1)' : 
                              (tc.test_type || tc.type || '').toLowerCase().includes('negative') ? 'rgba(218,30,40,0.1)' : 'rgba(241,194,27,0.1)',
                  color: (tc.test_type || tc.type || '').toLowerCase().includes('positive') ? 'var(--success)' : 
                         (tc.test_type || tc.type || '').toLowerCase().includes('negative') ? 'var(--error)' : 'var(--warning)'
                }}>
                  {renderReactChild(tc.test_type || tc.type || 'Functional')}
                </span>
              </div>
              
              {tc.preconditions && (
                <div style={{ marginBottom: '8px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  <strong>Preconditions:</strong> {renderReactChild(tc.preconditions)}
                </div>
              )}
              
              {tc.test_data && (
                <div style={{ marginBottom: '12px', fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                  <strong>Test Data:</strong> {renderReactChild(tc.test_data)}
                </div>
              )}
              
              <div style={{ background: 'var(--primary-bg)', borderRadius: '8px', padding: '12px', fontSize: '0.9rem' }}>
                <strong style={{ display: 'block', marginBottom: '8px' }}>Steps:</strong>
                <ol style={{ margin: '0 0 12px 20px', padding: 0 }}>
                  {tc.steps?.map((step, sIdx) => (
                    <li key={sIdx} style={{marginBottom: '6px'}}>
                      {typeof step === 'string' ? step : (
                        <>
                          <span>{renderReactChild(step.action)}</span>
                          {step.expected_result && (
                            <span style={{ display: 'block', color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '2px' }}>
                              ↳ <em>Expected:</em> {renderReactChild(step.expected_result)}
                            </span>
                          )}
                        </>
                      )}
                    </li>
                  ))}
                </ol>
                {tc.postconditions && (
                  <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '8px', marginBottom: '8px' }}>
                    <strong>Postconditions:</strong> {renderReactChild(tc.postconditions)}
                  </div>
                )}
                {tc.expected_result && (
                  <div style={{ borderTop: '1px solid var(--glass-border)', paddingTop: '8px' }}>
                    <strong>Overall Expected Result:</strong> {renderReactChild(tc.expected_result)}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        </div>
      ) : (
        <div className="playwright-code-view">
          {parsedData.playwright_script ? (
             <div style={{ background: '#1e1e1e', borderRadius: '8px', padding: '16px', overflowX: 'auto' }}>
               <pre style={{ margin: 0, color: '#d4d4d4', fontFamily: '"JetBrains Mono", monospace', fontSize: '0.9rem' }}>
                 <code>{parsedData.playwright_script}</code>
               </pre>
             </div>
          ) : (
             <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>
               No Playwright script generated for this set.
             </div>
          )}
        </div>
      )}
      {showImportModal && (
        <div className="modal-overlay" style={{ zIndex: 10000 }}>
          <div className="modal-content glass-card animation-fade-in" style={{ maxWidth: '900px', width: '100%', padding: '24px', background: '#0f172a', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.15)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '12px' }}>
              <div>
                <h3 style={{ margin: 0, color: '#f8fafc', fontSize: '1.25rem' }}>Playwright Spec Repository Explorer</h3>
                <p style={{ margin: '4px 0 0 0', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Inspect existing repository specs & pushed BA Agent automated test files</p>
              </div>
              <button className="btn-secondary mini" onClick={() => setShowImportModal(false)} style={{ padding: '6px 14px' }}>✕ Close</button>
            </div>

            {loadingImport ? (
              <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                <div className="discovery-spinner" style={{ margin: '0 auto 12px' }}></div>
                <p>Scanning repository directory (`playwright_tests/`) for TypeScript test specs...</p>
              </div>
            ) : importedSpecs.length > 0 ? (
              <div style={{ display: 'flex', gap: '20px', minHeight: '400px', maxHeight: '550px' }}>
                {/* Left File List */}
                <div style={{ width: '35%', borderRight: '1px solid rgba(255,255,255,0.1)', paddingRight: '16px', overflowY: 'auto' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase' }}>
                    Repository Specs ({importedSpecs.length})
                  </div>
                  {importedSpecs.map((spec, idx) => {
                    const isSelected = selectedSpecIndex === idx;
                    return (
                      <div 
                        key={idx} 
                         role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") e.currentTarget.click(); }} onClick={() => setSelectedSpecIndex(idx)}
                        style={{ 
                          padding: '12px', 
                          borderRadius: '8px', 
                          marginBottom: '8px', 
                          cursor: 'pointer',
                          background: isSelected ? 'rgba(59, 130, 246, 0.2)' : 'rgba(255,255,255,0.03)',
                          border: isSelected ? '1px solid #60a5fa' : '1px solid rgba(255,255,255,0.08)',
                          transition: 'all 0.2s ease'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{ fontWeight: '600', color: isSelected ? '#ffffff' : '#93c5fd', fontSize: '0.9rem' }}>📁 {spec.filename}</span>
                          {spec.is_pushed_from_ba_agent ? (
                            <span style={{ fontSize: '0.65rem', padding: '2px 6px', background: 'rgba(34, 197, 94, 0.2)', color: '#4ade80', borderRadius: '4px', border: '1px solid rgba(34, 197, 94, 0.4)' }}>
                              Pushed by Agent
                            </span>
                          ) : (
                            <span style={{ fontSize: '0.65rem', padding: '2px 6px', background: 'rgba(148, 163, 184, 0.2)', color: '#cbd5e1', borderRadius: '4px' }}>
                              Existing Spec
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'flex', gap: '12px' }}>
                          <span>🧪 {spec.test_count} Scenarios</span>
                          <span>📦 {spec.file_size}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Right Spec Detail & Code Inspector */}
                <div style={{ width: '65%', display: 'flex', flexDirection: 'column', overflowY: 'auto' }}>
                  {importedSpecs[selectedSpecIndex] ? (
                    <div>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                        <div>
                          <h4 style={{ margin: 0, color: '#60a5fa', fontSize: '1.05rem' }}>{importedSpecs[selectedSpecIndex].filename}</h4>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            Updated: {importedSpecs[selectedSpecIndex].modified_at}
                          </span>
                        </div>
                        <button 
                          className="btn-secondary mini"
                          onClick={() => {
                            navigator.clipboard.writeText(importedSpecs[selectedSpecIndex].content);
                            alert("Playwright spec code copied to clipboard!");
                          }}
                          style={{ padding: '4px 10px', fontSize: '0.8rem' }}
                        >
                          📋 Copy Code
                        </button>
                      </div>

                      {/* Scenario Summary */}
                      {importedSpecs[selectedSpecIndex].test_titles?.length > 0 && (
                        <div style={{ background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', marginBottom: '12px', border: '1px solid rgba(255,255,255,0.08)' }}>
                          <strong style={{ display: 'block', fontSize: '0.85rem', color: '#f8fafc', marginBottom: '6px' }}>Test Scenarios ({importedSpecs[selectedSpecIndex].test_titles.length}):</strong>
                          <ul style={{ margin: '0 0 0 16px', padding: 0, fontSize: '0.8rem', color: '#cbd5e1' }}>
                            {importedSpecs[selectedSpecIndex].test_titles.map((t, i) => (
                              <li key={i} style={{ marginBottom: '3px' }}>{t}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Code Viewer */}
                      <div style={{ background: '#1e1e1e', borderRadius: '8px', padding: '14px', overflowX: 'auto', border: '1px solid rgba(255,255,255,0.1)' }}>
                        <pre style={{ margin: 0, color: '#d4d4d4', fontFamily: '"JetBrains Mono", monospace', fontSize: '0.85rem', lineHeight: '1.4' }}>
                          <code>{importedSpecs[selectedSpecIndex].content}</code>
                        </pre>
                      </div>
                    </div>
                  ) : (
                    <div style={{ color: 'var(--text-muted)', padding: '20px' }}>Select a spec file to inspect.</div>
                  )}
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)' }}>No existing Playwright specs found in repository directory.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TestCasesViewer;
