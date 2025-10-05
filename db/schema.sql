-- Postgres schema (Stage 1)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE source (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  kind TEXT NOT NULL,
  title TEXT,
  origin_url TEXT,
  license TEXT,
  owner TEXT,
  hash TEXT,
  valid_from DATE,
  valid_to DATE,
  meta JSONB,
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE norm_unit (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  law TEXT NOT NULL,
  law_title TEXT,
  article TEXT,
  part TEXT,
  point TEXT,
  subpoint TEXT,
  official_id TEXT,
  valid_from DATE NOT NULL,
  valid_to DATE,
  text TEXT,
  source_id UUID REFERENCES source(id)
);
CREATE INDEX idx_norm_unit_lookup ON norm_unit (law, article, part, point, subpoint);
CREATE INDEX idx_norm_unit_valid ON norm_unit (valid_from, COALESCE(valid_to,'2999-12-31'::date));

CREATE TABLE chunk (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_id UUID REFERENCES source(id),
  norm_unit_id UUID REFERENCES norm_unit(id),
  page INT,
  paragraph INT,
  slide INT,
  timecode TEXT,
  text TEXT NOT NULL
);
CREATE INDEX idx_chunk_source ON chunk (source_id);
CREATE INDEX idx_chunk_norm ON chunk (norm_unit_id);

CREATE TABLE knowledge_atom (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  statement TEXT NOT NULL,
  type TEXT CHECK (type IN ('declarative','procedural','conceptual','conditional','metacognitive','normative')),
  bloom TEXT CHECK (bloom IN ('remember','understand','apply','analyze','evaluate','create')),
  granularity TEXT CHECK (granularity IN ('micro','meso','macro')),
  status TEXT CHECK (status IN ('draft','reviewed','approved','deprecated')) DEFAULT 'draft',
  importance INT,
  difficulty INT,
  version TEXT,
  created_at TIMESTAMP DEFAULT now(),
  updated_at TIMESTAMP DEFAULT now()
);

CREATE TABLE atom_citation (
  atom_id TEXT REFERENCES knowledge_atom(id),
  norm_unit_id UUID REFERENCES norm_unit(id),
  chunk_id UUID REFERENCES chunk(id),
  PRIMARY KEY (atom_id, norm_unit_id, chunk_id)
);

CREATE TABLE context_profile (
  id TEXT PRIMARY KEY,
  atom_id TEXT REFERENCES knowledge_atom(id),
  context_id TEXT,
  role TEXT,
  delivery TEXT[],
  activities_default TEXT[],
  srs JSONB,
  notes TEXT
);

CREATE TABLE artifact (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  type TEXT,
  format TEXT,
  status TEXT,
  file_path TEXT,
  valid_from DATE,
  valid_to DATE,
  meta JSONB
);

CREATE TABLE artifact_link (
  artifact_id UUID REFERENCES artifact(id),
  atom_id TEXT REFERENCES knowledge_atom(id),
  norm_unit_id UUID REFERENCES norm_unit(id),
  PRIMARY KEY (artifact_id, atom_id, norm_unit_id)
);

CREATE TABLE change_event (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  source_doc TEXT,
  norm_unit_id UUID REFERENCES norm_unit(id),
  change_type TEXT CHECK (change_type IN ('ADD','AMEND','REPEAL','RENUMBER','NEW_EDITION')),
  semantics JSONB,
  effective_from DATE,
  published_at DATE NOT NULL,
  classification_level TEXT CHECK (classification_level IN ('minor','major')),
  patch_notes TEXT
);

CREATE TABLE impact_link (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  from_type TEXT,
  from_id TEXT,
  to_type TEXT,
  to_id TEXT,
  relation_type TEXT,
  weight NUMERIC,
  created_by TEXT,
  reason TEXT,
  created_at TIMESTAMP DEFAULT now()
);

COMMENT ON TABLE knowledge_atom IS 'Атом знания: минимальная единица смысла';
COMMENT ON TABLE norm_unit IS 'Единица нормы: закон/статья/часть/пункт/подпункт';
