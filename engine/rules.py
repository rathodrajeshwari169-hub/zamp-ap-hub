from typing import Dict, Any, List
from .database import db

class ValidationRuleEngine:
    def __init__(self):
        pass

    def evaluate(self, invoice_data: Dict[str, Any], match_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Runs comprehensive compliance, fraud, tolerance, and budget rules.
        Returns a list of evaluated rule outcomes.
        """
        results = []
        vendor = match_result.get("vendor")
        po = match_result.get("po")
        inv_num = invoice_data.get("invoice_number")
        inv_total = float(invoice_data.get("total_amount") or 0.0)

        # -------------------------------------------------------------
        # Rule 1: Mandatory Field Completeness
        # -------------------------------------------------------------
        missing_fields = []
        if not inv_num: missing_fields.append("Invoice Number")
        if not invoice_data.get("invoice_date"): missing_fields.append("Invoice Date")
        if inv_total <= 0: missing_fields.append("Total Amount")
        if not invoice_data.get("vendor_name"): missing_fields.append("Vendor Name")

        if missing_fields:
            results.append({
                "rule_id": "RULE_MANDATORY_FIELDS",
                "rule_name": "Mandatory Tax & Compliance Fields",
                "status": "FAIL",
                "severity": "CRITICAL",
                "message": f"Missing critical required invoice fields: {', '.join(missing_fields)}.",
                "details": {"missing_fields": missing_fields}
            })
        else:
            results.append({
                "rule_id": "RULE_MANDATORY_FIELDS",
                "rule_name": "Mandatory Tax & Compliance Fields",
                "status": "PASS",
                "severity": "INFO",
                "message": "All required tax and invoice identification fields are present.",
                "details": {"invoice_number": inv_num, "date": invoice_data.get("invoice_date"), "total": inv_total}
            })

        # -------------------------------------------------------------
        # Rule 2: Duplicate Invoice Detection
        # -------------------------------------------------------------
        is_duplicate = False
        dup_source = None

        if inv_num and vendor:
            v_id = vendor["id"]
            # Check runs history
            for r in db.runs:
                if r.get("invoice_number") == inv_num and r.get("vendor_id") == v_id and r.get("status") == "APPROVED":
                    is_duplicate = True
                    dup_source = f"Prior Run {r.get('run_id')} on {r.get('timestamp')}"
                    break

            # Check purchase order billed lists
            if not is_duplicate:
                for p in db.purchase_orders.values():
                    for billed in p.get("invoices_billed", []):
                        if billed.get("invoice_number") == inv_num:
                            is_duplicate = True
                            dup_source = f"PO {p['po_number']} records (Amount: ${billed.get('amount')})"
                            break

        if is_duplicate:
            results.append({
                "rule_id": "RULE_DUPLICATE_CHECK",
                "rule_name": "Duplicate Invoice Detection",
                "status": "FAIL",
                "severity": "CRITICAL",
                "message": f"Duplicate invoice detected! Invoice #{inv_num} was already processed ({dup_source}).",
                "details": {"duplicate_source": dup_source}
            })
        else:
            results.append({
                "rule_id": "RULE_DUPLICATE_CHECK",
                "rule_name": "Duplicate Invoice Detection",
                "status": "PASS",
                "severity": "INFO",
                "message": "No duplicate record found in procurement history or active runs.",
                "details": {}
            })

        # -------------------------------------------------------------
        # Rule 3: Vendor Registration & KYC Status
        # -------------------------------------------------------------
        if not vendor:
            results.append({
                "rule_id": "RULE_VENDOR_KYC",
                "rule_name": "Approved Vendor Directory & KYC",
                "status": "FAIL",
                "severity": "CRITICAL",
                "message": f"Vendor '{invoice_data.get('vendor_name')}' is not registered in the Master Vendor Directory.",
                "details": {}
            })
        elif vendor.get("status") != "APPROVED":
            results.append({
                "rule_id": "RULE_VENDOR_KYC",
                "rule_name": "Approved Vendor Directory & KYC",
                "status": "FAIL",
                "severity": "HIGH",
                "message": f"Vendor '{vendor.get('name')}' is currently set to '{vendor.get('status')}'. Payment blocked.",
                "details": {"vendor_status": vendor.get("status")}
            })
        else:
            results.append({
                "rule_id": "RULE_VENDOR_KYC",
                "rule_name": "Approved Vendor Directory & KYC",
                "status": "PASS",
                "severity": "INFO",
                "message": f"Vendor verified: {vendor.get('name')} (ID: {vendor.get('id')}, Tax ID: {vendor.get('tax_id')}).",
                "details": {"vendor_id": vendor.get("id"), "terms": vendor.get("payment_terms")}
            })

        # -------------------------------------------------------------
        # Rule 4: Purchase Order Reconciliation & Tolerance Checks
        # -------------------------------------------------------------
        if not po:
            results.append({
                "rule_id": "RULE_PO_RECONCILIATION",
                "rule_name": "Purchase Order 2-Way Match",
                "status": "FAIL",
                "severity": "CRITICAL",
                "message": "No valid purchase order matched this invoice.",
                "details": {}
            })
        else:
            match_type = match_result.get("match_type")
            remaining = match_result.get("remaining_balance_before", 0.0)
            variance_amt = match_result.get("variance_amount", 0.0)
            variance_pct = match_result.get("variance_percent", 0.0)

            tol_pct_max = float(vendor.get("tolerance_percent", 2.0)) if vendor else 2.0
            tol_amt_max = float(vendor.get("tolerance_amount_max", 100.0)) if vendor else 100.0

            if match_type in ["EXACT_MATCH", "FINAL_PARTIAL_DRAW"]:
                results.append({
                    "rule_id": "RULE_PO_RECONCILIATION",
                    "rule_name": "Purchase Order 2-Way Match",
                    "status": "PASS",
                    "severity": "INFO",
                    "message": f"Exact match with PO {po['po_number']} remaining balance (${remaining:,.2f}).",
                    "details": {"match_type": match_type, "remaining": remaining}
                })
            elif match_type == "PARTIAL_PO_DRAW":
                results.append({
                    "rule_id": "RULE_PO_RECONCILIATION",
                    "rule_name": "Cumulative PO Budget & Split Draw",
                    "status": "PASS",
                    "severity": "INFO",
                    "message": f"Valid partial invoice draw of ${inv_total:,.2f}. Leaves ${match_result.get('remaining_balance_after'):,.2f} remaining on PO {po['po_number']}.",
                    "details": {
                        "po_total": po.get("total_amount"),
                        "previously_invoiced": po.get("previously_invoiced"),
                        "new_balance": match_result.get("remaining_balance_after")
                    }
                })
            elif match_type == "OVER_BILLING":
                # Check tolerance
                if variance_pct <= tol_pct_max and variance_amt <= tol_amt_max:
                    results.append({
                        "rule_id": "RULE_PO_RECONCILIATION",
                        "rule_name": "Purchase Order Tolerance Policy",
                        "status": "WARN",
                        "severity": "MEDIUM",
                        "message": f"Invoice exceeds PO balance by ${variance_amt:,.2f} ({variance_pct}%). Within approved tolerance limit (Max: {tol_pct_max}% or ${tol_amt_max:,.2f}).",
                        "details": {
                            "variance_amount": variance_amt,
                            "variance_percent": variance_pct,
                            "allowed_percent": tol_pct_max,
                            "allowed_amount": tol_amt_max
                        }
                    })
                else:
                    results.append({
                        "rule_id": "RULE_PO_RECONCILIATION",
                        "rule_name": "Purchase Order Tolerance Policy",
                        "status": "FAIL",
                        "severity": "HIGH",
                        "message": f"Over-billing exceeds allowable tolerance! Variance is ${variance_amt:,.2f} ({variance_pct}%), exceeding limit of {tol_pct_max}% / ${tol_amt_max:,.2f}.",
                        "details": {
                            "variance_amount": variance_amt,
                            "variance_percent": variance_pct,
                            "allowed_percent": tol_pct_max
                        }
                    })

        # -------------------------------------------------------------
        # Rule 5: Anti-Fraud & Remittance Bank Verification
        # -------------------------------------------------------------
        inv_bank = invoice_data.get("remittance_bank", {})
        inv_routing = inv_bank.get("routing_number")
        inv_acct = inv_bank.get("account_number")

        if vendor:
            master_bank = vendor.get("remittance_bank", {})
            master_routing = master_bank.get("routing_number")
            master_acct = master_bank.get("account_number")

            if inv_routing or inv_acct:
                routing_mismatch = bool(inv_routing and master_routing and inv_routing != master_routing)
                acct_mismatch = bool(inv_acct and master_acct and inv_acct != master_acct)

                if routing_mismatch or acct_mismatch:
                    results.append({
                        "rule_id": "RULE_BANK_REMITTANCE",
                        "rule_name": "Anti-Fraud Remittance Verification",
                        "status": "FAIL",
                        "severity": "CRITICAL",
                        "message": f"SECURITY ALERT: Remittance bank routing or account on invoice does not match Master Vendor record! "
                                   f"(Invoice Routing: {inv_routing or 'N/A'}, Expected: {master_routing}). Potential payment diversion fraud.",
                        "details": {
                            "invoice_routing": inv_routing,
                            "expected_routing": master_routing,
                            "invoice_account_tail": inv_acct[-4:] if inv_acct else "N/A",
                            "expected_account_tail": master_acct[-4:] if master_acct else "N/A"
                        }
                    })
                else:
                    results.append({
                        "rule_id": "RULE_BANK_REMITTANCE",
                        "rule_name": "Anti-Fraud Remittance Verification",
                        "status": "PASS",
                        "severity": "INFO",
                        "message": f"Remittance bank details verified against approved record ({master_bank.get('bank_name')}).",
                        "details": {"bank_name": master_bank.get("bank_name")}
                    })
            else:
                results.append({
                    "rule_id": "RULE_BANK_REMITTANCE",
                    "rule_name": "Anti-Fraud Remittance Verification",
                    "status": "WARN",
                    "severity": "LOW",
                    "message": "No explicit bank remittance account stated on invoice document. Verified against master file on file.",
                    "details": {}
                })
        else:
            results.append({
                "rule_id": "RULE_BANK_REMITTANCE",
                "rule_name": "Anti-Fraud Remittance Verification",
                "status": "WARN",
                "severity": "MEDIUM",
                "message": "Cannot verify remittance bank details without matched vendor record.",
                "details": {}
            })

        # -------------------------------------------------------------
        # Rule 6: Tax & Line-Item Mathematical Verification
        # -------------------------------------------------------------
        subtotal = float(invoice_data.get("subtotal") or 0.0)
        tax = float(invoice_data.get("tax") or 0.0)
        shipping = float(invoice_data.get("shipping") or 0.0)
        calc_total = round(subtotal + tax + shipping, 2)

        if inv_total > 0 and subtotal > 0:
            math_diff = round(abs(inv_total - calc_total), 2)
            if math_diff > 0.05:
                results.append({
                    "rule_id": "RULE_TAX_MATH",
                    "rule_name": "Tax & Line-Item Mathematical Integrity",
                    "status": "WARN",
                    "severity": "MEDIUM",
                    "message": f"Calculated sum (${subtotal:,.2f} subtotal + ${tax:,.2f} tax + ${shipping:,.2f} shipping = ${calc_total:,.2f}) "
                               f"differs from stated total (${inv_total:,.2f}) by ${math_diff:,.2f}.",
                    "details": {"stated_total": inv_total, "calculated_total": calc_total, "diff": math_diff}
                })
            else:
                results.append({
                    "rule_id": "RULE_TAX_MATH",
                    "rule_name": "Tax & Line-Item Mathematical Integrity",
                    "status": "PASS",
                    "severity": "INFO",
                    "message": f"Financial arithmetic verified (Subtotal: ${subtotal:,.2f}, Tax: ${tax:,.2f}, Shipping: ${shipping:,.2f}).",
                    "details": {"subtotal": subtotal, "tax": tax, "shipping": shipping, "total": inv_total}
                })

        return results

rule_engine = ValidationRuleEngine()
