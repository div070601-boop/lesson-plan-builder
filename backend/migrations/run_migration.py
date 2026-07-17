import psycopg2
import os

conn = psycopg2.connect(
    host='db.qfylsqexxnpgynyhhkjx.supabase.co',
    port=5432,
    dbname='postgres',
    user='postgres',
    password=os.environ.get('SUPABASE_SERVICE_ROLE_KEY', ''),
    sslmode='require',
    connect_timeout=10
)
conn.autocommit = True
cur = conn.cursor()

# Create table
cur.execute("""
CREATE TABLE IF NOT EXISTS public.decks (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_size BIGINT,
    client_id TEXT,
    client_name TEXT,
    module_name TEXT,
    topic_tags JSONB DEFAULT '[]'::jsonb,
    slide_count INTEGER DEFAULT 0,
    slide_titles JSONB DEFAULT '[]'::jsonb,
    analysis JSONB,
    summary TEXT,
    onedrive_path TEXT,
    file_hash TEXT,
    indexed_at TIMESTAMPTZ,
    analyzed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
""")
print("Table created successfully!")

# Enable RLS
cur.execute("ALTER TABLE public.decks ENABLE ROW LEVEL SECURITY;")
print("RLS enabled!")

# Create policy (ignore if exists)
try:
    cur.execute("CREATE POLICY decks_service_role_all ON public.decks FOR ALL USING (true) WITH CHECK (true);")
    print("Policy created!")
except Exception as e:
    print(f"Policy (may already exist): {e}")

# Verify columns
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'decks' ORDER BY ordinal_position;")
print("\nTable columns:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

cur.close()
conn.close()
print("\nDone!")
