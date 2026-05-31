CREATE TABLE customers (
    customer_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    industry TEXT,
    account_manager TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE issues (
    issue_id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    priority TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE issue_updates (
    update_id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES issues(issue_id) ON DELETE CASCADE,
    update_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE next_actions (
    action_id SERIAL PRIMARY KEY,
    issue_id INTEGER NOT NULL REFERENCES issues(issue_id) ON DELETE CASCADE,
    action_text TEXT NOT NULL,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO customers (name, industry, account_manager)
VALUES
('Client X', 'Financial Services', 'Alice'),
('Client Y', 'Retail', 'Bob'),
('Client Z', 'Healthcare', 'Charlie');

INSERT INTO issues (customer_id, title, status, priority)
VALUES
(1, 'Delayed onboarding', 'open', 'high'),
(1, 'API integration failure', 'open', 'critical'),
(2, 'Billing discrepancy', 'open', 'medium'),
(3, 'Data sync issue', 'in_progress', 'high'),
(3, 'User training request', 'closed', 'low');

INSERT INTO issue_updates (issue_id, update_text)
VALUES
(1, 'Customer reported onboarding delay last week.'),
(1, 'Support team is waiting for missing configuration details.'),
(2, 'Integration fails during authentication step.'),
(3, 'Invoice amount disputed by customer.');