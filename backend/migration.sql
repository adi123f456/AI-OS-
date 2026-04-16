-- ============================================
-- AI OS Backend — Database Migration
-- Run this in Supabase SQL Editor:
-- https://supabase.com/dashboard/project/khdooqzxomehmiiaznjc/sql/new
-- ============================================

-- 1. Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'pro', 'enterprise')),
    api_key TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Messages
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    model TEXT,
    tokens_used INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Persistent User Memory
CREATE TABLE IF NOT EXISTS user_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    category TEXT DEFAULT 'general',
    importance FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, key)
);

-- 5. Usage Logs
CREATE TABLE IF NOT EXISTS usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    model TEXT,
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    cost DECIMAL(10, 6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Daily Usage Aggregates
CREATE TABLE IF NOT EXISTS daily_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    date DATE DEFAULT CURRENT_DATE,
    request_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0,
    UNIQUE(user_id, date)
);

-- 7. Workflows
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    steps JSONB NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    results JSONB DEFAULT '[]',
    total_cost DECIMAL(10, 6) DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Enable Row Level Security (RLS) on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE daily_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;

-- 9. RLS Policies — Allow backend (service role) full access
-- Since we use anon key from backend, allow all operations for now
CREATE POLICY "Allow all operations" ON users FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON conversations FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON messages FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON user_memory FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON usage_logs FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON daily_usage FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Allow all operations" ON workflows FOR ALL USING (true) WITH CHECK (true);

-- 10. Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_memory_user ON user_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_usage_user ON usage_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_daily_user_date ON daily_usage(user_id, date);
CREATE INDEX IF NOT EXISTS idx_workflows_user ON workflows(user_id);
