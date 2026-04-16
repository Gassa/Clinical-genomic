import os
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://rfbayzcgceiyxdmxaoml.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJmYmF5emNnY2VpeXhkbXhhb21sIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0MzExNDMsImV4cCI6MjA5MTAwNzE0M30.ydhV6XhQowpGWoarjVfDz25kIFLrXr2UxkEWRXiLz70")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase():
    return supabasebase
