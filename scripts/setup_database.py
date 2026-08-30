from wellground.data.duckdb import build_database

if __name__ == "__main__":
    path = build_database()
    print(f"Wrote {path}")
