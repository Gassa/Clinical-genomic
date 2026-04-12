
-- Institutions (hôpitaux, centres)
CREATE TABLE IF NOT EXISTS institutions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    city TEXT,
    country TEXT DEFAULT 'Sénégal',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Profils utilisateurs (liés à auth.users Supabase)
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'medecin' CHECK (role IN ('medecin','biologiste','admin','chercheur')),
    institution_id UUID REFERENCES institutions(id),
    specialty TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Patients
CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    institution_id UUID REFERENCES institutions(id),
    created_by UUID REFERENCES auth.users(id),
    patient_code TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    date_of_birth DATE,
    sex TEXT CHECK (sex IN ('M','F','Autre')),
    cancer_type TEXT,
    stage TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analyses (NGS, CNV, Fusions, Signatures, MTB)
CREATE TABLE IF NOT EXISTS analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE,
    created_by UUID REFERENCES auth.users(id),
    analysis_type TEXT NOT NULL CHECK (analysis_type IN ('ngs','cnv','fusions','signatures','mtb')),
    input_text TEXT,
    context TEXT,
    result JSONB,
    status TEXT DEFAULT 'completed',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_analyses_patient ON analyses(patient_id);
CREATE INDEX IF NOT EXISTS idx_analyses_type ON analyses(analysis_type);
CREATE INDEX IF NOT EXISTS idx_patients_institution ON patients(institution_id);

-- RLS (Row Level Security)
ALTER TABLE institutions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE patients ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;

-- Policies basiques
CREATE POLICY IF NOT EXISTS "Users can read own profile"
    ON user_profiles FOR SELECT USING (auth.uid() = id);

CREATE POLICY IF NOT EXISTS "Users can update own profile"
    ON user_profiles FOR UPDATE USING (auth.uid() = id);

CREATE POLICY IF NOT EXISTS "Users can read patients in their institution"
    ON patients FOR SELECT USING (
        institution_id IN (
            SELECT institution_id FROM user_profiles WHERE id = auth.uid()
        )
    );

CREATE POLICY IF NOT EXISTS "Users can insert patients"
    ON patients FOR INSERT WITH CHECK (auth.uid() = created_by);

CREATE POLICY IF NOT EXISTS "Users can read analyses"
    ON analyses FOR SELECT USING (
        patient_id IN (
            SELECT p.id FROM patients p
            JOIN user_profiles up ON p.institution_id = up.institution_id
            WHERE up.id = auth.uid()
        )
    );

CREATE POLICY IF NOT EXISTS "Users can insert analyses"
    ON analyses FOR INSERT WITH CHECK (auth.uid() = created_by);
