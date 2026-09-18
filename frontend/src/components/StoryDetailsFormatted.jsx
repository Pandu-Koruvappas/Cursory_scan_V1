import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export const StoryDetailsFormatted = ({ story }) => {
  if (!story) return null;

  let rawDesc = story.description || '';
  const rawAC = story.acceptance_criteria;

  // Extract clean INVEST statement "As a..." ONLY (strip Business Context, Workflow Impact, etc.)
  let storyStatement = rawDesc;
  let match = rawDesc.match(/As\s+an?\s+[^\s,.][^,.]*,\s*I\s+want\s+to\s+[^\s,.][^,.]*,\s*so\s+that\s+[^\s.\n][^.\n]*/i);
  
  if (!match) {
    const fallbackMatch = rawDesc.match(/As\s+an?\s+/i);
    if (fallbackMatch) {
      const sub = rawDesc.substring(fallbackMatch.index);
      const endMatch = sub.match(/\n\n|\*\*/);
      match = [endMatch ? sub.substring(0, endMatch.index) : sub];
    }
  }

  if (match) {
    storyStatement = match[0].trim();
  }
  storyStatement = storyStatement.replaceAll(/\*\*\s*(?:User Story|Description|User Story Statement)[^*]*\*\*:?/gi, '').trim();

  let extractedACText = '';

  // Separate Acceptance Criteria if embedded inside description
  const acMatch = rawDesc.match(/\*\*\s*Acceptance Criteria[^*]*\*\*:?/i) || rawDesc.match(/Acceptance Criteria\s*\([^)]*\):?/i);
  if (acMatch) {
    const splitIdx = rawDesc.indexOf(acMatch[0]);
    extractedACText = rawDesc.substring(splitIdx + acMatch[0].length).trim();
  }

  // Parse extracted AC text into structured blocks/scenarios
  let extractedACItems = [];
  if (extractedACText) {
    // Split by Scenario or double newline
    extractedACItems = extractedACText
      .split(/(?=\bScenario\s*\d+:|\*\*Scenario\s*\d+:|\n\n)/i)
      .map(s => s.trim())
      .filter(Boolean);
  }

  // Normalize explicit acceptance_criteria property
  let explicitACItems = [];
  if (Array.isArray(rawAC) && rawAC.length > 0) {
    explicitACItems = rawAC.map(item => typeof item === 'string' ? item.trim() : JSON.stringify(item)).filter(Boolean);
  } else if (typeof rawAC === 'string' && rawAC.trim()) {
    explicitACItems = rawAC.split('\n').map(s => s.trim()).filter(Boolean);
  }

  // Combine all AC items
  const allACItems = [...explicitACItems, ...extractedACItems];

  // Helper to format Gherkin text with keyword badges
  const renderGherkinText = (text) => {
    // Clean up asterisks if any
    const cleaned = text.replaceAll('**', '');
    const lines = cleaned.split('\n').filter(Boolean);

    return lines.map((line, lIdx) => {
      const trimmed = line.trim();
      const match = trimmed.match(/^(Given|When|Then|And|Scenario\s*\d+:?)(.*)/i);

      if (match) {
        const keyword = match[1].trim();
        const rest = match[2];
        const lowerKw = keyword.toLowerCase();

        if (lowerKw.startsWith('scenario')) {
          return (
            <div key={lIdx} className="ac-scenario-header">
              📌 <strong>{keyword}{rest}</strong>
            </div>
          );
        }

        let kwClass = 'and';
        if (lowerKw === 'given') kwClass = 'given';
        else if (lowerKw === 'when') kwClass = 'when';
        else if (lowerKw === 'then') kwClass = 'then';

        return (
          <div key={lIdx} className="ac-gherkin-line">
            <span className={`ac-kw ${kwClass}`}>{keyword.toUpperCase()}</span>
            <span>{rest}</span>
          </div>
        );
      }

      return (
        <div key={lIdx} className="ac-plain-line">
          {line}
        </div>
      );
    });
  };

  return (
    <div className="story-details-container">
      {storyStatement && (
        <div className="story-desc-markdown">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{storyStatement}</ReactMarkdown>
        </div>
      )}

      {allACItems.length > 0 && (
        <div className="ac-section">
          <div className="ac-section-header">
            <span className="ac-icon">📋</span>
            <h6>Acceptance Criteria</h6>
          </div>
          <div className="ac-list-container">
            {allACItems.map((acItem, idx) => (
              <div key={idx} className="ac-item-card">
                {renderGherkinText(acItem)}
              </div>
            ))}
          </div>
        </div>
      )}

      {story.tasks && story.tasks.length > 0 && (
        <div className="story-tasks-section">
          <div className="tasks-header">
            <span>⚙️ Development Tasks</span>
          </div>
          <div className="tasks-list">
            {story.tasks.map((task, tIdx) => (
              <div key={tIdx} className="node task">
                <div className="node-head">
                  <span className="node-tag">TASK</span>
                  <span className="node-title">{typeof task === 'string' ? task : (task.title || JSON.stringify(task))}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StoryDetailsFormatted;
