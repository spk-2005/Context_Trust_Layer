CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    account_name VARCHAR(100) NOT NULL UNIQUE,
    balance NUMERIC(12, 2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE transactions (
    tx_id UUID PRIMARY KEY,
    account_id INT NOT NULL REFERENCES accounts(id),
    amount NUMERIC(12, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending'
);
