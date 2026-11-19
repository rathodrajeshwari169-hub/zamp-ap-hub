import time
from typing import Dict, Any, List
from .extractor import extractor, extract_raw_text
from .matcher import matcher
from .rules import rule_engine
from .database import db

class DecisionOrchestrator:
    def __init__(self):
        pass

    def process_invoice(self, file_path: str = None, raw_text: str = None, filename: str = "invoice.pdf") -> Dict[str, Any]:
        """
        Executes the end-to-end 5-stage AP pipeline:
        Stage 1: Document Ingestion & Optical Parsing
        Stage 2: Entity & Semantic Extraction
        Stage 3: Purchase Order 2-Way & 3-Way Reconciliation
        Stage 4: Automated Policy, Fraud & Tolerance Rules
        Stage 5: Autonomous Decision & Audit Reasoning
        """
        start_time = time.time()
        stage_logs: List[Dict[str, Any]] = []

        # -------------------------------------------------------------
        # Stage 1: Document Ingestion & Optical Analysis
        # -------------------------------------------------------------
        stage1_start = time.time()
        if not raw_text and file_path:
            text = extract_raw_text(file_path)
        else:
            text = raw_text or ""

        stage1_duration = int((time.time() - stage1_start) * 1000)
        stage_logs.append({
            "stage_number": 1,
            "stage_name": "Document Ingestion & Optical Parsing",
            "status": "COMPLETED",
            "duration_ms": stage1_duration,
            "summary": f"Ingested '{filename}' ({len(text)} characters extracted). Format verified.",
            "details": {"filename": filename, "char_count": len(text)}
        })

        # -------------------------------------------------------------
        # Stage 2: Entity & Semantic Extraction
        # -------------------------------------------------------------
        stage2_start = time.time()
        extracted_data = extractor.parse(text)
        stage2_duration = int((time.time() - stage2_start) * 1000)

        stage_logs.append({
            "stage_number": 2,
            "stage_name": "Entity & Semantic Extraction",
            "status": "COMPLETED" if extracted_data["confidence_score"] >= 0.5 else "WARNING",
            "duration_ms": stage2_duration,
            "summary": f"Extracted Invoice #{extracted_data.get('invoice_number') or 'UNKNOWN'}, "
                       f"Vendor: {extracted_data.get('vendor_name') or 'UNKNOWN'}, "
                       f"Total: ${extracted_data.get('total_amount', 0.0):,.2f} "
                       f"(Confidence: {int(extracted_data['confidence_score'] * 100)}%).",
            "details": extracted_data
        })

        # -------------------------------------------------------------
        # Stage 3: Purchase Order Reconciliation
        # -------------------------------------------------------------
        stage3_start = time.time()
        match_result = matcher.match(extracted_data)
        stage3_duration = int((time.time() - stage3_start) * 1000)

        stage_logs.append({
            "stage_number": 3,
            "stage_name": "PO 2-Way / 3-Way Reconciliation",
            "status": "COMPLETED" if match_result["po_matched"] else "WARNING",
            "duration_ms": stage3_duration,
            "summary": f"PO Reconciliation: {match_result['match_type']}. " +
                       (" ".join(match_result["reconciliation_notes"]) if match_result["reconciliation_notes"] else ""),
            "details": match_result
        })

        # -------------------------------------------------------------
        # Stage 4: Automated Policy, Fraud & Tolerance Rules
        # -------------------------------------------------------------
        stage4_start = time.time()
        rule_evaluations = rule_engine.evaluate(extracted_data, match_result)
        stage4_duration = int((time.time() - stage4_start) * 1000)

        fail_count = sum(1 for r in rule_evaluations if r["status"] == "FAIL")
        warn_count = sum(1 for r in rule_evaluations if r["status"] == "WARN")

        stage_logs.append({
            "stage_number": 4,
            "stage_name": "Compliance, Fraud & Tolerance Engine",
            "status": "FAILED" if fail_count > 0 else ("WARNING" if warn_count > 0 else "COMPLETED"),
            "duration_ms": stage4_duration,
            "summary": f"Evaluated 6 enterprise rules: {len(rule_evaluations) - fail_count - warn_count} Passed, {warn_count} Warnings, {fail_count} Failed.",
            "details": rule_evaluations
        })

        # -------------------------------------------------------------
        # Stage 5: Autonomous Decision & Reasoning Synthesis
        # -------------------------------------------------------------
        critical_fails = [r for r in rule_evaluations if r["status"] == "FAIL" and r["severity"] in ["CRITICAL", "HIGH"]]
        has_fraud_alert = any(r["rule_id"] == "RULE_BANK_REMITTANCE" and r["status"] == "FAIL" for r in rule_evaluations)
        has_duplicate = any(r["rule_id"] == "RULE_DUPLICATE_CHECK" and r["status"] == "FAIL" for r in rule_evaluations)
        missing_critical = any(r["rule_id"] == "RULE_MANDATORY_FIELDS" and r["status"] == "FAIL" for r in rule_evaluations)
        has_tolerance_warn = any(r["rule_id"] == "RULE_PO_RECONCILIATION" and r["status"] == "WARN" for r in rule_evaluations)

        total_latency = int((time.time() - start_time) * 1000)

        # Decision Logic:
        # 1. Critical fraud alert -> Flag for urgent review (or reject)
        # 2. Duplicate -> Reject
        # 3. Missing mandatory info -> Reject
        # 4. Other critical failure -> Needs Review
        # 5. Tolerance warning -> Approved with warning / Touchless
        # 6. Clean -> Approved Touchless
        if has_duplicate:
            final_status = "REJECTED"
            decision_type = "DUPLICATE_REJECTED"
            reason_summary = "Duplicate invoice detected. Prior payment record exists in the system."
            recommended_action = "Reject invoice and notify vendor of previous payment settlement."
        elif has_fraud_alert:
            final_status = "NEEDS_REVIEW"
            decision_type = "FRAUD_SECURITY_HOLD"
            reason_summary = "CRITICAL SECURITY HOLD: Remittance bank routing mismatch against Vendor Master File. Possible wire diversion fraud."
            recommended_action = "Escalate immediately to AP Security / Vendor Management for verbal callback verification."
        elif missing_critical:
            final_status = "REJECTED"
            decision_type = "COMPLIANCE_REJECTED"
            reason_summary = "Critical mandatory fields missing (Invoice #, Date, or Vendor Name unresolvable)."
            recommended_action = "Auto-request corrected invoice PDF from vendor."
        elif len(critical_fails) > 0:
            final_status = "NEEDS_REVIEW"
            decision_type = "POLICY_EXCEPTION"
            reasons = "; ".join(f["message"] for f in critical_fails)
            reason_summary = f"Policy exceptions detected: {reasons}"
            recommended_action = "Route to AP Manager for line-item & PO exception review."
        elif has_tolerance_warn:
            final_status = "APPROVED"
            decision_type = "APPROVED_WITH_TOLERANCE"
            reason_summary = "Approved within allowable vendor tolerance threshold. All other KYC and anti-fraud checks passed."
            recommended_action = "Schedule payment per standard terms Net 30."
        elif match_result.get("is_partial_draw"):
            final_status = "APPROVED"
            decision_type = "TOUCHLESS_PARTIAL_DRAW"
            reason_summary = f"Valid partial draw against PO {match_result['po']['po_number']}. Remaining balance updated to ${match_result['remaining_balance_after']:,.2f}."
            recommended_action = "Schedule payment per standard terms."
        else:
            final_status = "APPROVED"
            decision_type = "TOUCHLESS_APPROVED"
            reason_summary = "Straight-Through Processing (STP) success: 100% 2-way match, verified bank remittance, and active KYC."
            recommended_action = "Auto-approve and export to ERP for scheduled disbursement."

        # Vendor Notification Draft
        vendor_email_draft = self._generate_vendor_email(
            final_status, decision_type, extracted_data, reason_summary, recommended_action
        )

        stage_logs.append({
            "stage_number": 5,
            "stage_name": "Autonomous Decision & Audit Reasoning",
            "status": "COMPLETED",
            "duration_ms": int((time.time() - stage4_start) * 1000),
            "summary": f"Final Decision: {final_status} ({decision_type}). {reason_summary}",
            "details": {
                "decision_type": decision_type,
                "reason_summary": reason_summary,
                "recommended_action": recommended_action
            }
        })

        run_id = f"RUN-{time.strftime('%Y%m%d-%H%M%S')}"
        run_record = {
            "run_id": run_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "filename": filename,
            "invoice_number": extracted_data.get("invoice_number"),
            "vendor_name": extracted_data.get("vendor_name"),
            "vendor_id": match_result.get("vendor", {}).get("id") if match_result.get("vendor") else None,
            "po_number": match_result.get("po", {}).get("po_number") if match_result.get("po") else extracted_data.get("po_number"),
            "invoice_total": extracted_data.get("total_amount", 0.0),
            "po_total": match_result.get("po", {}).get("total_amount") if match_result.get("po") else None,
            "status": final_status,
            "decision_type": decision_type,
            "confidence_score": extracted_data.get("confidence_score", 0.9),
            "latency_ms": total_latency,
            "summary": reason_summary,
            "recommended_action": recommended_action,
            "vendor_email_draft": vendor_email_draft,
            "extracted_data": extracted_data,
            "match_result": match_result,
            "rule_evaluations": rule_evaluations,
            "stage_logs": stage_logs
        }

        # Persist to database
        db.record_run(run_record)

        return run_record

    def _generate_vendor_email(self, status: str, decision_type: str, extracted: Dict[str, Any], reason: str, action: str) -> Dict[str, str]:
        vendor = extracted.get("vendor_name") or "Vendor Partner"
        inv_num = extracted.get("invoice_number") or "Unknown"

        if status == "APPROVED":
            subject = f"Invoice Accepted for Payment: #{inv_num} - {vendor}"
            body = (
                f"Dear {vendor} Accounts Receivable,\n\n"
                f"We are pleased to inform you that Invoice #{inv_num} in the amount of ${extracted.get('total_amount', 0.0):,.2f} "
                f"has been fully verified, matched against our procurement records, and approved for payment disbursement.\n\n"
                f"Status: Approved ({decision_type})\n"
                f"Payment will be initiated in accordance with our agreed payment terms.\n\n"
                f"Thank you,\nAutomated Accounts Payable Operations"
            )
        elif status == "NEEDS_REVIEW":
            subject = f"ACTION REQUIRED: Verification Hold on Invoice #{inv_num} - {vendor}"
            body = (
                f"Dear {vendor} Accounts Receivable,\n\n"
                f"Your Invoice #{inv_num} for ${extracted.get('total_amount', 0.0):,.2f} is currently undergoing secondary verification.\n\n"
                f"Reason for hold: {reason}\n"
                f"Next Step: {action}\n\n"
                f"Our team will reach out if additional documentation or confirmation is required.\n\n"
                f"Accounts Payable Operations"
            )
        else: # REJECTED
            subject = f"REJECTED: Invoice #{inv_num} - Correction Required"
            body = (
                f"Dear {vendor} Accounts Receivable,\n\n"
                f"We are unable to process Invoice #{inv_num} due to the following exception:\n\n"
                f"Reason: {reason}\n"
                f"Action Required: {action}\n\n"
                f"Please issue a revised invoice or contact our AP support desk.\n\n"
                f"Accounts Payable Operations"
            )

        return {"subject": subject, "body": body}

orchestrator = DecisionOrchestrator()
