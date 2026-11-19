# Zamp AP Hub — Autonomous Invoice Processing Engine (PS-1)
> **AI Solutions Analyst Case Study Submission · Zamp 2026**  
> *An end-to-end, live-runnable automated Accounts Payable (AP) decision system featuring optical ingestion, 3-way PO reconciliation, cumulative budget tracking, tolerance policies, anti-fraud guards, and a real-time execution dashboard.*

---

## 🌟 Executive Summary

In mid-size enterprise finance teams, Accounts Payable (AP) specialists process hundreds of messy vendor invoices monthly. Manual verification against purchase orders, budget spreadsheets, and bank records is slow, expensive, and prone to human error on Friday afternoons.

**Zamp AP Hub** automates this lifecycle from **PDF to verified decision**:
1. **Document Ingestion & Preprocessing**: Extracts text and structural layers from native PDFs, scans, and electronic documents.
2. **Entity & Semantic Parsing**: Identifies vendor names, invoice numbers, dates, payment terms, line items, and remittance bank details.
3. **PO 2-Way & 3-Way Reconciliation**: Matches against procurement purchase orders, verifying prices, quantities, and cumulative remaining budget balances.
4. **Enterprise Policy & Anti-Fraud Engine**: Evaluates duplicate submissions, approved KYC directories, variance tolerances, and bank routing integrity.
5. **Autonomous Decision & Explainable Audit Trail**: Delivers instant straight-through processing (`TOUCHLESS_APPROVED`), routes policy exceptions to humans (`NEEDS_REVIEW`), or rejects non-compliant submissions (`REJECTED`) with an auto-drafted explanation email to the vendor.

---

## 🚀 Quickstart: Run Live in 10 Seconds

The application is completely self-contained in Python using native system libraries and Flask. No external databases or heavy node setups are needed.

```bash
# 1. Clone or navigate to the directory
cd Zamp

# 2. Run the application
python3 app.py
```

