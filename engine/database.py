import os
import json
import threading
from typing import Dict, List, Optional, Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PO_FILE = os.path.join(DATA_DIR, "purchase_orders.json")
VENDORS_FILE = os.path.join(DATA_DIR, "vendors.json")
RUNS_FILE = os.path.join(DATA_DIR, "runs_history.json")

DEFAULT_VENDORS = {
  "VEND-001": {
    "id": "VEND-001",
    "name": "Acme Cloud Corp",
    "aliases": ["Acme Cloud", "Acme Cloud Corporation", "Acme Hosting"],
    "tax_id": "US-849201948",
    "email": "billing@acmecloud.com",
    "status": "APPROVED",
    "remittance_bank": {
      "bank_name": "JPMorgan Chase Bank",
      "routing_number": "021000021",
      "account_number": "9842104892",
      "account_display": "****4892"
    },
    "payment_terms": "Net 30",
    "tolerance_percent": 2.0,
    "tolerance_amount_max": 100.0
  },
  "VEND-002": {
    "id": "VEND-002",
    "name": "Apex Logistics LLC",
    "aliases": ["Apex Logistics", "Apex Freight Services", "Apex Transport"],
    "tax_id": "US-472910481",
    "email": "invoices@apexlogistics.io",
    "status": "APPROVED",
    "remittance_bank": {
      "bank_name": "Bank of America",
      "routing_number": "121000358",
      "account_number": "5481920731",
      "account_display": "****7310"
    },
    "payment_terms": "Net 15",
    "tolerance_percent": 3.0,
    "tolerance_amount_max": 250.0
  },
  "VEND-003": {
    "id": "VEND-003",
    "name": "NexGen Hardware Systems",
    "aliases": ["NexGen Hardware", "NexGen Systems Inc", "NexGen HW"],
    "tax_id": "US-938210492",
    "email": "ar@nexgenhardware.com",
    "status": "APPROVED",
    "remittance_bank": {
      "bank_name": "Wells Fargo Bank",
      "routing_number": "071000013",
      "account_number": "7718290214",
      "account_display": "****9021"
    },
    "payment_terms": "Net 30",
    "tolerance_percent": 3.0,
    "tolerance_amount_max": 150.0
  },
  "VEND-004": {
    "id": "VEND-004",
    "name": "Global Office Supplies",
    "aliases": ["Global Office Supplies Inc", "Global Office", "GOS Supply"],
    "tax_id": "US-192840192",
    "email": "finance@globalofficesupply.com",
    "status": "APPROVED",
    "remittance_bank": {
      "bank_name": "Citibank N.A.",
      "routing_number": "026009593",
      "account_number": "1129481145",
      "account_display": "****1145"
    },
    "payment_terms": "Net 30",
    "tolerance_percent": 1.0,
    "tolerance_amount_max": 50.0
  },
  "VEND-005": {
    "id": "VEND-005",
    "name": "Vertex Consulting Partners",
    "aliases": ["Vertex Consulting", "Vertex Partners"],
    "tax_id": "US-551920384",
    "email": "billing@vertexconsulting.com",
    "status": "APPROVED",
    "remittance_bank": {
      "bank_name": "Silicon Valley Bank",
      "routing_number": "111000025",
      "account_number": "3391826678",
      "account_display": "****6678"
    },
    "payment_terms": "Net 45",
    "tolerance_percent": 2.0,
    "tolerance_amount_max": 200.0
  }
}

