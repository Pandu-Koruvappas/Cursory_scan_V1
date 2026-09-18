import React, { useState, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronRight, Search, Maximize2, Minimize2, CheckCircle, FileText } from 'lucide-react';

export default function FunctionalSpecAccordionViewer({ content }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [openSections, setOpenSections] = useState({});
  const [allExpanded, setAllExpanded] = useState(true);
  const [hideNFR, setHideNFR] = useState(false);

  const extractRawString = (src) => {
    if (!src) return '';
    if (typeof src === 'string') return src;
    if (typeof src === 'object') {
      if (typeof src.functional_spec === 'string') return src.functional_spec;
      if (typeof src.master_spec === 'string') return src.master_spec;
      if (typeof src.spec === 'string') return src.spec;
      if (typeof src.text === 'string') return src.text;
    }
    return JSON.stringify(src, null, 2);
  };

  const rawText = extractRawString(content);

  // Convert FR-xxx tags into REQ-xxx tags strictly in the frontend display
  const formattedText = useMemo(() => {
    if (!rawText) return '';
    return rawText
      .replace(/\bFR([-\s]?\d+)\b/gi, 'REQ$1')
      .replace(/\[FR([-\s]?\d+)\]/gi, '[REQ$1]')
      .replace(/FR-(\d+)/gi, 'REQ-$1');
  }, [rawText]);

  // Parse markdown content into structured sections based on top-level h1 / h2 headings
  const parsedSections = useMemo(() => {
    if (!formattedText) return [];

    const lines = formattedText.split('\n');
    const sections = [];
    let currentSection = null;

    lines.forEach((line) => {
      // Do NOT split sub-modules (e.g. "## 3.1", "### 3.2", "## Module 1") into new accordion boxes
      const isSubModuleHeading = line.match(/^#{1,3}\s+(?:3\.\d+|\d+\.\d+|Module|Building|INTAKE|PREFILL|CONDITIONAL|DESCRIPTION)/i);
      const isTopHeading = !isSubModuleHeading && line.match(/^#{1,2}\s+(?:\d+\.|\bExecutive\b|\bWorkflow\b|\bDetailed\b|\bSpecific\b|\bNon-Functional\b|\bValidated\b|\bIntegration\b|\bArchitect\b)/i);

      if (isTopHeading) {
        if (currentSection && (currentSection.contentLines.length > 0 || currentSection.title)) {
          sections.push(currentSection);
        }
        const titleText = isTopHeading[1] ? isTopHeading[1].trim() : isTopHeading[0].replace(/^#{1,2}\s+/, '').trim();
        currentSection = {
          id: `sec-${sections.length + 1}`,
          title: titleText,
          contentLines: [line],
          reqCount: 0
        };
      } else {
        if (!currentSection) {
          currentSection = {
            id: `sec-1`,
            title: '1. Executive Summary & Overview',
            contentLines: [line],
            reqCount: 0
          };
        } else {
          currentSection.contentLines.push(line);
        }
      }
    });

    if (currentSection && (currentSection.contentLines.length > 0 || currentSection.title)) {
      sections.push(currentSection);
    }

    return sections.map(sec => {
      const text = sec.contentLines.join('\n');
      const reqMatches = text.match(/\[?REQ[-\s]?\d+\]?/gi) || [];
      const uniqueREQ = new Set(reqMatches.map(m => m.toUpperCase().replace(/[\[\]\s]/g, '').replace('REQ', 'REQ-').replace('REQ--', 'REQ-')));
      return {
        ...sec,
        text,
        frCount: uniqueREQ.size
      };
    });
  }, [formattedText]);

  // Custom Markdown components to strictly strip 4th & 5th table columns in frontend
  const markdownComponents = useMemo(() => ({
    tr: ({ node, children, ...props }) => {
      const childArray = React.Children.toArray(children);
      const elementCells = childArray.filter(child => React.isValidElement(child));
      // Keep only Column 1 (Req ID), Column 2 (Req Name), Column 3 (Description) -> Drop 4th and 5th columns
      const filteredCells = elementCells.filter((_, idx) => idx < 3);
      return <tr {...props}>{filteredCells}</tr>;
    }
  }), []);

  // Filter sections by search term and NFR toggle
  const filteredSections = useMemo(() => {
    let sections = parsedSections;
    if (hideNFR) {
      sections = sections.filter(sec => !sec.title.toLowerCase().includes('non-functional') && !sec.title.toLowerCase().includes('nfr'));
    }
    if (!searchTerm.trim()) return sections;
    const term = searchTerm.toLowerCase();
    return sections.filter(sec => 
      sec.title.toLowerCase().includes(term) || sec.text.toLowerCase().includes(term)
    );
  }, [parsedSections, searchTerm, hideNFR]);

  const toggleSection = (id) => {
    setOpenSections(prev => ({
      ...prev,
      [id]: prev[id] === undefined ? false : !prev[id]
    }));
  };

  const handleToggleAll = () => {
    const nextState = !allExpanded;
    setAllExpanded(nextState);
    const newOpen = {};
    parsedSections.forEach(s => { newOpen[s.id] = nextState; });
    setOpenSections(newOpen);
  };

  const totalFRs = useMemo(() => {
    if (!formattedText) return 0;
    const allMatches = formattedText.match(/\[?REQ[-\s]?\d+\]?/gi) || [];
    const globalUnique = new Set(allMatches.map(m => m.toUpperCase().replace(/[\[\]\s]/g, '').replace('REQ', 'REQ-').replace('REQ--', 'REQ-')));
    return Math.max(globalUnique.size, parsedSections.reduce((acc, s) => acc + s.frCount, 0));
  }, [formattedText, parsedSections]);

  // Helper to deduplicate table header rows and separator lines inside Section 3
  const deduplicateTableHeaders = (text) => {
    if (!text) return '';
    const lines = text.split('\n');
    const cleanLines = [];
    let headerSeen = false;

    for (let line of lines) {
      const isHeaderRow = line.includes('Requirement ID') || line.includes('Requirement Name');
      const isSeparatorRow = /^\|\s*:?-+:?\s*\|\s*:?-+:?\s*\|/.test(line);

      if (isHeaderRow) {
        if (headerSeen) continue; // Skip duplicate table header row
        headerSeen = true;
      } else if (isSeparatorRow && headerSeen) {
        // Skip duplicate separator line if header was already seen
        const lastLine = cleanLines[cleanLines.length - 1] || '';
        if (!lastLine.includes('Requirement ID') && !lastLine.includes('Requirement Name')) {
          continue;
        }
      }
      cleanLines.push(line);
    }
    return cleanLines.join('\n');
  };

  return (
    <div className="functional-spec-accordion-container" style={{ color: '#1e293b', background: '#ffffff', padding: '16px', borderRadius: '12px' }}>
      {/* Top Toolbar with Search & Accordion Controls */}
      <div className="spec-toolbar" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        marginBottom: '16px',
        background: '#f8fafc',
        borderRadius: '10px',
        border: '1px solid #e2e8f0',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: '1', minWidth: '240px' }}>
          <Search size={18} color="#64748b" />
          <input
            type="text"
            placeholder="Search REQ ID (e.g. REQ-001) or keyword..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: '100%',
              padding: '8px 12px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              fontSize: '0.85rem',
              outline: 'none'
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.82rem', color: '#475569', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={!hideNFR}
              onChange={(e) => setHideNFR(!e.target.checked)}
              style={{ accentColor: '#2563eb', cursor: 'pointer' }}
            />
            {' '}Include NFR Section
          </label>

          <button
            onClick={handleToggleAll}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid #cbd5e1',
              background: '#ffffff',
              fontSize: '0.82rem',
              color: '#334155',
              cursor: 'pointer',
              fontWeight: '500'
            }}
          >
            {allExpanded ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            {allExpanded ? 'Collapse All' : 'Expand All'}
          </button>
        </div>
      </div>

      {/* Accordion Sections Stack */}
      <div className="spec-sections-stack" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {filteredSections.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: '#64748b', fontSize: '0.9rem' }}>
            No matching functional requirement sections found.
          </div>
        ) : (
          filteredSections.map((sec) => {
            const isOpen = openSections[sec.id] !== undefined ? openSections[sec.id] : allExpanded;
            const isDetailedSection = sec.title.toLowerCase().includes('detailed functional requirements') || sec.title.toLowerCase().includes('specific functional requirements');
            
            return (
              <div
                key={sec.id}
                className="spec-accordion-item"
                style={{
                  borderRadius: '10px',
                  border: '1px solid #e2e8f0',
                  overflow: 'hidden',
                  background: '#ffffff',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                  transition: 'all 0.2s ease'
                }}
              >
                {/* Accordion Header */}
                <div
                  className="spec-accordion-header"
                   role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") e.currentTarget.click(); }} onClick={() => toggleSection(sec.id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '14px 18px',
                    cursor: 'pointer',
                    background: isOpen ? '#f1f5f9' : '#f8fafc',
                    borderBottom: isOpen ? '1px solid #e2e8f0' : 'none',
                    userSelect: 'none'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {isOpen ? <ChevronDown size={18} color="#2563eb" /> : <ChevronRight size={18} color="#64748b" />}
                    <span style={{ fontWeight: '600', fontSize: '0.95rem', color: '#0f172a' }}>
                      {sec.title}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {sec.frCount > 0 && (
                      <span style={{
                        fontSize: '0.75rem',
                        padding: '2px 8px',
                        borderRadius: '12px',
                        background: '#ecfdf5',
                        color: '#047857',
                        border: '1px solid #a7f3d0',
                        fontWeight: '600'
                      }}>
                        {sec.frCount} REQs
                      </span>
                    )}
                  </div>
                </div>

                {/* Accordion Content Body inside Single Consolidated Box */}
                {isOpen && (
                  <div
                    className="spec-accordion-body"
                    style={{
                      padding: '18px 22px',
                      background: isDetailedSection ? '#f8fafc' : '#ffffff',
                      color: '#0f172a',
                      fontSize: '0.9rem',
                      lineHeight: '1.6'
                    }}
                  >
                    <article className="doc-content markdown-body" style={{
                      color: '#0f172a',
                      background: '#ffffff',
                      padding: isDetailedSection ? '20px' : '0',
                      borderRadius: isDetailedSection ? '10px' : '0',
                      border: isDetailedSection ? '1px solid #e2e8f0' : 'none'
                    }}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                        {deduplicateTableHeaders(sec.text)}
                      </ReactMarkdown>
                    </article>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
