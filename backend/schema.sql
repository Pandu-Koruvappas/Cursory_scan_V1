-- BA Agent Pro: Database Schema

CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) -- e.g., 'ingested', 'analyzed', 'trd_generated', 'backlog_synced'
);

CREATE TABLE requirements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    req_id VARCHAR(50), -- e.g., 'REQ-001'
    description TEXT,
    req_type VARCHAR(50), -- 'functional', 'non-functional', 'business_rule'
    source_document VARCHAR(255)
);

CREATE TABLE trds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    content TEXT, -- Markdown content
    version INTEGER DEFAULT 1
);

CREATE TABLE backlog_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID REFERENCES workflows(id),
    ado_id INTEGER, -- ID from Azure DevOps
    title VARCHAR(255),
    item_type VARCHAR(50), -- 'Epic', 'Feature', 'Story', 'Task'
    parent_id UUID REFERENCES backlog_items(id)
);