Open your browser to:
👉 **[http://127.0.0.1:8080](http://127.0.0.1:8080)** (or **[http://localhost:8080](http://localhost:8080)**)

---

## 🧪 Prepared Test Scenarios (Happy Path & 5 Real-World Edge Cases)

Right on the user interface, you have **one-click buttons** to execute each scenario live with real-time stage streaming:

| Scenario | Vendor / Invoice | Document Type | System Verdict | Decision Reason & Logic |
| :--- | :--- | :--- | :--- | :--- |
| **Happy Path** | **Acme Cloud Corp**<br>`INV-2026-8812` | Clean PDF | `TOUCHLESS_APPROVED` | 100% 2-way match against `PO-2026-101` ($3,500.00). Verified bank routing & active KYC. Auto-cleared for ERP disbursement. |
| **Edge Case 1** | **Apex Logistics LLC**<br>`INV-2026-9041` | Split PO / Milestone | `TOUCHLESS_PARTIAL_DRAW` | Cumulative partial draw ($4,200.00) against $10,000.00 PO with prior draw ($5,000.00). Approved; updates remaining PO balance to $800.00. |
| **Edge Case 2** | **NexGen Hardware**<br>`INV-2026-7731` | Freight Surcharge | `APPROVED_WITH_TOLERANCE` | Invoice is $5,120.00 vs $5,000.00 PO. $120.00 / 2.4% variance is within vendor's configured 3.0% / $150 tolerance threshold. Approved with warning. |
| **Edge Case 3** | **Global Office Supplies**<br>`INV-2026-6620` | Phishing / Fraud Alert | `FRAUD_SECURITY_HOLD` (Needs Review) | Invoice amounts match PO perfectly, but remittance bank routing on invoice (`999999999`) differs from Vendor Master File. Flagged for security callback. |
| **Edge Case 4** | **Apex Logistics LLC**<br>`INV-2026-8100` | Duplicate Submission | `DUPLICATE_REJECTED` | Exact duplicate of an already approved and paid invoice. Blocked by duplicate detection engine to prevent double payout. |
| **Edge Case 5** | **Quick Print Scan**<br>`(Unformatted Scan)` | Missing Compliance Data | `COMPLIANCE_REJECTED` | Critical mandatory invoice fields missing (no Invoice #, unlisted vendor). Auto-drafts revision request email to vendor. |

You can also drag-and-drop any custom PDF or text invoice directly into the file upload box.

---

## 🏗️ System Architecture

```
                                  [ Incoming Vendor Invoice PDF ]
                                                │
                                                ▼
                        ┌──────────────────────────────────────────────┐
                        │   Stage 1: Document Ingestion & Optical OCR  │
                        │   (PDFKit / CoreGraphics Text Extraction)    │
                        └───────────────────────┬──────────────────────┘
                                                │
                                                ▼
                        ┌──────────────────────────────────────────────┐
                        │   Stage 2: Entity & Semantic Field Parser    │
                        │   (Vendor, Inv#, Date, Lines, Bank Routing)  │
                        └───────────────────────┬──────────────────────┘
                                                │
                                                ▼
                        ┌──────────────────────────────────────────────┐
                        │   Stage 3: PO 2-Way / 3-Way Reconciliation   │
                        │   (Master PO DB, Line Reconciliation, Split) │
                        └───────────────────────┬──────────────────────┘
                                                │
                                                ▼
                        ┌──────────────────────────────────────────────┐
                        │   Stage 4: Compliance, Fraud & Tolerance     │
                        │   - Rule 1: Duplicate Invoice Detection      │
                        │   - Rule 2: Vendor KYC & Master Directory    │
                        │   - Rule 3: Cumulative PO Budget Ceiling     │
                        │   - Rule 4: Price & Quantity Tolerance (3%)  │
                        │   - Rule 5: Bank Remittance Anti-Fraud Guard │
                        │   - Rule 6: Tax & Mathematical Integrity     │
                        └───────────────────────┬──────────────────────┘
                                                │
                                                ▼
                        ┌──────────────────────────────────────────────┐
                        │   Stage 5: Autonomous Decision Engine        │
                        │   Outputs: APPROVED / NEEDS_REVIEW / REJECT  │
                        │   + Action Recommendation + Vendor Email     │
                        └──────────────────────────────────────────────┘
```

---

## 🖥️ User Interface Highlights

- **Live Run View**: Visual stepper with real-time status pulses, stage duration (latency in ms), live execution console, side-by-side reconciliation progress bar, and line-item match table.
- **AP Executive Dashboard**: High-level KPIs (Straight-Through Processing rate %, Total value cleared, Exceptions count, Processing latency) and filterable audit ledger.
- **PO Explorer**: Real-time view of company purchase orders showing initial budget, committed spend, and remaining balance.
- **Vendor Master Directory**: Shows verified vendor records, approved tax IDs, authorized wire routing, and contractual tolerance policies.
- **Audit Drilldown Modal**: In-depth inspection of any historical run showing raw extracted JSON, stage timestamps, and every rule's individual verdict.
- **Reset Demo Baseline**: One-click restore button to bring back initial sample states during demos and interview rehearsals.

---

## 📂 Project Structure

```
Zamp/
├── app.py                      # Flask backend API & Server-Sent Events (SSE) streamer
├── engine/
│   ├── database.py             # Master data stores (POs, Vendors, Runs) & stats
│   ├── extractor.py            # PDF text extraction & structured entity parser
│   ├── matcher.py              # 2-way/3-way PO matcher & fuzzy line reconciliation
│   ├── rules.py                # 6-rule compliance, fraud, tolerance & math engine
│   └── decision.py             # Decision synthesizer & vendor notification generator
├── data/
│   ├── purchase_orders.json    # Procurement PO dataset with remaining balances
│   ├── vendors.json            # Approved vendor records & bank routing master
│   └── runs_history.json       # Historical operational run ledger
├── test_invoices/              # 6 realistic sample PDF & text test documents
├── templates/
│   └── index.html              # Responsive single-page application UI
├── static/
│   ├── js/app.js               # Frontend controller, SSE listener & dynamic renderer
│   └── css/styles.css          # Visual animations and custom scrollbars
├── scripts/
│   └── generate_sample_pdfs.py # Test invoice PDF generator script
├── DEMO_VIDEO_SCRIPT.md        # 5-minute timed walkthrough script for Loom
├── INTERVIEW_GUIDE.md          # Live interview defense notes & anticipated Q&A
└── README.md                   # Project overview & documentation
```

---

## 🏆 Deliverables Checklist (Per Zamp Candidate Guide)

- [x] **Deliverable 1 — A working automated process · live and runnable**: Accepts real PDF/text inputs, executes complete 5-stage logic, features an intuitive UI with live run view and dashboard.
- [x] **Deliverable 2 — 5-minute demo video script**: Ready in `DEMO_VIDEO_SCRIPT.md`.
- [x] **2–4 Realistic Edge Cases (Delivered 5)**: Split PO billing, Tolerance threshold variance, Bank wire phishing alert, Duplicate invoice prevention, Missing compliance data.
- [x] **Prepared for Live Demo in Follow-up Interview**: Tested, reproducible, zero-friction local execution.
