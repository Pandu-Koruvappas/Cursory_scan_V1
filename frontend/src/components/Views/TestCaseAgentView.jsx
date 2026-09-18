import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Loader2, RefreshCw, Send, CheckCircle, Upload, FileText, X, ChevronLeft, ChevronRight, Menu } from 'lucide-react';
import TestCasesViewer from './TestCasesViewer';

const API_BASE = import.meta.env.VITE_API_BASE_URL || (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'
    : 'https://ba-agent-aqd8c3d8dtdrbcat.centralus-01.azurewebsites.net'
);

const TestCaseAgentView = () => {
    const [activeMode, setActiveMode] = useState('ado'); // 'ado' | 'brd'
    const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
    
    // ADO Mode state
    const [workItems, setWorkItems] = useState([]);
    const [selectedItem, setSelectedItem] = useState(null);
    const [isLoadingItems, setIsLoadingItems] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isSyncing, setIsSyncing] = useState(false);
    const [testCasesMarkdown, setTestCasesMarkdown] = useState('');
    const [syncSuccess, setSyncSuccess] = useState(false);

    // BRD Upload Mode state
    const [brdFile, setBrdFile] = useState(null);
    const [isBrdGenerating, setIsBrdGenerating] = useState(false);
    const [brdProgressMsg, setBrdProgressMsg] = useState('');
    const [isDragging, setIsDragging] = useState(false);

    useEffect(() => {
        fetchWorkItems();
    }, []);

    const fetchWorkItems = async () => {
        setIsLoadingItems(true);
        try {
            const res = await fetch(`${API_BASE}/ado-work-items`);
            if (res.ok) {
                const data = await res.json();
                const validItems = data.filter(i => 
                    ['User Story', 'Feature', 'Bug', 'Task'].includes(i.type)
                );
                setWorkItems(validItems);
            }
        } catch (e) {
            console.error("Failed to fetch ADO items for QA", e);
        } finally {
            setIsLoadingItems(false);
        }
    };

    const handleSelectItem = (item) => {
        setSelectedItem(item);
        // Automatically collapse selection panel upon selecting an ADO item
        setIsSidebarCollapsed(true);
    };

    const handleGenerate = async () => {
        if (!selectedItem) return;
        setIsGenerating(true);
        setTestCasesMarkdown('');
        setSyncSuccess(false);

        try {
            const res = await fetch(`${API_BASE}/api/qa/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ item_id: selectedItem.id })
            });
            if (res.ok) {
                const data = await res.json();
                setTestCasesMarkdown(data.markdown);
            } else {
                throw new Error("Failed to generate test cases");
            }
        } catch (e) {
            alert("Error: " + e.message);
        } finally {
            setIsGenerating(false);
        }
    };

    const handleGenerateFromBrd = async () => {
        if (!brdFile) return;
        setIsBrdGenerating(true);
        setBrdProgressMsg('Extracting BRD content & generating Auto-Backlog User Stories...');
        setTestCasesMarkdown('');
        setSyncSuccess(false);
        setSelectedItem({ id: 'BRD', title: brdFile.name, type: 'Document' });

        // Auto collapse sidebar when generating from BRD
        setIsSidebarCollapsed(true);

        const formData = new FormData();
        formData.append('file', brdFile);

        try {
            const res = await fetch(`${API_BASE}/api/qa/generate-from-brd`, {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                setTestCasesMarkdown(data.test_cases);
            } else {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Failed to generate test cases from BRD");
            }
        } catch (e) {
            alert("Error generating test cases from BRD: " + e.message);
        } finally {
            setIsBrdGenerating(false);
            setBrdProgressMsg('');
        }
    };

    const handleSync = async () => {
        if (!selectedItem || !testCasesMarkdown || selectedItem.id === 'BRD') return;
        setIsSyncing(true);

        try {
            const res = await fetch(`${API_BASE}/api/qa/sync`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    parent_id: selectedItem.id,
                    markdown_content: testCasesMarkdown
                })
            });
            
            if (res.ok) {
                setSyncSuccess(true);
            } else {
                throw new Error("Failed to sync to ADO");
            }
        } catch (e) {
            alert("Sync Error: " + e.message);
        } finally {
            setIsSyncing(false);
        }
    };

    const handleFileDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            setBrdFile(e.dataTransfer.files[0]);
        }
    };

    return (
        <div className="view-container">
            <header className="view-header">
                <div className="title-area">
                    <span className="pre-title">Quality Assurance Copilot</span>
                    <h1>Test Case Agent</h1>
                    <p>Select an Azure DevOps work item or upload a BRD document to generate high-accuracy BDD test cases & Playwright scripts.</p>
                </div>
            </header>

            <div style={{ display: 'flex', gap: '24px', height: 'calc(100vh - 200px)', position: 'relative' }}>
                
                {/* Left Panel: Item Selection / BRD Upload */}
                <div className="glass-card" style={{ 
                    flex: isSidebarCollapsed ? '0 0 0px' : '0 0 360px', 
                    width: isSidebarCollapsed ? '0px' : '360px',
                    display: 'flex', 
                    flexDirection: 'column',
                    overflow: 'hidden',
                    opacity: isSidebarCollapsed ? 0 : 1,
                    pointerEvents: isSidebarCollapsed ? 'none' : 'all',
                    transition: 'all 0.3s ease-in-out',
                    marginRight: isSidebarCollapsed ? '-24px' : '0px'
                }}>
                    
                    {/* Option A Dual-Tab Mode Switcher Header */}
                    <div style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.1)', display: 'flex', gap: '8px', background: 'rgba(0,0,0,0.2)', borderRadius: '12px 12px 0 0', alignItems: 'center' }}>
                        <button
                            onClick={() => { setActiveMode('ado'); }}
                            style={{
                                flex: 1,
                                padding: '8px 12px',
                                borderRadius: '6px',
                                border: 'none',
                                cursor: 'pointer',
                                fontSize: '0.85rem',
                                fontWeight: '600',
                                background: activeMode === 'ado' ? 'var(--accent-primary, #00f2ff)' : 'transparent',
                                color: activeMode === 'ado' ? '#000' : '#aaa',
                                transition: 'all 0.2s'
                            }}
                        >
                            ADO Backlog
                        </button>
                        <button
                            onClick={() => { setActiveMode('brd'); }}
                            style={{
                                flex: 1,
                                padding: '8px 12px',
                                borderRadius: '6px',
                                border: 'none',
                                cursor: 'pointer',
                                fontSize: '0.85rem',
                                fontWeight: '600',
                                background: activeMode === 'brd' ? 'var(--accent-primary, #00f2ff)' : 'transparent',
                                color: activeMode === 'brd' ? '#000' : '#aaa',
                                transition: 'all 0.2s'
                            }}
                        >
                            Upload BRD
                        </button>
                        <button 
                            onClick={() => setIsSidebarCollapsed(true)} 
                            title="Close selection tab"
                            style={{ background: 'none', border: 'none', color: '#aaa', cursor: 'pointer', padding: '4px', display: 'flex', alignItems: 'center' }}
                        >
                            <ChevronLeft size={20} />
                        </button>
                    </div>

                    {/* Mode 1: ADO Work Items List */}
                    {activeMode === 'ado' && (
                        <>
                            <div style={{ padding: '16px 20px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h4 style={{ margin: 0, fontSize: '0.9rem', color: '#ccc' }}>Active ADO Items</h4>
                                <button className="icon-button" onClick={fetchWorkItems} disabled={isLoadingItems}>
                                    <RefreshCw size={16} className={isLoadingItems ? 'spinner' : ''} />
                                </button>
                            </div>
                            <div style={{ flex: 1, overflowY: 'auto', padding: '10px' }}>
                                {isLoadingItems ? (
                                    <div style={{ padding: '20px', textAlign: 'center', color: '#aaa' }}>Loading ADO Items...</div>
                                ) : workItems.length === 0 ? (
                                    <div style={{ padding: '20px', textAlign: 'center', color: '#aaa' }}>No active ADO work items found.</div>
                                ) : (
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        {workItems.map(item => (
                                            <button 
                                                key={item.id}
                                                onClick={() => handleSelectItem(item)}
                                                style={{
                                                    padding: '12px 16px',
                                                    borderRadius: '8px',
                                                    cursor: 'pointer',
                                                    background: selectedItem?.id === item.id ? 'rgba(0, 242, 255, 0.15)' : 'rgba(255,255,255,0.02)',
                                                    border: `1px solid ${selectedItem?.id === item.id ? 'var(--accent-primary)' : 'rgba(255,255,255,0.05)'}`,
                                                    transition: 'all 0.2s',
                                                    textAlign: 'left',
                                                    display: 'block',
                                                    width: '100%'
                                                }}
                                            >
                                                <span style={{ fontSize: '0.75rem', color: '#aaa', marginBottom: '4px', display: 'flex', justifyContent: 'space-between' }}>
                                                    <span>{item.type} {item.id}</span>
                                                    <span style={{ color: item.status === 'New' ? '#ff9800' : '#4caf50' }}>{item.status}</span>
                                                </span>
                                                <span style={{ fontWeight: '500', fontSize: '0.9rem', lineHeight: '1.3', display: 'block' }}>
                                                    {item.title}
                                                </span>
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </>
                    )}

                    {/* Mode 2: BRD Document Upload */}
                    {activeMode === 'brd' && (
                        <div style={{ flex: 1, padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
                            <div style={{ fontSize: '0.85rem', color: '#aaa', lineHeight: '1.4' }}>
                                Upload a Business Requirements Document (PDF, DOCX, TXT) to execute the <strong>Auto-Backlog Pipeline (Approach 3)</strong> and generate test cases.
                            </div>

                            {/* Drop Zone */}
                            <button
                                onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
                                onDragLeave={() => setIsDragging(false)}
                                onDrop={handleFileDrop}
                                style={{
                                    border: `2px dashed ${isDragging ? 'var(--accent-primary, #00f2ff)' : 'rgba(255,255,255,0.15)'}`,
                                    borderRadius: '12px',
                                    padding: '24px 16px',
                                    textAlign: 'center',
                                    background: isDragging ? 'rgba(0, 242, 255, 0.08)' : 'rgba(0,0,0,0.2)',
                                    transition: 'all 0.2s',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    cursor: 'pointer',
                                    width: '100%',
                                    outline: 'none',
                                    color: 'inherit'
                                }}
                                onClick={() => document.getElementById('brd-file-input').click()}
                            >
                                <input
                                    id="brd-file-input"
                                    type="file"
                                    accept=".pdf,.docx,.doc,.txt"
                                    style={{ display: 'none' }}
                                    onChange={(e) => {
                                        if (e.target.files && e.target.files[0]) {
                                            setBrdFile(e.target.files[0]);
                                        }
                                    }}
                                />
                                <Upload size={32} style={{ color: 'var(--accent-primary, #00f2ff)', marginBottom: '12px' }} />
                                <span style={{ margin: 0, fontWeight: '500', fontSize: '0.95rem', display: 'block' }}>Drag & drop BRD file here</span>
                                <span style={{ fontSize: '0.75rem', color: '#888', marginTop: '4px', display: 'block' }}>Supports .pdf, .docx, .txt</span>
                            </button>

                            {/* Selected File Card */}
                            {brdFile && (
                                <div style={{
                                    padding: '12px 16px',
                                    borderRadius: '8px',
                                    background: 'rgba(0, 242, 255, 0.08)',
                                    border: '1px solid rgba(0, 242, 255, 0.2)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between'
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                                        <FileText size={20} style={{ color: 'var(--accent-primary, #00f2ff)', flexShrink: 0 }} />
                                        <div style={{ overflow: 'hidden' }}>
                                            <div style={{ fontWeight: '500', fontSize: '0.85rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                {brdFile.name}
                                            </div>
                                            <div style={{ fontSize: '0.75rem', color: '#aaa' }}>
                                                {(brdFile.size / 1024).toFixed(1)} KB
                                            </div>
                                        </div>
                                    </div>
                                    <button 
                                        onClick={(e) => { e.stopPropagation(); setBrdFile(null); }}
                                        style={{ background: 'none', border: 'none', color: '#aaa', cursor: 'pointer', padding: '4px' }}
                                    >
                                        <X size={16} />
                                    </button>
                                </div>
                            )}

                            {/* Generate Button */}
                            <button
                                className="btn-primary"
                                onClick={handleGenerateFromBrd}
                                disabled={!brdFile || isBrdGenerating}
                                style={{
                                    marginTop: 'auto',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '8px',
                                    padding: '12px',
                                    fontSize: '0.95rem'
                                }}
                            >
                                {isBrdGenerating ? <Loader2 size={16} className="spinner" /> : <Send size={16} />}
                                {isBrdGenerating ? "Generating Test Suite..." : "Generate Tests from BRD"}
                            </button>
                        </div>
                    )}
                </div>

                {/* Right Panel: Generation & Results */}
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px', transition: 'all 0.3s ease-in-out' }}>
                    {selectedItem ? (
                        <>
                            <div className="glass-card" style={{ padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                                    {isSidebarCollapsed && (
                                        <button 
                                            className="btn-primary"
                                            onClick={() => setIsSidebarCollapsed(false)}
                                            style={{ padding: '8px 14px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)' }}
                                            title="Re-open selection sidebar"
                                        >
                                            <ChevronRight size={16} /> Change Selection
                                        </button>
                                    )}
                                    <div>
                                        <div style={{ fontSize: '0.8rem', color: 'var(--accent-primary)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '1px' }}>Selected Target</div>
                                        <h2 style={{ margin: 0 }}>{selectedItem.type} {selectedItem.id !== 'BRD' ? selectedItem.id + ':' : ''} {selectedItem.title}</h2>
                                    </div>
                                </div>

                                {activeMode === 'ado' && selectedItem.id !== 'BRD' && (
                                    <button 
                                        className="btn-primary" 
                                        onClick={handleGenerate}
                                        disabled={isGenerating}
                                        style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
                                    >
                                        {isGenerating ? <Loader2 size={16} className="spinner" /> : <Send size={16} />}
                                        {isGenerating ? "Analyzing..." : "Generate Tests"}
                                    </button>
                                )}
                            </div>

                            <div className="glass-card" style={{ flex: 1, padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
                                {testCasesMarkdown ? (
                                    <>
                                        <div style={{ flex: 1, paddingBottom: '20px' }}>
                                            <TestCasesViewer rawData={testCasesMarkdown} storyTitle={selectedItem?.title} />
                                        </div>
                                        {activeMode === 'ado' && selectedItem.id !== 'BRD' && (
                                            <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '20px', display: 'flex', justifyContent: 'flex-end' }}>
                                                {syncSuccess ? (
                                                    <button className="btn-primary" style={{ background: '#4caf50', display: 'flex', alignItems: 'center', gap: '8px' }} disabled>
                                                        <CheckCircle size={16} /> Synced to ADO
                                                    </button>
                                                ) : (
                                                    <button 
                                                        className="btn-primary" 
                                                        onClick={handleSync}
                                                        disabled={isSyncing}
                                                        style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
                                                    >
                                                        {isSyncing ? <Loader2 size={16} className="spinner" /> : <RefreshCw size={16} />}
                                                        {isSyncing ? "Syncing..." : "Sync to Azure DevOps"}
                                                    </button>
                                                )}
                                            </div>
                                        )}
                                    </>
                                ) : (isGenerating || isBrdGenerating) ? (
                                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.8 }}>
                                        <Loader2 size={40} className="spinner" style={{ color: 'var(--accent-primary)', marginBottom: '16px' }} />
                                        <p style={{ fontWeight: '500' }}>{brdProgressMsg || "Executing Multi-Agent Processing Pipeline..."}</p>
                                        <small style={{ color: '#aaa', marginTop: '8px' }}>
                                            {isBrdGenerating ? "Auto-Backlog Pipeline: BRD ➔ Epics/User Stories ➔ QA Test Suite & Playwright Scripts." : "Drafting cases with Groq, verifying accuracy with Azure OpenAI."}
                                        </small>
                                    </div>
                                ) : (
                                    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.4 }}>
                                        <p>{activeMode === 'brd' ? "Select a BRD file on the left and click 'Generate Tests from BRD'." : "Click 'Generate Tests' to start."}</p>
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="glass-card" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.4 }}>
                            {isSidebarCollapsed && (
                                <button 
                                    className="btn-primary"
                                    onClick={() => setIsSidebarCollapsed(false)}
                                    style={{ position: 'absolute', top: '24px', left: '24px', padding: '8px 14px', fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}
                                >
                                    <ChevronRight size={16} /> Open Selection Panel
                                </button>
                            )}
                            <p>{activeMode === 'brd' ? "Upload a BRD document from the selection panel to begin." : "Select a work item from the selection panel to begin."}</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default TestCaseAgentView;
