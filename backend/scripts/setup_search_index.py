"""
Supabase pgvector search index setup helper.

Usage:
    cd backend
    python scripts/setup_search_index.py --print-sql    # Print migration SQL to stdout
    python scripts/setup_search_index.py --check        # Verify table exists in Supabase

Run the migration once in Supabase Dashboard > SQL Editor > New query.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

MIGRATION_FILE = os.path.join(
    os.path.dirname(__file__), "migrations", "001_create_search_index.sql"
)


def print_migration() -> None:
    with open(MIGRATION_FILE) as f:
        print(f.read())


def check_table() -> bool:
    from dotenv import load_dotenv
    load_dotenv()
    from supabase import create_client
    client = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    try:
        client.table("search_index").select("id").limit(1).execute()
        print("OK search_index table exists in Supabase")
        return True
    except Exception as e:
        print(f"FAIL search_index table not found: {e}")
        print("  Run: python scripts/setup_search_index.py --print-sql")
        print("  Then paste the output into Supabase SQL Editor.")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-sql", action="store_true", help="Print migration SQL")
    parser.add_argument("--check", action="store_true", help="Verify table exists")
    args = parser.parse_args()

    if args.print_sql:
        print_migration()
    elif args.check:
        ok = check_table()
        sys.exit(0 if ok else 1)
    else:
        parser.print_help()
