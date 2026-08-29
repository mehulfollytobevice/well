# import duckdb
import duckdb
import pandas as pd

# read the xlsx file
df_wells_csv = pd.read_csv('data/seed/wells.csv')
df_timeseries = pd.read_excel('data/raw/timeseries/Extended Circulation Test Data 08082024 to 09052024 (30 sec increment).xlsx', header= None, skiprows= 4)

# preprocess the timeseries data
# assign correct column names to the DataFrame
df_timeseries.columns = [
    "ts",
    "pressure_16b",
    "flow_16b_1",
    "flow_16b_2",
    "temp_16b",
    "flow_sep_1",
    "flow_sep_2",
    "flow_sep_total",
    "pressure_16a",
    "pump_rate_liberty",
    "pressure_liberty",
]

df_select = df_timeseries.copy()

df_select["ts"] = pd.to_datetime(df_select["ts"], errors='coerce')
df_select = df_select.dropna(subset=["ts"])

num_cols = [c for c in df_select.columns if c != "ts"]
df_select[num_cols] = df_select[num_cols].apply(pd.to_numeric, errors="coerce")

# convert from long to wide format
records = []

# 16B: pressure + temp (+ optional flow)
b = df_select[["ts", "pressure_16b", "temp_16b", "flow_16b_1"]].copy()
b["well_id"] = "16B"
b = b.rename(columns={
    "pressure_16b": "pressure",
    "temp_16b": "temperature",
    "flow_16b_1": "flow_rate",
})
records.append(b)

# 16A: mostly pressure in this file
a = df_select[["ts", "pressure_16a"]].copy()
a["well_id"] = "16A"
a = a.rename(columns={"pressure_16a": "pressure"})
a["temperature"] = pd.NA
a["flow_rate"] = pd.NA
records.append(a)

timeseries = pd.concat(records, ignore_index=True)
timeseries["source"] = "gdr:2475065 raw uncorrected"

# create a duckdb database
DB_PATH = "data/processed/forge.duckdb"  # matches .env.example
conn = duckdb.connect(DB_PATH)

# create a table in the database
conn.execute("CREATE OR REPLACE TABLE wells AS SELECT * FROM df_wells_csv")
conn.execute("""
    CREATE OR REPLACE TABLE timeseries AS
    SELECT
        ts::TIMESTAMP AS ts,
        well_id::VARCHAR AS well_id,
        flow_rate::DOUBLE AS flow_rate,
        pressure::DOUBLE AS pressure,
        temperature::DOUBLE AS temperature,
        source::VARCHAR AS source
    FROM timeseries
""")

# close the connection
conn.close()