DEFAULT_POS = {
  "PO-2026-101": {
    "po_number": "PO-2026-101",
    "vendor_id": "VEND-001",
    "vendor_name": "Acme Cloud Corp",
    "issue_date": "2026-09-01",
    "status": "OPEN",
    "description": "Enterprise Cloud Infrastructure & Hosting Q4",
    "total_amount": 3500.00,
    "previously_invoiced": 0.00,
    "remaining_balance": 3500.00,
    "currency": "USD",
    "line_items": [
      {
        "item_id": "ITEM-101",
        "description": "Cloud Compute Instances (c5.4xlarge)",
        "quantity": 20,
        "unit_price": 150.00,
        "total": 3000.00
      },
      {
        "item_id": "ITEM-102",
        "description": "Premium Support SLA",
        "quantity": 1,
        "unit_price": 500.00,
        "total": 500.00
      }
    ],
    "invoices_billed": []
  },
  "PO-2026-102": {
    "po_number": "PO-2026-102",
    "vendor_id": "VEND-002",
    "vendor_name": "Apex Logistics LLC",
    "issue_date": "2026-08-15",
    "status": "PARTIALLY_INVOICED",
    "description": "Regional Freight & Multi-Drop Warehouse Fulfillment",
    "total_amount": 10000.00,
    "previously_invoiced": 5000.00,
    "remaining_balance": 5000.00,
    "currency": "USD",
    "line_items": [
      {
        "item_id": "ITEM-201",
        "description": "Regional Pallet Distribution (Batch A)",
        "quantity": 1,
        "unit_price": 5000.00,
        "total": 5000.00
      },
      {
        "item_id": "ITEM-202",
        "description": "Regional Pallet Distribution (Batch B)",
        "quantity": 1,
        "unit_price": 4200.00,
        "total": 4200.00
      },
      {
        "item_id": "ITEM-203",
        "description": "Fuel Surcharge Contingency Reserve",
        "quantity": 1,
        "unit_price": 800.00,
        "total": 800.00
      }
    ],
    "invoices_billed": [
      {
        "invoice_number": "INV-2026-8100",
        "amount": 5000.00,
        "date": "2026-09-10",
        "status": "PAID"
      }
    ]
  },
  "PO-2026-103": {
    "po_number": "PO-2026-103",
    "vendor_id": "VEND-003",
    "vendor_name": "NexGen Hardware Systems",
    "issue_date": "2026-10-01",
    "status": "OPEN",
    "description": "Developer Workstations & Dual-Monitor Hubs",
    "total_amount": 5000.00,
    "previously_invoiced": 0.00,
    "remaining_balance": 5000.00,
    "currency": "USD",
    "line_items": [
      {
        "item_id": "ITEM-301",
        "description": "Developer Workstation Pro Max",
        "quantity": 2,
        "unit_price": 2500.00,
        "total": 5000.00
      }
    ],
    "invoices_billed": []
  },
  "PO-2026-104": {
    "po_number": "PO-2026-104",
    "vendor_id": "VEND-004",
    "vendor_name": "Global Office Supplies",
    "issue_date": "2026-10-05",
    "status": "OPEN",
    "description": "Ergonomic Chairs & Dual Monitor Mounting Arms",
    "total_amount": 1850.00,
    "previously_invoiced": 0.00,
    "remaining_balance": 1850.00,
    "currency": "USD",
    "line_items": [
      {
        "item_id": "ITEM-401",
        "description": "Ergonomic Mesh Task Chairs",
        "quantity": 5,
        "unit_price": 300.00,
        "total": 1500.00
      },
      {
        "item_id": "ITEM-402",
        "description": "Dual Monitor Desk Mount Arms",
        "quantity": 7,
        "unit_price": 50.00,
        "total": 350.00
      }
    ],
    "invoices_billed": []
  },
  "PO-2026-105": {
    "po_number": "PO-2026-105",
    "vendor_id": "VEND-005",
    "vendor_name": "Vertex Consulting Partners",
    "issue_date": "2026-07-01",
    "status": "CLOSED",
    "description": "SOC2 Type II Security Compliance Audit",
    "total_amount": 12500.00,
    "previously_invoiced": 12500.00,
    "remaining_balance": 0.00,
    "currency": "USD",
    "line_items": [
      {
        "item_id": "ITEM-501",
        "description": "SOC2 Audit Milestone 1 & 2 Completion",
        "quantity": 1,
        "unit_price": 12500.00,
        "total": 12500.00
      }
    ],
    "invoices_billed": [
      {
        "invoice_number": "INV-2026-7011",
        "amount": 12500.00,
        "date": "2026-08-01",
        "status": "PAID"
      }
    ]
  }
}

DEFAULT_RUNS = [
  {
    "run_id": "RUN-20261115-091422",
    "timestamp": "2026-11-15T09:14:22Z",
    "invoice_number": "INV-2026-8100",
    "vendor_name": "Apex Logistics LLC",
    "vendor_id": "VEND-002",
    "po_number": "PO-2026-102",
    "invoice_total": 5000.00,
    "po_total": 10000.00,
    "status": "APPROVED",
    "decision_type": "TOUCHLESS_APPROVED",
    "confidence_score": 0.99,
    "latency_ms": 420,
    "summary": "Initial milestone draw on PO-2026-102. Line items, bank routing, and tax ID matched master ledger.",
    "flags": []
  },
  {
    "run_id": "RUN-20261115-113010",
    "timestamp": "2026-11-15T11:30:10Z",
    "invoice_number": "INV-2026-7011",
    "vendor_name": "Vertex Consulting Partners",
    "vendor_id": "VEND-005",
    "po_number": "PO-2026-105",
    "invoice_total": 12500.00,
    "po_total": 12500.00,
    "status": "APPROVED",
    "decision_type": "TOUCHLESS_APPROVED",
    "confidence_score": 0.98,
    "latency_ms": 380,
    "summary": "Full milestone invoice matched PO-2026-105. PO closed automatically.",
    "flags": []
  },
  {
    "run_id": "RUN-20261115-142250",
    "timestamp": "2026-11-15T14:22:50Z",
    "invoice_number": "INV-2026-5502",
    "vendor_name": "Unknown Express Logistics",
    "vendor_id": None,
    "po_number": None,
    "invoice_total": 850.00,
    "po_total": None,
    "status": "REJECTED",
    "decision_type": "REJECTED",
    "confidence_score": 0.42,
    "latency_ms": 290,
    "summary": "Unregistered vendor. Missing PO reference and unverified bank account.",
    "flags": ["VENDOR_UNREGISTERED", "MISSING_PO_NUMBER", "BANK_NOT_VERIFIED"]
  }
]

