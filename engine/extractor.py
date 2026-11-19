import re
import os
from typing import Dict, Any, List, Optional

try:
    import objc
    from Foundation import NSURL
    objc.loadBundle('PDFKit', bundle_path='/System/Library/Frameworks/PDFKit.framework', module_globals=globals())
    PDFDocument = objc.lookUpClass('PDFDocument')
    PDFKIT_AVAILABLE = True
except Exception:
    PDFKIT_AVAILABLE = False


def extract_raw_text(file_path: str) -> str:
    """Extract raw text from PDF or text file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        if PDFKIT_AVAILABLE:
            ns_url = NSURL.fileURLWithPath_(os.path.abspath(file_path))
            pdf_doc = PDFDocument.alloc().initWithURL_(ns_url)
            if pdf_doc:
                text = pdf_doc.string() or ""
                if text.strip():
                    return text

        # Cross-platform path (Linux / cloud hosts): pypdf text layer
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text = "\n".join((pg.extract_text() or "") for pg in reader.pages)
            if text.strip():
                return text
        except Exception:
            pass

        # Last-resort fallback using string scraping
        try:
            with open(file_path, "rb") as f:
                content = f.read().decode("latin1", errors="ignore")
                text_chunks = re.findall(r"\(([^\(\)]+)\)\s*Tj", content)
                if text_chunks:
                    return "\n".join(text_chunks)
        except Exception:
            pass

    # Default text / utf-8 reader
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


class InvoiceExtractor:
    def __init__(self):
        pass

    def parse(self, raw_text: str) -> Dict[str, Any]:
        """
        Extracts structured AP invoice fields with robust regex heuristics,
        line item parsing, and remittance bank details.
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        data: Dict[str, Any] = {
            "invoice_number": None,
            "po_number": None,
            "vendor_name": None,
            "invoice_date": None,
            "due_date": None,
            "subtotal": 0.0,
            "tax": 0.0,
            "shipping": 0.0,
            "total_amount": 0.0,
            "remittance_bank": {
                "bank_name": None,
                "routing_number": None,
                "account_number": None
            },
            "line_items": [],
            "raw_text": raw_text,
            "confidence_score": 0.0,
            "extraction_quality": "HIGH"
        }

        # 1. Invoice Number (strictly avoid matching words like 'invoices@email.com' or header 'INVOICE')
        inv_match = re.search(r'(?:Invoice\s*(?:Number|No|Num|#)|Inv\s*(?:Number|No|#)|Bill\s*#)[:\s]+([A-Z0-9\-_]+)', raw_text, re.IGNORECASE)
        if inv_match and inv_match.group(1).lower() not in ['date', 'status', 'due', 'amount', 'total']:
            data["invoice_number"] = inv_match.group(1).strip()
        else:
            inv_code = re.search(r'\bINV-[0-9]{4}-[0-9]+', raw_text, re.IGNORECASE)
            if inv_code:
                data["invoice_number"] = inv_code.group(0).strip()

        # 2. PO Number
        po_match = re.search(r'(?:Purchase\s*Order|PO\s*(?:Number|No|Num|#)|P\.O\.\s*(?:Number|No|Num|#)|PO\s*:)[:\s]*([A-Z0-9\-_]{4,20})', raw_text, re.IGNORECASE)
        if po_match and po_match.group(1).lower() not in ['date', 'status', 'due', 'amount', 'on', 'number']:
            data["po_number"] = po_match.group(1).strip()
        else:
            po_code = re.search(r'\bPO-[0-9]{4}-[0-9]+', raw_text, re.IGNORECASE)
            if po_code:
                data["po_number"] = po_code.group(0).strip()

        # 3. Dates
        date_patterns = [
            r'(?:Invoice\s*Date|Date)[:\s]*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})',
            r'(?:Invoice\s*Date|Date)[:\s]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})',
            r'(?:Invoice\s*Date|Date)[:\s]*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})'
        ]
        for pat in date_patterns:
            m = re.search(pat, raw_text, re.IGNORECASE)
            if m:
                data["invoice_date"] = m.group(1).strip()
                break

        due_patterns = [
            r'(?:Due\s*Date)[:\s]*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})',
            r'(?:Due\s*Date)[:\s]*([0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})',
            r'(?:Due\s*Date)[:\s]*([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})'
        ]
        for pat in due_patterns:
            m = re.search(pat, raw_text, re.IGNORECASE)
            if m:
                data["due_date"] = m.group(1).strip()
                break

        # 4. Vendor Name extraction
        vendor_match = re.search(r'(?:Vendor|Supplier|From|Company|Billed\s*By)[:\s]*([A-Za-z0-9\s,\.]{3,50})', raw_text, re.IGNORECASE)
        if vendor_match:
            candidate = vendor_match.group(1).strip().split("\n")[0]
            candidate = re.sub(r'(?:Invoice|Tax\s*ID|Tel|Email|Date).*', '', candidate, flags=re.IGNORECASE).strip()
            if len(candidate) > 2:
                data["vendor_name"] = candidate

        # If vendor not found by label, check top lines for corporate entities
        if not data["vendor_name"]:
            for line in lines[:5]:
                clean_line = line.strip()
                if any(kw in clean_line.lower() for kw in ["corp", "corporation", "inc", "llc", "systems", "logistics", "cloud", "supplies", "partners", "solutions"]):
                    data["vendor_name"] = clean_line
                    break

        # 5. Financial Totals
        # Check explicit Grand Total / Total Due / Total Amount first
        tot_m = re.search(r'(?:Grand\s*Total|Total\s*Due|Balance\s*Due|Total\s*Amount)[:\s]+\$?([0-9,]+\.[0-9]{2})', raw_text, re.IGNORECASE)
        if not tot_m:
            tot_m = re.search(r'\bTotal[:\s]+\$?([0-9,]+\.[0-9]{2})', raw_text, re.IGNORECASE)
        if tot_m:
            try:
                data["total_amount"] = float(tot_m.group(1).replace(",", ""))
            except ValueError:
                pass

        # Subtotal
        sub_match = re.search(r'(?:Subtotal|Sub-Total|Net\s*Amount)[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)', raw_text, re.IGNORECASE)
        if sub_match:
            try:
                data["subtotal"] = float(sub_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # Tax
        tax_match = re.search(r'(?:Tax|Sales\s*Tax|VAT|GST)[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)', raw_text, re.IGNORECASE)
        if tax_match:
            try:
                data["tax"] = float(tax_match.group(1).replace(",", ""))
            except ValueError:
                pass

        # Shipping / Freight
        ship_match = re.search(r'(?:Shipping|Freight|Handling|Delivery)[:\s]*\$?\s*([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)', raw_text, re.IGNORECASE)
        if ship_match:
            try:
                data["shipping"] = float(ship_match.group(1).replace(",", ""))
            except ValueError:
                pass

        if data["subtotal"] == 0.0 and data["total_amount"] > 0.0:
            data["subtotal"] = round(data["total_amount"] - data["tax"] - data["shipping"], 2)

        # 6. Remittance Banking Details
        routing_match = re.search(r'(?:Routing|ABA|RTN)\s*(?:Number|#|No)?[:\s]+([0-9]{9})', raw_text, re.IGNORECASE)
        if routing_match:
            data["remittance_bank"]["routing_number"] = routing_match.group(1).strip()

        acct_match = re.search(r'(?:Account|Acct|Acc)\s*(?:Number|#|No)?[:\s]+([0-9]{8,14})', raw_text, re.IGNORECASE)
        if acct_match:
            data["remittance_bank"]["account_number"] = acct_match.group(1).strip()

        bank_name_match = re.search(r'(?:Bank\s*Name|Remit\s*To\s*Bank|Bank)[:\s]*([A-Za-z0-9\s,\.]{4,35})', raw_text, re.IGNORECASE)
        if bank_name_match:
            b_name = bank_name_match.group(1).strip().split("\n")[0]
            data["remittance_bank"]["bank_name"] = re.sub(r'(?:Routing|Account|Date|Tel).*', '', b_name, flags=re.IGNORECASE).strip()

        # 7. Line Items Parser
        line_item_pat = re.compile(r'([A-Za-z0-9\s\(\)\-_/]{4,50})\s+(\d+)\s+\$?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2}))\s+\$?([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2}))')
        for match in line_item_pat.finditer(raw_text):
            desc, qty, unit_p, tot = match.groups()
            desc_clean = desc.strip()
            if any(h in desc_clean.lower() for h in ["item", "description", "qty", "quantity", "unit price", "subtotal", "line items"]):
                continue
            try:
                data["line_items"].append({
                    "description": desc_clean,
                    "quantity": int(qty),
                    "unit_price": float(unit_p.replace(",", "")),
                    "total": float(tot.replace(",", ""))
                })
            except ValueError:
                pass

        # 8. Confidence Score
        score = 0.0
        if data["invoice_number"]: score += 0.25
        if data["total_amount"] > 0: score += 0.25
        if data["vendor_name"]: score += 0.20
        if data["invoice_date"]: score += 0.15
        if data["po_number"]: score += 0.10
        if data["remittance_bank"]["routing_number"]: score += 0.05

        data["confidence_score"] = round(min(1.0, score), 2)
        if data["confidence_score"] < 0.5:
            data["extraction_quality"] = "LOW"
        elif data["confidence_score"] < 0.8:
            data["extraction_quality"] = "MEDIUM"
        else:
            data["extraction_quality"] = "HIGH"

        return data

extractor = InvoiceExtractor()
