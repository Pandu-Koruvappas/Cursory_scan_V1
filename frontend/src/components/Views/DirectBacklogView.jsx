import React, { useState } from 'react';
import { UploadCloud, CheckCircle, FileText, Loader2, ListTree, Code2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import StoryDetailsFormatted from '../StoryDetailsFormatted';

const API_BASE = import.meta.env.VITE_API_BASE_URL || (
  window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000'
    : 'https://ba-agent-aqd8c3d8dtdrbcat.centralus-01.azurewebsites.net'
);

const CollapsibleEpic = ({ epic, epicIndex, epicsList, onToggleSelect, onMoveFeature }) => {
  const [isOpen, setIsOpen] = useState(true);
  const isSelected = epic.selected !== false;
  return (
    <div className="epic-node" style={{ marginBottom: '16px', border: '1px solid rgba(56, 189, 248, 0.2)', borderRadius: '8px', padding: '12px', background: 'rgba(30,41,59,0.7)', opacity: isSelected ? 1 : 0.5 }}>
      <div 
        className="node-title" 
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input type="checkbox" checked={isSelected} onChange={() => onToggleSelect(epic)} style={{ width: '18px', height: '18px', cursor: 'pointer' }} title="Include in ADO Sync" />
            <span style={{ background: 'rgba(59,130,246,0.2)', color: '#60a5fa', border: '1px solid #3b82f6', padding: '2px 8px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 'bold' }}>EPIC</span>
            <span style={{ fontSize: '1.1rem', color: '#fff', fontWeight: '600', cursor: 'pointer' }}  role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") e.currentTarget.click(); }} onClick={() => setIsOpen(!isOpen)}>{epic.title}</span>
        </span>
        <span style={{ fontSize: '0.8rem', opacity: 0.7, cursor: 'pointer' }}  role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") e.currentTarget.click(); }} onClick={() => setIsOpen(!isOpen)}>{isOpen ? '🔽 COLLAPSE' : '▶ EXPAND'}</span>
      </div>
      {isOpen && (
        <div style={{ paddingLeft: '20px', marginTop: '16px' }}>
          {epic.features?.map((feat, i) => (
              <CollapsibleFeature 
                  key={feat.id || i} 
                  feat={feat} 
                  epicIndex={epicIndex} 
                  featIndex={i} 
                  epicsList={epicsList} 
                  onToggleSelect={onToggleSelect} 
                  onMoveFeature={onMoveFeature} 
              />
          ))}
        </div>
      )}
    </div>
  );
};

const CollapsibleFeature = ({ feat, epicIndex, featIndex, epicsList, onToggleSelect, onMoveFeature }) => {
  const [isOpen, setIsOpen] = useState(true);
  const isSelected = feat.selected !== false;
  return (
    <div className="feat-node" style={{ marginBottom: '12px', borderLeft: '2px solid rgba(59,130,246,0.3)', paddingLeft: '12px', opacity: isSelected ? 1 : 0.5 }}>
      <div 
        className="node-title" 
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.95rem' }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <input type="checkbox" checked={isSelected} onChange={() => onToggleSelect(feat)} style={{ width: '16px', height: '16px', cursor: 'pointer' }} title="Include in ADO Sync" />
            <span style={{ background: 'rgba(139,92,246,0.2)', color: '#a78bfa', border: '1px solid #8b5cf6', padding: '2px 8px', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 'bold' }}>FEATURE</span>
            <span style={{ color: '#e2e8f0', fontWeight: '500', cursor: 'pointer' }}  role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") e.currentTarget.click(); }} onClick={() => setIsOpen(!isOpen)}>{feat.title}</span>
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <select 
                onChange={(e) => {
                    if (e.target.value !== "") onMoveFeature(epicIndex, featIndex, Number.parseInt(e.target.value, 10));
                    e.target.value = "";
                }} 
                style={{ background: 'rgba(0,0,0,0.5)', color: '#fff', border: '1px solid rgba(255,255,255,0.1)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', outline: 'none' }}
            >
                <option value="">Move to Epic...</option>
                {epicsList.map((e, idx) => (
                    <option key={idx} value={idx} disabled={idx === epicIndex}>
                        {e.title.length > 30 ? e.title.substring(0, 30) + '...' : e.title}
                    </option>
                ))}
            </select>
            <span style={{ fontSize: '0.8rem', opacity: 0.7, cursor: 'pointer' }}  role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") e.currentTarget.click(); }} onClick={() => setIsOpen(!isOpen)}>{isOpen ? '🔽' : '▶'}</span>
        </div>
      </div>
      {isOpen && (
        <div style={{ paddingLeft: '16px', marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {feat.user_stories?.map((story, i) => {
            const isStorySelected = story.selected !== false;
            return (
            <div key={story.id || i} className="story-node" style={{ padding: '12px', background: '#FFFFFF', border: '1px solid #CCFBF1', borderRadius: '8px', fontSize: '0.85rem', opacity: isStorySelected ? 1 : 0.5, boxShadow: '0 1px 3px rgba(0,0,0,0.03)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '0.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <input type="checkbox" checked={isStorySelected} onChange={() => onToggleSelect(story)} style={{ width: '14px', height: '14px', cursor: 'pointer' }} title="Include in ADO Sync" />
                    <span style={{ background: 'rgba(16,185,129,0.2)', color: '#059669', border: '1px solid #10b981', padding: '2px 6px', borderRadius: '6px', fontSize: '0.7rem', fontWeight: 'bold' }}>STORY</span>
                    <span style={{ fontWeight: '600', color: '#0f172a', fontSize: '0.95rem' }}>{story.title}</span>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {story.story_points && <span style={{ background: 'rgba(255,255,255,0.1)', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '500' }}>{story.story_points} pts</span>}
                    {story.moscow && <span style={{ background: 'rgba(245,158,11,0.15)', color: '#fbbf24', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '600' }}>{story.moscow}</span>}
                    {story.release_phase && <span style={{ background: 'rgba(236,72,153,0.15)', color: '#f472b6', padding: '2px 8px', borderRadius: '12px', fontSize: '0.75rem', fontWeight: '500' }}>{story.release_phase}</span>}
                </div>
              </div>
              <StoryDetailsFormatted story={story} />
            </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

const DirectBacklogView = () => {
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);
    const [isPublishing, setIsPublishing] = useState(false);
    const [publishSuccess, setPublishSuccess] = useState(false);
    const [result, setResult] = useState(null);
    const [activeTab, setActiveTab] = useState('backlog');
    const [exportTarget, setExportTarget] = useState('ado');

    const handleFileUpload = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
        }
    };

    const handleGenerate = async () => {
        if (!file) return;
        setLoading(true);
        setResult(null);

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${API_BASE}/generate-backlog-direct`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to generate backlog");
            }

            const data = await response.json();
            setResult(data);
            setLoading(false); // Unblock UI for Backlog

            // Background Test Case Generation
            try {
                const tcResponse = await fetch(`${API_BASE}/generate-testcases-direct`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ backlog: data.backlog })
                });
                
                if (tcResponse.ok) {
                    const tcData = await tcResponse.json();
                    setResult(prev => ({ ...prev, test_cases: tcData.test_cases }));
                } else {
                    setResult(prev => ({ ...prev, test_cases: "⚠️ Error generating test cases. The API failed." }));
                }
            } catch (err) {
                setResult(prev => ({ ...prev, test_cases: "⚠️ Connection to test case generator failed." }));
            }

        } catch (err) {
            alert(`Error: ${err.message}`);
            setLoading(false);
        }
    };

    const handleToggleSelect = (item) => {
        item.selected = item.selected === false ? true : false;
        setResult({ ...result });
    };

    const handleMoveFeature = (epicIndex, featIndex, targetEpicIndex) => {
        const feat = result.backlog.epics[epicIndex].features[featIndex];
        result.backlog.epics[epicIndex].features.splice(featIndex, 1);
        result.backlog.epics[targetEpicIndex].features = result.backlog.epics[targetEpicIndex].features || [];
        result.backlog.epics[targetEpicIndex].features.push(feat);
        setResult({ ...result });
    };

    const handlePublish = async () => {
        if (!result?.backlog) return;
        setIsPublishing(true);

        try {
            // Filter out unselected items
            const filteredEpics = result.backlog.epics.filter(e => e.selected !== false).map(epic => {
                const filteredFeatures = (epic.features || []).filter(f => f.selected !== false).map(feat => {
                    const filteredStories = (feat.user_stories || []).filter(s => s.selected !== false);
                    return { ...feat, user_stories: filteredStories };
                });
                return { ...epic, features: filteredFeatures };
            });

            const filteredBacklog = { epics: filteredEpics };

            const response = await fetch(`${API_BASE}/automate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ backlog: filteredBacklog, export_target: exportTarget })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to publish to ADO");
            }

            const data = await response.json();
            setPublishSuccess(true);
            alert(`Success! Synchronized ${data.created_items?.length || 0} work items to Azure DevOps.`);
        } catch (err) {
            alert(`Publish Error: ${err.message}`);
        } finally {
            setIsPublishing(false);
        }
    };

    return (
        <div className="view-container slide-in">
            <div className="view-header">
                <h2>Quick Backlog Generator</h2>
                <p>Upload a raw Business Requirements Document (BRD) to instantly generate an ADO hierarchy and Test Cases.</p>
            </div>

            {!result && !loading && (
                <div 
                    className="glass-panel upload-zone-large slide-up" 
                    style={{ 
                        marginTop: '3rem', 
                        textAlign: 'center', 
                        padding: '5rem 3rem',
                        background: 'linear-gradient(145deg, rgba(15,23,42,0.6) 0%, rgba(30,41,59,0.4) 100%)',
                        border: '1px solid rgba(56, 189, 248, 0.2)',
                        boxShadow: '0 20px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)',
                        borderRadius: '24px',
                        position: 'relative',
                        overflow: 'hidden'
                    }}
                >
                    {/* Glowing background orb */}
                    <div style={{ position: 'absolute', top: '-50%', left: '50%', transform: 'translateX(-50%)', width: '300px', height: '300px', background: 'radial-gradient(circle, rgba(56,189,248,0.15) 0%, rgba(0,0,0,0) 70%)', zIndex: 0, pointerEvents: 'none' }}></div>
                    
                    <div style={{ position: 'relative', zIndex: 1 }}>
                        <UploadCloud size={72} style={{ color: 'var(--primary)', marginBottom: '1.5rem', filter: 'drop-shadow(0 0 12px rgba(56,189,248,0.5))' }} />
                        <h3 style={{ fontSize: '1.8rem', fontWeight: '600', marginBottom: '0.5rem', background: 'linear-gradient(to right, #fff, #a5d6ff)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Drag & Drop your BRD here</h3>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '2.5rem', fontSize: '1.1rem' }}>Supports PDF, DOCX, TXT</p>
                    
                    <input 
                        type="file" 
                        id="direct-file-upload" 
                        style={{ display: 'none' }} 
                        onChange={handleFileUpload} 
                        accept=".pdf,.txt,.docx"
                    />
                    <label htmlFor="direct-file-upload" className="btn-primary" style={{ display: 'inline-flex', cursor: 'pointer' }}>
                        Browse Files
                    </label>

                    {file && (
                        <div className="slide-up" style={{ marginTop: '3rem', padding: '2rem', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem', boxShadow: '0 10px 30px rgba(0,0,0,0.3)' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div style={{ background: 'linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))', padding: '1rem', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                    <FileText size={24} color="#000" />
                                </div>
                                <div style={{ textAlign: 'left' }}>
                                    <h4 style={{ fontSize: '1.2rem', margin: 0, fontWeight: '600' }}>{file.name}</h4>
                                    <p style={{ margin: 0, color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.2rem', fontSize: '0.9rem', marginTop: '0.25rem' }}>
                                        <CheckCircle size={14} /> Ready for Architecture
                                    </p>
                                </div>
                            </div>
                            <div style={{ width: '100%', height: '1px', background: 'rgba(255,255,255,0.1)' }}></div>
                            <button className="btn-primary" onClick={handleGenerate} style={{ padding: '0.8rem 2rem', fontSize: '1.1rem', borderRadius: '50px' }}>
                                ✨ Generate Backlog & Tests
                            </button>
                        </div>
                    )}
                    </div>
                </div>
            )}

            {loading && (
                <div className="loading-state glass-panel pulse" style={{ marginTop: '3rem', padding: '5rem', textAlign: 'center', borderRadius: '24px', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                    <Loader2 className="spinner" size={64} style={{ color: 'var(--primary)', margin: '0 auto 2rem', filter: 'drop-shadow(0 0 10px rgba(56,189,248,0.8))' }} />
                    <h3 style={{ fontSize: '1.5rem', color: '#fff', marginBottom: '0.5rem' }}>Analyzing Requirements & Architecting Backlog...</h3>
                    <p style={{ color: 'var(--primary)', opacity: 0.8 }}>Bypassing deep analysis phase for maximum velocity.</p>
                </div>
            )}

            {result && !loading && (
                <div className="result-container slide-up" style={{ marginTop: '2rem' }}>
                    <div className="modern-tabs slide-in" style={{ display: 'flex', gap: '0.5rem', background: 'rgba(15,23,42,0.6)', padding: '0.5rem', borderRadius: '16px', width: 'fit-content', border: '1px solid rgba(255,255,255,0.05)', marginBottom: '2rem', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' }}>
                        <button 
                            onClick={() => setActiveTab('backlog')}
                            style={{ background: activeTab === 'backlog' ? 'var(--primary)' : 'transparent', border: 'none', color: activeTab === 'backlog' ? '#0f172a' : 'var(--text-secondary)', padding: '0.8rem 1.5rem', borderRadius: '12px', fontSize: '1rem', cursor: 'pointer', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem', transition: 'all 0.3s ease' }}
                        >
                            <ListTree size={18} /> ADO Backlog
                        </button>
                        <button 
                            onClick={() => setActiveTab('tests')}
                            style={{ background: activeTab === 'tests' ? 'var(--primary)' : 'transparent', border: 'none', color: activeTab === 'tests' ? '#0f172a' : 'var(--text-secondary)', padding: '0.8rem 1.5rem', borderRadius: '12px', fontSize: '1rem', cursor: 'pointer', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem', transition: 'all 0.3s ease' }}
                        >
                            <Code2 size={18} /> QA Test Cases
                        </button>
                    </div>

                    <div className="tab-content">
                        {activeTab === 'backlog' && (
                            <div className="glass-panel" style={{ padding: '2rem', background: 'rgba(15,23,42,0.4)', borderRadius: '16px' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                                    {!result.backlog?.epics && !result.backlog?.features ? (
                                        <div style={{ color: 'var(--text-secondary)' }}>No backlog data found.</div>
                                    ) : (
                                        <>
                                            {(() => {
                                                let eCount = result.backlog.epics?.length || 0;
                                                let fCount = 0, sCount = 0, tCount = 0;
                                                const featuresToCount = result.backlog.epics 
                                                    ? result.backlog.epics.flatMap(e => e.features || []) 
                                                    : (result.backlog.features || []);

                                                fCount = featuresToCount.length;
                                                featuresToCount.forEach(f => {
                                                    f.user_stories?.forEach(s => {
                                                        sCount++;
                                                        if (s.tasks) tCount += s.tasks.length;
                                                    });
                                                });
                                                
                                                return (
                                                  <div className="backlog-metrics-boxes" style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
                                                    <div style={{ background: 'rgba(30,41,59,0.5)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px', textAlign: 'center' }}>
                                                      <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#60a5fa' }}>{eCount}</div>
                                                      <div style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>Epics</div>
                                                    </div>
                                                    <div style={{ background: 'rgba(30,41,59,0.5)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px', textAlign: 'center' }}>
                                                      <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#a78bfa' }}>{fCount}</div>
                                                      <div style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>Features</div>
                                                    </div>
                                                    <div style={{ background: 'rgba(30,41,59,0.5)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px', textAlign: 'center' }}>
                                                      <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#34d399' }}>{sCount}</div>
                                                      <div style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>User Stories</div>
                                                    </div>
                                                    <div style={{ background: 'rgba(30,41,59,0.5)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', padding: '16px', textAlign: 'center' }}>
                                                      <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#f472b6' }}>{tCount}</div>
                                                      <div style={{ fontSize: '0.8rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '1px' }}>Tasks</div>
                                                    </div>
                                                  </div>
                                                );
                                            })()}

                                            <div className="backlog-explorer" style={{ maxHeight: '600px', overflowY: 'auto', paddingRight: '12px' }}>
                                                {result.backlog.epics ? (
                                                    result.backlog.epics.map((epic, i) => (
                                                        <CollapsibleEpic 
                                                            key={epic.id || i} 
                                                            epic={epic} 
                                                            epicIndex={i} 
                                                            epicsList={result.backlog.epics} 
                                                            onToggleSelect={handleToggleSelect} 
                                                            onMoveFeature={handleMoveFeature} 
                                                        />
                                                    ))
                                                ) : (
                                                    result.backlog.features?.map((feat, i) => (
                                                        <CollapsibleFeature 
                                                            key={feat.id || i} 
                                                            feat={feat} 
                                                            epicIndex={0} 
                                                            featIndex={i} 
                                                            epicsList={[]} 
                                                            onToggleSelect={handleToggleSelect} 
                                                            onMoveFeature={handleMoveFeature} 
                                                        />
                                                    ))
                                                )}
                                            </div>
                                        </>
                                    )}
                                </div>
                            </div>
                        )}

                        {activeTab === 'tests' && (
                            <div className="glass-panel markdown-body" style={{ padding: '2rem' }}>
                                {typeof result.test_cases === 'string' ? (
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.test_cases}</ReactMarkdown>
                                ) : (
                                    <pre style={{ margin: 0, color: '#a5d6ff', fontSize: '0.9rem' }}>
                                        {JSON.stringify(result.test_cases, null, 2)}
                                    </pre>
                                )}
                            </div>
                        )}
                    </div>

                    <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <button className="btn-secondary" onClick={() => { setResult(null); setFile(null); }}>
                            Start Over
                        </button>
                        
                        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: 'rgba(255,255,255,0.05)', padding: '0.5rem 1rem', borderRadius: '8px' }}>
                                <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Destination:</span>
                                <select 
                                    value="ado"
                                    disabled
                                    style={{ background: 'transparent', border: 'none', color: '#fff', fontSize: '0.95rem', fontWeight: '500', outline: 'none' }}
                                >
                                    <option value="ado" style={{ color: '#000' }}>Azure DevOps</option>
                                </select>
                            </div>

                            <button className="btn-primary" onClick={handlePublish} disabled={isPublishing || publishSuccess} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                {isPublishing ? <Loader2 size={16} className="spin" /> : <img src="/assets/icons/Azure-DevOps.png" width="18" height="18" alt="ADO" style={{ verticalAlign: 'middle' }} />}
                                {isPublishing ? 'Publishing...' : publishSuccess ? '✨ Published to ADO!' : 'Publish to Azure DevOps'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default DirectBacklogView;
