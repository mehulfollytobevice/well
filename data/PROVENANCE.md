# Data Provenance

WellGround v1 corpus: Utah FORGE structured time series + unstructured ops/technical reports for wells **16A(78)-32** and **16B(78)-32**, Aug–Sep 2024 extended circulation test.

All GDR datasets below are public DOE submissions. License: **Creative Commons Attribution 4.0 (CC-BY 4.0)** unless noted.

Local acquisition date: **2026-08-26**

---

## Well metadata (committed seed)

| Field | Value |
|---|---|
| **File** | `data/seed/wells.csv` |
| **Source** | [Utah FORGE Data Dashboard — Well Data](https://utahforge.com/project-data-dashboard/#well-data) |
| **Enrichment** | [GDR submission 1358](https://gdr.openei.org/submissions/1358) — GPS wellhead coordinates (Dec 2021); OpenEI wiki for 16A/16B TVD |
| **DOI (GPS)** | [10.15121/1838418](https://doi.org/10.15121/1838418) |
| **License** | Public project metadata; GDR GPS data CC-BY 4.0 |
| **Script** | `scripts/scrape_wells.py` |

---

## 1. Extended circulation time series (structured)

| Field | Value |
|---|---|
| **Role** | Primary SQL / DuckDB source |
| **GDR submission** | [1683](https://gdr.openei.org/submissions/1683) |
| **DOI** | [10.15121/2475065](https://doi.org/10.15121/2475065) |
| **Title** | Utah FORGE: Wells 16A(78)-32 and 16B(78)-32 Extended Circulation Test Data — August and September 2024 |
| **Authors** | McLennan, John; England, Kevin; Swearingen, Leroy |
| **Organization** | Energy and Geoscience Institute, University of Utah |
| **Published** | 2024-10-11 |
| **Archive ZIP** | `Extended Circulation Test.zip` |
| **Local ZIP** | `data/raw/timeseries/Extended Circulation Test.zip` |
| **Extracted to** | `data/raw/timeseries/` |
| **License** | CC-BY 4.0 |

### Extracted files

| File | Description |
|---|---|
| `Extended Circulation Test Data 08082024 to 09052024 (30 sec increment).xlsx` | Uncorrected Pason time series @ 30 s (flow, WHP, temperature) |
| `Extended Circulation Test Report-Final.docx` | Final test report (procedure, corrections guidance) |
| `Field Calibration of Flow Meters.xlsx` | Flow meter calibration data |
| `Manual Temperature and Pressure Data.xlsx` | Manual calibration readings |
| `Read Me.docx` | Dataset readme |

**Notes:** Data are **raw / uncorrected**. Test period: 2024-08-08 → 2024-09-05. Prefer documenting raw values + disclaimer over applying field calibrations in v1.

---

## 2. Circulation daily reports (unstructured / RAG)

| Field | Value |
|---|---|
| **Role** | Daily ops narrative (rig activity, pumping, temps, safety) |
| **GDR submission** | [1681](https://gdr.openei.org/submissions/1681) |
| **DOI** | [10.15121/2455019](https://doi.org/10.15121/2455019) |
| **Title** | Utah FORGE: Wells 16A(78)-32 and 16B(78)-32 Circulation Test Daily Reports from August 2024 |
| **Author** | Swearingen, Leroy |
| **Organization** | Energy and Geoscience Institute, University of Utah |
| **Published** | 2024-10-04 |
| **Archive ZIP** | `Circulation Daily Reports.zip` (local name: `2024Circulation_daily_reports.zip`) |
| **Local ZIP** | `data/raw/pdfs/daily_reports/2024Circulation_daily_reports.zip` |
| **Extracted to** | `data/raw/pdfs/daily_reports/extracted/` |
| **File count** | 70 PDFs (Jul 29 – Sep 5, 2024; includes 16B clean-out + 16A/16B circulation dailies) |
| **License** | CC-BY 4.0 |

---

## 3. Injection / production test reports (unstructured / RAG)

| Field | Value |
|---|---|
| **Role** | PLT/PTS survey reports and tables for 16A injection + 16B production |
| **GDR submission** | [1668](https://gdr.openei.org/submissions/1668) |
| **DOI** | [10.15121/2473673](https://doi.org/10.15121/2473673) |
| **Title** | Utah FORGE: Injection and Production Test results and Reports from August 2024 |
| **Authors** | Kolomytsev, Leonid; Chadwick, Casey |
| **Organization** | Energy and Geoscience Institute, University of Utah |
| **Published** | 2024-09-24 |
| **License** | CC-BY 4.0 |

### 16A — injection / producing profile

| Field | Value |
|---|---|
| **Archive ZIP** | `16A Logs and Reports.zip` (local: `16A PLT_PTS Survey.zip`) |
| **Local ZIP** | `data/raw/pdfs/inj_prod/16A PLT_PTS Survey.zip` |
| **Extracted to** | `data/raw/pdfs/inj_prod/16A/` |
| **Contents** | 2 PDF reports, 3 XLSX result tables, 1 LAS (excluded from v1 RAG index) |

### 16B — production log

| Field | Value |
|---|---|
| **Archive ZIP** | `16B Logs and Reports.zip` (local: `16B PLT_PTS Survey.zip`) |
| **Local ZIP** | `data/raw/pdfs/inj_prod/16B PLT_PTS Survey.zip` |
| **Extracted to** | `data/raw/pdfs/inj_prod/16B/` |
| **Contents** | 2 PDF reports, 2 XLSX result tables, 1 LAS (excluded from v1 RAG index) |

**Notes:** v1 RAG indexes **PDFs + XLSX tables** only; `.las` well logs deferred (no multimodal log vision in v1).

---

## Local layout summary

```
data/
├── PROVENANCE.md          ← this file (committed)
├── release/               ← pinned deploy snapshot (committed)
│   ├── README.md          ← attribution + license for deployed indexes
│   ├── MANIFEST.json
│   ├── forge.duckdb
│   ├── chroma/
│   └── bm25/
├── seed/
│   └── wells.csv          ← well metadata (committed)
└── raw/                   ← gitignored
    ├── timeseries/
    │   ├── Extended Circulation Test.zip
    │   └── *.xlsx, *.docx (extracted)
    └── pdfs/
        ├── daily_reports/
        │   ├── 2024Circulation_daily_reports.zip
        │   └── extracted/   ← 70 PDFs
        └── inj_prod/
            ├── 16A PLT_PTS Survey.zip
            ├── 16B PLT_PTS Survey.zip
            ├── 16A/           ← 6 files
            └── 16B/           ← 5 files
```

---

## Citation (recommended)

McLennan, J., England, K., & Swearingen, L. (2024). *Utah FORGE: Wells 16A(78)-32 and 16B(78)-32 Extended Circulation Test Data — August and September 2024*. Geothermal Data Repository. https://doi.org/10.15121/2475065

Swearingen, L. (2024). *Utah FORGE: Wells 16A(78)-32 and 16B(78)-32 Circulation Test Daily Reports from August 2024*. Geothermal Data Repository. https://doi.org/10.15121/2455019

Kolomytsev, L., & Chadwick, C. (2024). *Utah FORGE: Injection and Production Test results and Reports from August 2024*. Geothermal Data Repository. https://doi.org/10.15121/2473673

---

## Disclaimer

Public Utah FORGE / DOE GDR data for research and portfolio use. Not affiliated with DOE, University of Utah, or Utah FORGE operators. Not a substitute for engineering judgment.
