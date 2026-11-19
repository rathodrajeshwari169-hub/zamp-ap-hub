from typing import Dict, Any, List, Optional
from difflib import SequenceMatcher
from .database import db

def fuzzy_match_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()

class POMatcher:
    def __init__(self):
        pass

    def match(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reconciles extracted invoice data against Master Vendor and PO records.
        """
        vendor_name_extracted = invoice_data.get("vendor_name")
        po_number_extracted = invoice_data.get("po_number")
        invoice_total = float(invoice_data.get("total_amount") or 0.0)

        # 1. Resolve Vendor
        vendor = db.find_vendor_by_name(vendor_name_extracted)
        vendor_id = vendor["id"] if vendor else None

        # 2. Resolve Purchase Order
        po = None
        match_method = "NONE"

        if po_number_extracted:
            po = db.get_po(po_number_extracted)
            if po:
                match_method = "EXPLICIT_PO_NUMBER"
        
        # If PO not found by number or missing, try Vendor + Amount matching
        if not po and vendor_id and invoice_total > 0:
            po = db.find_po_by_vendor_and_amount(vendor_id, invoice_total)
            if po:
                match_method = "INFERRED_VENDOR_AMOUNT"

        # 3. Analyze Reconciliation & Line Items
        result: Dict[str, Any] = {
            "vendor_matched": bool(vendor),
            "vendor": vendor,
            "po_matched": bool(po),
            "po": po,
            "match_method": match_method,
            "match_type": "NO_MATCH",
            "is_partial_draw": False,
            "remaining_balance_before": 0.0,
            "remaining_balance_after": 0.0,
            "variance_amount": 0.0,
            "variance_percent": 0.0,
            "line_reconciliation": [],
            "reconciliation_notes": []
        }

        if not po:
            result["match_type"] = "NO_PO_FOUND"
            result["reconciliation_notes"].append("No matching purchase order found in the procurement ledger.")
            return result

        po_total = float(po.get("total_amount", 0.0))
        previously_invoiced = float(po.get("previously_invoiced", 0.0))
        remaining_balance = float(po.get("remaining_balance", po_total - previously_invoiced))
        
        result["remaining_balance_before"] = remaining_balance
        new_remaining = round(remaining_balance - invoice_total, 2)
        result["remaining_balance_after"] = max(0.0, new_remaining)

        # Variance calculation
        variance_amt = round(invoice_total - remaining_balance, 2)
        variance_pct = round((variance_amt / remaining_balance * 100), 2) if remaining_balance > 0 else 0.0
        result["variance_amount"] = variance_amt
        result["variance_percent"] = variance_pct

        # Determine Match Type
        if abs(variance_amt) <= 0.01:
            if previously_invoiced > 0:
                result["match_type"] = "FINAL_PARTIAL_DRAW"
                result["is_partial_draw"] = True
                result["reconciliation_notes"].append(f"Completes PO {po['po_number']}. Closes remaining balance of ${remaining_balance:,.2f}.")
            else:
                result["match_type"] = "EXACT_MATCH"
                result["reconciliation_notes"].append(f"Exact 100% 2-way match against {po['po_number']}.")
        elif invoice_total < remaining_balance:
            result["match_type"] = "PARTIAL_PO_DRAW"
            result["is_partial_draw"] = True
            result["reconciliation_notes"].append(
                f"Valid partial billing draw of ${invoice_total:,.2f} against ${remaining_balance:,.2f} remaining on {po['po_number']}. "
                f"Anticipated remaining PO balance: ${result['remaining_balance_after']:,.2f}."
            )
        else:
            result["match_type"] = "OVER_BILLING"
            result["reconciliation_notes"].append(
                f"Invoice total (${invoice_total:,.2f}) exceeds remaining PO balance (${remaining_balance:,.2f}) by ${variance_amt:,.2f} ({variance_pct}%)."
            )

        # 4. Line Item 3-Way Reconciliation
        po_lines = po.get("line_items", [])
        inv_lines = invoice_data.get("line_items", [])

        for inv_item in inv_lines:
            best_match = None
            highest_score = 0.0
            for po_item in po_lines:
                score = fuzzy_match_ratio(inv_item["description"], po_item["description"])
                if score > highest_score and score >= 0.5:
                    highest_score = score
                    best_match = po_item

            line_entry = {
                "invoice_item": inv_item,
                "po_item": best_match,
                "match_score": round(highest_score, 2),
                "matched": bool(best_match),
                "qty_match": (inv_item["quantity"] == best_match["quantity"]) if best_match else False,
                "price_match": (abs(inv_item["unit_price"] - best_match["unit_price"]) <= 0.01) if best_match else False
            }
            result["line_reconciliation"].append(line_entry)

        return result

matcher = POMatcher()
