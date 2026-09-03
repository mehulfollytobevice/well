# WellGround Data Guide

This document explains **what the data is**, **where it came from**, and **how the pieces fit together**. For download URLs, DOIs, and local file paths, see [`data/PROVENANCE.md`](../data/PROVENANCE.md).

---

## Domain context

**Utah FORGE** (Frontier Observatory for Research in Geothermal Energy) is a DOE-funded EGS research site near Milford, Utah. The goal is to prove that water can be circulated through hot, fractured granite: inject cold water in one well, produce heated water from a paired well, and measure whether the reservoir sustains flow and heat transfer.

WellGround v1 focuses on one campaign: the **extended circulation test** run on wells **16A(78)-32** (injection) and **16B(78)-32** (production) from **8 August to 5 September 2024**.

```
Surface                         Subsurface (hot granite)
─────────                       ─────────────────────────
Liberty pump ──► 16A (inject) ──► fractured EGS reservoir ──► 16B (produce) ──► separator / meters
                      ▲                                              │
                      └──────────── circulation loop ────────────────┘
```

Prior milestones that give context to the files:

| When | Event |
|---|---|
| 2020–2021 | 16A drilled (~11,000 ft MD, highly deviated) |
| Apr 2022 | 16A hydraulically stimulated |
| May 2023 | Short 9-hour circulation test proved connectivity between 16A and 16B |
| Apr–Jul 2023 | 16B drilled (~300 ft above and parallel to 16A) |
| Aug 2024 | Downhole PLT/PTS surveys (Schlumberger) on both wells |
| **Aug–Sep 2024** | **Extended circulation test** — the primary dataset in this repo |
| Oct 2024 | Data published to the [Geothermal Data Repository (GDR)](https://gdr.openei.org/) |

---

## Three data layers

The corpus is intentionally split into layers that map to how the agent queries them:

| Layer | Location | Answers questions like… | Agent route |
|---|---|---|---|
| **Well metadata** | `data/seed/wells.csv` | Which well is the injector? How deep is 16B? | SQL |
| **Time series** | `data/raw/timeseries/` | Avg production temp last week? When did flow drop? | SQL |
| **Reports & logs** | `data/raw/pdfs/` | How was 16A stimulated? What happened on Aug 12? | RAG |

---

## Wells (`data/seed/wells.csv`)

Static reference for eight wells at the FORGE site. The circulation test data revolves around **16A** and **16B**; the others provide site context.

| well_id | Full name | Role | MD (ft) | Notes |
|---|---|---|---|---|
| **16A** | 16A(78)-32 | Injection | 10,987 | Stimulated Apr 2022; water pumped in during circulation |
| **16B** | 16B(78)-32 | Production | 10,947 | Paired with 16A; heated water produced here |
| 58-32 | 58-32 | Pilot | 7,536 | Deep vertical well; early stimulation experiments |
| 58-32-WW | 58-32 | Water | 1,200 | Shallow water supply on the 58-32 pad |
| 56-32, 68-32, 78-32, 78B-32 | — | Seismic monitoring | varies | Microseismic / DAS instrumentation wells |

Regenerate with `python3 scripts/scrape_wells.py`.

---

## Time series (`data/raw/timeseries/`)

**Source:** GDR submission [1683](https://gdr.openei.org/submissions/1683) · DOI [10.15121/2475065](https://doi.org/10.15121/2475065)

Structured operational measurements recorded every **30 seconds** during the extended circulation test.

### Files

| File | Purpose |
|---|---|
| **`Extended Circulation Test Data … (30 sec increment).xlsx`** | Primary SQL source. Timestamped flow, wellhead pressure, and temperature for 16A/16B plus surface pump readings. Sheet: `Data (30 sec)`. |
| `Extended Circulation Test Report-Final.docx` | Official test report: objectives, procedure, equipment, and guidance on applying calibrations. Also indexed for RAG. |
| `Field Calibration of Flow Meters.xlsx` | Calibration data for flow meters (raw vs corrected). |
| `Manual Temperature and Pressure Data.xlsx` | Hand-measured spot checks during field calibration. |
| `Read Me.docx` | Column definitions and dataset notes from the data publisher. |

### Main XLSX columns (header rows)

The time series spreadsheet uses a three-row header. Key columns:

| Column group | Measures |
|---|---|
| `Date & Time of Day` | Timestamp (Mountain Time) |
| `16B` Wellhead Pressure | Production-side wellhead pressure |
| `16B-DIS FLOW 1 / 2` | Production flow (two discharge meters, gpm) |
| `16B-DIS TEMP` | Production wellhead temperature (°F) |
| `SEP DIS FLOW 1 / 2`, `SEP FLOW TOTAL` | Separator-side flow measurements |
| `16A` Wellhead Pressure | Injection-side wellhead pressure |
| `Liberty Pump Rate / Wellhead Pressure` | Surface pumping equipment |

### Important caveats

- Data are **raw / uncorrected Pason SCADA** readings. Calibration files explain how to correct them; v1 loads raw values with an explicit disclaimer.
- 16B has **two flow meters** plus separator totals — pick or combine consistently when building DuckDB.
- Test window: **2024-08-08 00:00 → 2024-09-05** (approximate; confirm against the XLSX).

---

## Daily ops reports (`data/raw/pdfs/daily_reports/extracted/`)

**Source:** GDR submission [1681](https://gdr.openei.org/submissions/1681) · DOI [10.15121/2455019](https://doi.org/10.15121/2455019)

**70 PDFs** — the field diary for Jul 29 – Sep 5, 2024. Narrative ops summaries, not machine-readable time series.

| Report type | Count | Period | Content |
|---|---|---|---|
| **16B Clean Out RPT** No.1–9 | 9 | Jul 29 – Aug 6 | Pre-test wellbore cleanout on 16B |
| **16A Circulation Test RPT** No.1–31 | 31 | Aug 6 – Sep 5 | Daily injection-side ops during circulation |
| **16B Circulation Test RPT** 1–30 | 30 | Aug 7 – Sep 5 | Daily production-side ops during circulation |

Each daily report typically covers: rig activity, pumping, water temperature, depths, safety, weather, and cleanout notes.

Use these for **qualitative** questions ("what happened that day?", "summarize the first week"). Use the time series XLSX for **numeric** questions ("average temperature on Aug 25").

---

## Downhole surveys (`data/raw/pdfs/inj_prod/`)

**Source:** GDR submission [1668](https://gdr.openei.org/submissions/1668) · DOI [10.15121/2473673](https://doi.org/10.15121/2473673)

Schlumberger (SLB) **PLT/PTS** wireline logs from August 2024. These measure flow, temperature, and pressure **along the wellbore** (vs surface wellhead readings in the time series).

### 16A (`inj_prod/16A/`) — injection well

| File | Purpose |
|---|---|
| `…Injection Profile Final Report.pdf` | Final SLB report on the Aug 17 injection profile log |
| `…Injection Profile Report Prelim.pdf` | Preliminary version of the same |
| `…Injection Profile Results Final.xlsx` | Tabular depth-resolved injection results |
| `…Injection Profile Results.xlsx` | Earlier results version |
| `…Producing Profile Results.xlsx` | Producing profile from Aug 28 |
| `…Interp Outputs LAS.las` | Standard well log format — **not indexed in v1** |

### 16B (`inj_prod/16B/`) — production well

| File | Purpose |
|---|---|
| `…DiDrill_Production Log Final Report.pdf` | Final production log report (Aug 28) |
| `…Producing Profile Prelim Report.pdf` | Preliminary producing profile report |
| `…DiDrill_Production Log Results.xlsx` | Depth-resolved production log tables |
| `…Producing Profile Results.xlsx` | Producing profile tables |
| `…Production Log Interp Outputs.las` | LAS well log — **not indexed in v1** |

XLSX files have sheets `Results Stage` and `Results Detail`.

---

## How files relate in time

```
Jul 29 – Aug 6     16B cleanout daily reports
Aug 17             16A injection profile log (inj_prod/16A)
Aug 28             16B production log + producing profiles (inj_prod/)
Aug 8 – Sep 5      Extended circulation test
                   ├── 30-sec time series (timeseries/*.xlsx)
                   └── daily circulation reports (daily_reports/extracted/)
Sep 5              Test ends
Oct 2024           Data published to GDR
```

---

## Example questions → data source

| Question | Route | Source |
|---|---|---|
| "Average production wellhead temperature for 16B during the last week of the test" | SQL | Time series XLSX → DuckDB |
| "Which well is the injector?" | SQL | `wells.csv` |
| "What pump rate was used for Step 7 of the 16A circulation test?" | RAG | daily reports |
| "What rig activity happened on Aug 12?" | RAG | Daily report PDF for that date |
| "Compare injection vs production temps and cite the test procedure" | SQL + RAG | Time series + final report DOCX |
| "Where does injection enter the 16A wellbore?" | RAG | 16A injection profile PDF/XLSX |

---

## Local directory layout

```
data/
├── PROVENANCE.md              # DOIs, licenses, download metadata
├── seed/
│   └── wells.csv              # Well metadata (committed)
├── raw/                       # Raw downloads (gitignored)
│   ├── timeseries/            # GDR 1683 — XLSX + DOCX
│   └── pdfs/
│       ├── daily_reports/extracted/   # GDR 1681 — 70 PDFs
│       └── inj_prod/
│           ├── 16A/           # GDR 1668 — injection surveys
│           └── 16B/           # GDR 1668 — production surveys
└── processed/                 # DuckDB, embeddings (gitignored, built later)
```

---

## v1 scope and exclusions

| Included | Excluded (v1) |
|---|---|
| 16A/16B circulation test time series | Nationwide heat-flow catalogs |
| Daily ops PDFs (~70) | DAS / fiber / microseismic catalogs |
| PLT/PTS PDFs and XLSX tables | `.las` well log parsing |
| Well metadata seed CSV | Multimodal well-log vision |

---

## License and disclaimer

All GDR datasets are **CC-BY 4.0**. Cite the DOIs in [`data/PROVENANCE.md`](../data/PROVENANCE.md) when publishing results.

This project uses public Utah FORGE data for research and portfolio purposes. It is not affiliated with DOE, the University of Utah, or Utah FORGE operators, and is not a substitute for engineering judgment.
