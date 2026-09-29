-- ====================================================================
-- SUPABASE COMPLETE SETUP SCRIPT FOR MAINTENANCE TRACKER
-- Run this script ONCE in your Supabase SQL Editor:
-- https://supabase.com/dashboard/project/durbufowkgwimbmsunsq/sql/new
-- ====================================================================

-- 1. Create Default Workspace Company
CREATE TABLE IF NOT EXISTS public.companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name TEXT NOT NULL,
    industry TEXT DEFAULT 'Manufacturing',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO public.companies (id, company_name, industry)
VALUES ('00000000-0000-0000-0000-000000000000', 'Default Workspace', 'Manufacturing')
ON CONFLICT (id) DO NOTHING;

-- 2. Breakdown Tickets Table
CREATE TABLE IF NOT EXISTS public.breakdowns (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000' REFERENCES public.companies(id) ON DELETE CASCADE,
    ticket_number TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'General',
    sender_phone TEXT,
    sender_name TEXT,
    equipment_id TEXT NOT NULL,
    issue_description TEXT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
    assigned_to TEXT DEFAULT 'Unassigned',
    duration_minutes INTEGER DEFAULT 0,
    resolution_notes TEXT,
    technician TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, ticket_number)
);

-- 3. Preventive Maintenance Logs Table
CREATE TABLE IF NOT EXISTS public.maintenance_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000' REFERENCES public.companies(id) ON DELETE CASCADE,
    ticket_number TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'General',
    sender_phone TEXT,
    sender_name TEXT,
    equipment_id TEXT NOT NULL,
    activity_description TEXT NOT NULL,
    scheduled_time TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
    assigned_to TEXT DEFAULT 'Unassigned',
    technician TEXT,
    performed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, ticket_number)
);

-- 4. Scheduled Welding Work Logs Table
CREATE TABLE IF NOT EXISTS public.welding_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000' REFERENCES public.companies(id) ON DELETE CASCADE,
    ticket_number TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'General',
    sender_phone TEXT,
    sender_name TEXT,
    equipment_id TEXT NOT NULL,
    location TEXT,
    welding_details TEXT NOT NULL,
    scheduled_time TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING_APPROVAL',
    assigned_to TEXT DEFAULT 'Unassigned',
    technician TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, ticket_number)
);

-- 5. Custom Departments Table
CREATE TABLE IF NOT EXISTS public.custom_departments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000' REFERENCES public.companies(id) ON DELETE CASCADE,
    department_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, department_name)
);

-- 6. Custom Equipment Table
CREATE TABLE IF NOT EXISTS public.custom_equipment (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000' REFERENCES public.companies(id) ON DELETE CASCADE,
    department_name TEXT NOT NULL,
    equipment_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, department_name, equipment_name)
);

-- 7. Users Table
CREATE TABLE IF NOT EXISTS public.users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    company_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000' REFERENCES public.companies(id) ON DELETE CASCADE,
    email_or_name TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Operator',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(company_id, email_or_name)
);

-- 8. Disable RLS on tables so API Key can read and write freely
ALTER TABLE public.companies DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.breakdowns DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.maintenance_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.welding_logs DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.custom_departments DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.custom_equipment DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;
