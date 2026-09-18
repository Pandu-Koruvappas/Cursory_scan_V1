import React, { useState, useEffect } from 'react';
import { Layers, Calendar, ChevronRight, Zap, Target, Edit2, AlertCircle } from 'lucide-react';

const API_BASE = "http://127.0.0.1:8000";

const SprintPlannerView = () => {
    const [backlog, setBacklog] = useState([]);
    const [sprints, setSprints] = useState([]);
    const [selectedSprint, setSelectedSprint] = useState(null);
    const [sprintItems, setSprintItems] = useState([]);
    
    // Capacity Goals
    const [targetHours, setTargetHours] = useState(80);
    const [targetPoints, setTargetPoints] = useState(40);
    
    // Calculated metrics
    const [currentPoints, setCurrentPoints] = useState(0);
    const [currentHours, setCurrentHours] = useState(0);
    
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        // For demonstration, we'll mock the ADO fetch and state if backend isn't ready
        // In a real flow, these would be fetch calls to our new endpoints.
        fetchPlannerData();
    }, []);

    const fetchPlannerData = async () => {
        setIsLoading(true);
        try {
            const [backlogRes, sprintsRes] = await Promise.all([
                fetch(`${API_BASE}/api/sprint-planning/backlog`),
                fetch(`${API_BASE}/api/sprint-planning/iterations`)
            ]);
            
            const backlogData = await backlogRes.json();
            const sprintsData = await sprintsRes.json();
            
            setBacklog(backlogData.items || []);
            setSprints(sprintsData.iterations || []);
            
            if (sprintsData.iterations && sprintsData.iterations.length > 0) {
                // Set the default selected sprint path
                setSelectedSprint(sprintsData.iterations[0].path);
            }
            
            setSprintItems([]);
            setCurrentPoints(0);
            setCurrentHours(0);
        } catch (e) {
            console.error("Error fetching planner data:", e);
        } finally {
            setIsLoading(false);
        }
    };

    const moveToSprint = (story) => {
        setBacklog(backlog.filter(b => b.id !== story.id));
        setSprintItems([...sprintItems, story]);
        updateMetrics([...sprintItems, story]);
    };

    const moveToBacklog = (story) => {
        setSprintItems(sprintItems.filter(s => s.id !== story.id));
        setBacklog([...backlog, story]);
        updateMetrics(sprintItems.filter(s => s.id !== story.id));
    };

    const updateMetrics = (items) => {
        const pts = items.reduce((sum, i) => sum + (i.points || 0), 0);
        const hrs = items.reduce((sum, i) => sum + (i.hours || 0), 0);
        setCurrentPoints(pts);
        setCurrentHours(hrs);
    };

    const handleAutoSuggest = () => {
        setIsLoading(true);
        setTimeout(() => {
            // Sort backlog by points descending just to mock AI logic fitting into 80 hrs
            let available = [...backlog, ...sprintItems];
            let newSprint = [];
            let newBacklog = [];
            let hrs = 0;
            
            for (let story of available) {
                if (hrs + story.hours <= targetHours) {
                    newSprint.push(story);
                    hrs += story.hours;
                } else {
                    newBacklog.push(story);
                }
            }
            
            setSprintItems(newSprint);
            setBacklog(newBacklog);
            updateMetrics(newSprint);
            setIsLoading(false);
        }, 1200);
    };

    const handleSavePlan = async () => {
        if (!selectedSprint) {
            alert("Please select a target sprint first.");
            return;
        }
        
        setIsSaving(true);
        try {
            const res = await fetch(`${API_BASE}/api/sprint-planning/assign`, { 
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    sprint_path: selectedSprint, 
                    items: sprintItems.map(s => s.id) 
                }) 
            });
            const data = await res.json();
            
            if (res.ok) {
                alert(`Successfully synced ${data.updated_count} stories to ADO!`);
                // Clear the sprint items since they are now assigned in ADO
                // (Alternatively, we could re-fetch data)
                setSprintItems([]);
                setCurrentPoints(0);
                setCurrentHours(0);
            } else {
                alert(`Error syncing: ${data.detail || JSON.stringify(data)}`);
            }
        } catch (e) {
            console.error("Error saving plan:", e);
            alert("Failed to sync plan to ADO.");
        } finally {
            setIsSaving(false);
        }
    };

    const pointsPct = Math.min((currentPoints / targetPoints) * 100, 100);
    const hoursPct = Math.min((currentHours / targetHours) * 100, 100);

    return (
        <div className="view-container slide-in">
            <div className="view-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div>
                    <h2>Agile Sprint Planner</h2>
                    <p>Assign backlog items to sprints and monitor real-time capacity and velocity.</p>
                </div>
                <button className="btn-primary" onClick={handleSavePlan} disabled={isSaving || sprintItems.length === 0}>
                    {isSaving ? "Syncing to ADO..." : "💾 Sync Plan to ADO"}
                </button>
            </div>

            <div className="sprint-planner-board" style={{ display: 'flex', gap: '24px', height: 'calc(100vh - 180px)' }}>
                
                {/* LEFT PANE: BACKLOG */}
                <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                            <Layers size={20} color="var(--accent-primary)" /> Unassigned Backlog
                        </h3>
                        <span className="badge">{backlog.length} items</span>
                    </div>
                    
                    <div className="search-bar" style={{ marginBottom: '16px' }}>
                        <input type="text" placeholder="Search backlog..." style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', background: 'var(--primary-bg)', border: '1px solid var(--glass-border)', color: 'var(--text-main)' }} />
                    </div>

                    <div style={{ overflowY: 'auto', flex: 1, paddingRight: '8px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {isLoading && backlog.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>Loading Backlog from ADO...</div>
                        ) : backlog.map(story => (
                            <div key={story.id} className="story-card" style={{ background: 'var(--primary-bg)', border: '1px solid var(--glass-border)', borderRadius: '8px', padding: '12px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>#{story.id}</span>
                                    <div style={{ display: 'flex', gap: '8px' }}>
                                        <span className="badge" style={{ background: 'rgba(0, 242, 255, 0.1)', color: 'var(--accent-primary)' }}>{story.points} pts</span>
                                        <span className="badge" style={{ background: 'rgba(255, 171, 0, 0.1)', color: '#ffab00' }}>{story.hours} hrs</span>
                                    </div>
                                </div>
                                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.95rem' }}>{story.title}</h4>
                                <button className="btn-ghost" style={{ width: '100%', justifyContent: 'center', padding: '6px' }} onClick={() => moveToSprint(story)}>
                                    Move to Sprint <ChevronRight size={16} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* RIGHT PANE: SPRINT PLAN */}
                <div className="glass-card" style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '20px', borderTop: '4px solid var(--accent-primary)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
                            <Calendar size={20} color="var(--accent-primary)" /> 
                            <select 
                                value={selectedSprint || ''} 
                                onChange={(e) => setSelectedSprint(e.target.value)}
                                style={{ background: 'transparent', color: 'var(--text-main)', border: 'none', fontSize: '1.2rem', fontWeight: 'bold', outline: 'none' }}
                            >
                                {sprints.map(s => <option key={s.id} value={s.id} style={{background: 'var(--primary-bg)'}}>{s.name}</option>)}
                            </select>
                        </h3>
                        <button className="btn-secondary mini" onClick={handleAutoSuggest}>
                            <Zap size={14} style={{ marginRight: '4px' }} /> Auto-Suggest (AI)
                        </button>
                    </div>

                    {/* Capacity Trackers */}
                    <div style={{ background: 'var(--primary-bg)', borderRadius: '8px', padding: '16px', marginBottom: '20px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.9rem' }}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Target size={14} /> <strong>Hours Capacity</strong></span>
                            <span>{currentHours} / {targetHours} hrs {currentHours > targetHours && <AlertCircle size={14} color="var(--error)" style={{marginLeft: '4px'}} />}</span>
                        </div>
                        <div style={{ width: '100%', height: '8px', background: 'var(--glass-bg)', borderRadius: '4px', overflow: 'hidden', marginBottom: '16px' }}>
                            <div style={{ height: '100%', width: `${hoursPct}%`, background: currentHours > targetHours ? 'var(--error)' : '#ffab00', transition: 'width 0.3s ease' }}></div>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px', fontSize: '0.9rem' }}>
                            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><Target size={14} /> <strong>Story Points Velocity</strong></span>
                            <span>{currentPoints} / {targetPoints} pts {currentPoints > targetPoints && <AlertCircle size={14} color="var(--error)" style={{marginLeft: '4px'}} />}</span>
                        </div>
                        <div style={{ width: '100%', height: '8px', background: 'var(--glass-bg)', borderRadius: '4px', overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${pointsPct}%`, background: currentPoints > targetPoints ? 'var(--error)' : 'var(--accent-primary)', transition: 'width 0.3s ease' }}></div>
                        </div>
                    </div>

                    <div style={{ overflowY: 'auto', flex: 1, paddingRight: '8px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {sprintItems.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-muted)' }}>
                                <div style={{ fontSize: '3rem', marginBottom: '16px', opacity: 0.2 }}>📥</div>
                                <p>No stories assigned to this sprint yet.</p>
                                <p style={{ fontSize: '0.9rem' }}>Move items from the backlog or use Auto-Suggest.</p>
                            </div>
                        ) : sprintItems.map(story => (
                            <div key={story.id} className="story-card sprint-item" style={{ background: 'var(--primary-bg)', border: '1px solid var(--glass-border)', borderLeft: '3px solid var(--accent-primary)', borderRadius: '8px', padding: '12px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>#{story.id}</span>
                                    <button className="btn-ghost mini" style={{ padding: '2px 8px' }} onClick={() => moveToBacklog(story)}>Remove ✕</button>
                                </div>
                                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.95rem' }}>{story.title}</h4>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                    <span className="badge" style={{ background: 'rgba(0, 242, 255, 0.1)', color: 'var(--accent-primary)' }}>{story.points} pts</span>
                                    <span className="badge" style={{ background: 'rgba(255, 171, 0, 0.1)', color: '#ffab00' }}>{story.hours} hrs</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SprintPlannerView;
