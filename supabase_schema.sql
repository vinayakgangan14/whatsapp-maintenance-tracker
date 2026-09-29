-- ====================================================================
-- SUPABASE MULTI-TENANT DATABASE SCHEMA
-- Maintenance Tracker Suite (Free & Open for Any Company)
-- ====================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- --------------------------------------------------------------------
-- 1. COMPANIES TABLE (Tenant Workspaces)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.companies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_name TEXT NOT NULL,
    industry TEXT DEFAULT 'Manufacturing',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- --------------------------------------------------------------------
-- 2. USER PROFILES TABLE (Tied to Supabase Auth & Company Tenant)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    company_id UUID REFERENCES public.companies(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('Operator', 'Manager', 'Admin')) DEFAULT 'Operator',
    phone_number TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- --------------------------------------------------------------------
-- 3. BREAKDOWN TICKETS TABLE (Multi-Tenant)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.breakdowns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    ticket_number TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'General',
    sender_phone TEXT,
    sender_name TEXT,
    equipment_id TEXT NOT NULL,
    issue_description TEXT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    status TEXT NOT NULL CHECK (status IN ('PENDING_APPROVAL', 'APPROVED', 'OPEN', 'RESOLVED', 'REJECTED')) DEFAULT 'PENDING_APPROVAL',
    assigned_to TEXT DEFAULT 'Unassigned',
    duration_minutes INTEGER DEFAULT 0,
    resolution_notes TEXT,
    technician TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, ticket_number)
);

-- --------------------------------------------------------------------
-- 4. PREVENTIVE MAINTENANCE LOGS TABLE (Multi-Tenant)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.maintenance_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    ticket_number TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'General',
    sender_phone TEXT,
    sender_name TEXT,
    equipment_id TEXT NOT NULL,
    activity_description TEXT NOT NULL,
    scheduled_time TEXT,
    status TEXT NOT NULL CHECK (status IN ('PENDING_APPROVAL', 'APPROVED', 'OPEN', 'RESOLVED', 'REJECTED')) DEFAULT 'PENDING_APPROVAL',
    assigned_to TEXT DEFAULT 'Unassigned',
    technician TEXT,
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, ticket_number)
);

-- --------------------------------------------------------------------
-- 5. WELDING WORK LOGS TABLE (Multi-Tenant)
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.welding_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES public.companies(id) ON DELETE CASCADE,
    ticket_number TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'General',
    sender_phone TEXT,
    sender_name TEXT,
    equipment_id TEXT NOT NULL,
    location TEXT,
    welding_details TEXT NOT NULL,
    scheduled_time TEXT,
    status TEXT NOT NULL CHECK (status IN ('PENDING_APPROVAL', 'APPROVED', 'OPEN', 'RESOLVED', 'REJECTED')) DEFAULT 'PENDING_APPROVAL',
    assigned_to TEXT DEFAULT 'Unassigned',
    technician TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, ticket_number)
);

-- ====================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES — COMPANY DATA ISOLATION
-- Ensures Company A can NEVER view or modify Company B's data!
-- ====================================================================

ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.breakdowns ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.maintenance_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.welding_logs ENABLE ROW LEVEL SECURITY;

-- Helper function to get current user's company_id
CREATE OR REPLACE FUNCTION public.get_user_company_id()
RETURNS UUID AS $$
  SELECT company_id FROM public.profiles WHERE id = auth.uid();
$$ LANGUAGE sql SECURITY DEFINER;

-- RLS Policy: Users can only see their own company profile
CREATE POLICY "Profiles isolated by company" ON public.profiles
    FOR ALL USING (company_id = public.get_user_company_id());

-- RLS Policy: Breakdowns isolated by company_id
CREATE POLICY "Breakdowns isolated by company" ON public.breakdowns
    FOR ALL USING (company_id = public.get_user_company_id());

-- RLS Policy: PM logs isolated by company_id
CREATE POLICY "PM logs isolated by company" ON public.maintenance_logs
    FOR ALL USING (company_id = public.get_user_company_id());

-- RLS Policy: Welding logs isolated by company_id
CREATE POLICY "Welding logs isolated by company" ON public.welding_logs
    FOR ALL USING (company_id = public.get_user_company_id());