class Database:
    def __init__(self):
        self._lock = threading.Lock()
        self.vendors: Dict[str, Any] = {}
        self.purchase_orders: Dict[str, Any] = {}
        self.runs: List[Dict[str, Any]] = []
        self.reload()

    def reload(self):
        with self._lock:
            if os.path.exists(VENDORS_FILE):
                with open(VENDORS_FILE, "r", encoding="utf-8") as f:
                    self.vendors = json.load(f)
            else:
                self.vendors = dict(DEFAULT_VENDORS)
                self.save_vendors()

            if os.path.exists(PO_FILE):
                with open(PO_FILE, "r", encoding="utf-8") as f:
                    self.purchase_orders = json.load(f)
            else:
                self.purchase_orders = dict(DEFAULT_POS)
                self.save_pos()

            if os.path.exists(RUNS_FILE):
                with open(RUNS_FILE, "r", encoding="utf-8") as f:
                    self.runs = json.load(f)
            else:
                self.runs = list(DEFAULT_RUNS)
                self.save_runs()

    def reset_defaults(self):
        with self._lock:
            self.vendors = json.loads(json.dumps(DEFAULT_VENDORS))
            self.purchase_orders = json.loads(json.dumps(DEFAULT_POS))
            self.runs = json.loads(json.dumps(DEFAULT_RUNS))
            self.save_vendors()
            self.save_pos()
            self.save_runs()

    def save_runs(self):
        with open(RUNS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.runs, f, indent=2)

    def save_pos(self):
        with open(PO_FILE, "w", encoding="utf-8") as f:
            json.dump(self.purchase_orders, f, indent=2)

    def save_vendors(self):
        with open(VENDORS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.vendors, f, indent=2)

    def get_vendor(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        return self.vendors.get(vendor_id)

    def find_vendor_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        name_clean = name.strip().lower()
        for v in self.vendors.values():
            if v["name"].lower() in name_clean or name_clean in v["name"].lower():
                return v
            for alias in v.get("aliases", []):
                if alias.lower() in name_clean or name_clean in alias.lower():
                    return v
        return None

    def get_po(self, po_number: str) -> Optional[Dict[str, Any]]:
        return self.purchase_orders.get(po_number)

    def find_po_by_vendor_and_amount(self, vendor_id: str, amount: float) -> Optional[Dict[str, Any]]:
        for po in self.purchase_orders.values():
            if po.get("vendor_id") == vendor_id and po.get("status") in ["OPEN", "PARTIALLY_INVOICED"]:
                if abs(po.get("total_amount", 0) - amount) <= 0.05 or abs(po.get("remaining_balance", 0) - amount) <= 0.05:
                    return po
        return None

    def record_run(self, run_record: Dict[str, Any]):
        with self._lock:
            self.runs.insert(0, run_record)
            self.save_runs()

            if run_record.get("status") == "APPROVED" and run_record.get("po_number"):
                po_num = run_record["po_number"]
                if po_num in self.purchase_orders:
                    po = self.purchase_orders[po_num]
                    inv_amt = float(run_record.get("invoice_total", 0.0))
                    po["previously_invoiced"] = round(po.get("previously_invoiced", 0.0) + inv_amt, 2)
                    po["remaining_balance"] = max(0.0, round(po.get("total_amount", 0.0) - po["previously_invoiced"], 2))
                    if po["remaining_balance"] == 0:
                        po["status"] = "CLOSED"
                    else:
                        po["status"] = "PARTIALLY_INVOICED"

                    if "invoices_billed" not in po:
                        po["invoices_billed"] = []
                    po["invoices_billed"].append({
                        "invoice_number": run_record.get("invoice_number"),
                        "amount": inv_amt,
                        "date": run_record.get("timestamp", "").split("T")[0],
                        "status": "APPROVED"
                    })
                    self.save_pos()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_runs = len(self.runs)
            if total_runs == 0:
                return {
                    "total_runs": 0,
                    "approved": 0,
                    "review": 0,
                    "rejected": 0,
                    "touchless_rate": 0.0,
                    "total_value": 0.0,
                    "avg_latency": 0
                }
            approved = sum(1 for r in self.runs if r.get("status") == "APPROVED")
            review = sum(1 for r in self.runs if r.get("status") in ["NEEDS_REVIEW", "PENDING_REVIEW"])
            rejected = sum(1 for r in self.runs if r.get("status") == "REJECTED")
            total_value = sum(float(r.get("invoice_total") or 0.0) for r in self.runs if r.get("status") == "APPROVED")
            touchless_rate = round((approved / total_runs) * 100, 1)
            avg_latency = int(sum(int(r.get("latency_ms") or 350) for r in self.runs) / total_runs)

            return {
                "total_runs": total_runs,
                "approved": approved,
                "review": review,
                "rejected": rejected,
                "touchless_rate": touchless_rate,
                "total_value": round(total_value, 2),
                "avg_latency": avg_latency
            }

db = Database()
