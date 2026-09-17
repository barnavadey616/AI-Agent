"""
ScamShield Threat Intelligence & Investigation Tools.
Provides regex entity extraction, URL threat heuristics, known scam signature matching,
risk scoring algorithms, and forensic investigation report generation.
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import datetime
import urllib.parse
from pathlib import Path
from taskflow import config
from taskflow.core.tool import tool

# Pre-compiled regex patterns for fraud entity extraction
PHONE_REGEX = re.compile(r'(?:\+?91[\-\s]?)?[6-9]\d{9}\b|\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b')
UPI_REGEX = re.compile(r'\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b')
URL_REGEX = re.compile(r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,8}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)')
CRYPTO_REGEX = re.compile(r'\b(?:0x[a-fA-F0-9]{40}|[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[a-z0-9]{39,59})\b')
AMOUNT_REGEX = re.compile(r'(?:₹|INR|Rs\.?|\$|USD)\s?[\d,]+(?:\.\d{1,2})?|\b[\d,]+(?:\.\d{1,2})?\s?(?:₹|INR|Rs\.?|rupees|dollars)\b', re.IGNORECASE)

# Suspicious Top-Level Domains (TLDs) frequently abused in phishing
SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".club", ".vip", ".work", ".site", ".online", ".live",
    ".buzz", ".loan", ".icu", ".monster", ".fit", ".rest", ".gq", ".cf", ".tk", ".ml"
}

# Known URL Shortener services often used to disguise phishing domains
URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "is.gd", "cutt.ly", "t.co", "rb.gy", "ow.ly", "shorturl.at", "tiny.cc", "goo.gl"
}

# Impersonation keywords target brands commonly used in India & globally
TARGET_BRANDS = [
    "sbi", "hdfc", "icici", "paytm", "phonepe", "gpay", "googlepay",
    "amazon", "flipkart", "fedex", "bluedart", "dhl", "india post",
    "electricity", "power", "bsnl", "jio", "airtel", "kbc", "cbi", "police", "customs"
]

# Signature catalog of known scam archetypes
KNOWN_SCAM_PATTERNS = [
    {
        "id": "upi_pin_refund_scam",
        "name": "Fake UPI Payment / Refund Trap",
        "category": "Financial Fraud",
        "keywords": ["enter upi pin", "pin to receive", "refund approval", "claim cashback", "scan qr to receive", "receive payment pin", "upi pin to credit", "collect request", "refund", "cashback", "enter pin"],
        "severity": "CRITICAL",
        "base_score": 95,
        "description": "Scammer sends a collect request or fake QR code claiming you must enter your UPI PIN to 'receive' money or cashback.",
        "golden_rule": "You NEVER need to enter your UPI PIN to receive money. Entering a PIN always DEBITS your account."
    },
    {
        "id": "telegram_rating_job_scam",
        "name": "Part-Time Task & Telegram Job Scam",
        "category": "Employment Scam",
        "keywords": ["youtube video", "like youtube", "liking youtube", "rating hotels", "review hotel", "google review", "google map", "telegram", "telegram vip", "telegram hr", "part-time", "work-from-home", "work from home", "daily income", "trial task", "paid for trial", "task list", "earn daily"],
        "severity": "HIGH",
        "base_score": 88,
        "description": "Victims are paid small amounts (₹150–₹500) for initial trivial tasks (liking videos/reviews), then trapped into 'prepaid merchant tasks' requiring large deposits that can never be withdrawn.",
        "golden_rule": "Legitimate employers never ask you to pay money or deposit funds to receive freelance tasks or salary."
    },
    {
        "id": "electricity_bill_disconnection_scam",
        "name": "Urgent Utility / Electricity Disconnection Scam",
        "category": "Extortion & Impersonation",
        "keywords": ["electricity", "power will be disconnected", "disconnected tonight", "unpaid bill", "power disconnected", "call electricity officer", "bill update", "bijli bill", "power cutoff"],
        "severity": "HIGH",
        "base_score": 90,
        "description": "Fake SMS claiming power will be shut off immediately unless you call a private mobile number and download a remote desktop app (AnyDesk/TeamViewer).",
        "golden_rule": "Power utilities never send disconnection notices via personal 10-digit mobile numbers giving immediate cutoff deadlines."
    },
    {
        "id": "courier_customs_cbi_extortion",
        "name": "Courier Narcotics / Digital Arrest Extortion",
        "category": "Police / Customs Impersonation",
        "keywords": ["fedex", "dhl", "customs", "narcotics", "digital arrest", "cbi arrest", "illegal package", "passport seized", "police verification", "customs mumbai"],
        "severity": "CRITICAL",
        "base_score": 98,
        "description": "Scammers pose as FedEx/DHL/Police officials claiming a parcel containing narcotics was booked with your Aadhaar, threatening immediate digital arrest unless you transfer funds for 'verification'.",
        "golden_rule": "Police, CBI, and Customs NEVER conduct arrests or legal interrogations over WhatsApp/Skype video calls, nor do they demand money to verify innocence."
    },
    {
        "id": "bank_kyc_pan_block_scam",
        "name": "Urgent Bank Account & Pan Card Deactivation Phishing",
        "category": "Banking Phishing",
        "keywords": ["account blocked", "pan card expired", "kyc update", "prevent block", "download sbi", "netbanking suspended", "kyc expired", "deactivated"],
        "severity": "HIGH",
        "base_score": 92,
        "description": "Phishing SMS warning your bank account or credit card is blocked, directing you to an unverified link or fraudulent APK download to harvest OTPs.",
        "golden_rule": "Banks never send APK files or shortened links to update KYC. Always visit your official banking app or branch."
    },
    {
        "id": "guaranteed_crypto_investment_ponzi",
        "name": "High-Yield Guaranteed Crypto / Forex Investment Scheme",
        "category": "Investment Fraud",
        "keywords": ["guaranteed 300%", "double your money", "vip signals", "crypto trading expert", "daily 10% profit", "guaranteed returns", "no loss guaranteed", "high yield investment"],
        "severity": "HIGH",
        "base_score": 85,
        "description": "Promises unrealistic risk-free returns through unregulated Telegram VIP channels or fake trading dashboard websites.",
        "golden_rule": "No genuine financial investment offers guaranteed double returns without risk. SEBI warns against unauthorized advisory groups."
    },
    {
        "id": "kbc_lottery_prize_scam",
        "name": "Lucky Draw / KBC WhatsApp Lottery Scam",
        "category": "Advance Fee Fraud",
        "keywords": ["kbc lottery", "congratulations won", "lottery winner", "kbc lucky draw", "won 25,00,000", "pay processing fee", "prize winner"],
        "severity": "HIGH",
        "base_score": 89,
        "description": "Audio notes or poster images claiming you won a KBC lottery, asking you to pay tax or processing fees first.",
        "golden_rule": "You cannot win a lottery you never bought a ticket for. Demanding money upfront to release prize funds is 100% fraud."
    }
]


@tool(name="extract_scam_entities", description="Extracts actionable indicators of compromise (IOCs) such as UPI VPAs, phone numbers, URLs, crypto addresses, amounts, and urgency triggers from text.")
def extract_scam_entities(text: str) -> Dict[str, Any]:
    """Scans text for phone numbers, UPI VPAs, URLs, financial amounts, and urgency triggers."""
    if not text:
        return {"phones": [], "upi_ids": [], "urls": [], "crypto_addresses": [], "amounts": [], "urgency_score": 0}

    phones = list(set(PHONE_REGEX.findall(text)))
    # Clean up phone numbers
    phones = [p.strip() for p in phones if len(re.sub(r'\D', '', p)) >= 10]

    raw_upis = UPI_REGEX.findall(text)
    # Filter out common email addresses if not typical UPI handles
    upi_handles = ["okhdfcbank", "oksbi", "okaxis", "okicici", "paytm", "ibl", "ybl", "axl", "upi", "apl", "postbank", "airtel"]
    upi_ids = []
    for u in set(raw_upis):
        domain = u.split("@")[-1].lower()
        if domain in upi_handles or any(h in domain for h in ["bank", "pay", "upi"]):
            upi_ids.append(u)

    urls = list(set(URL_REGEX.findall(text)))
    crypto = list(set(CRYPTO_REGEX.findall(text)))
    amounts = list(set(AMOUNT_REGEX.findall(text)))

    # Urgency keyword analysis
    urgency_words = ["immediately", "urgent", "tonight", "within 2 hours", "blocked", "suspended", "arrest", "cbi", "warrant", "last warning", "24 hours", "penalty"]
    urgency_hits = [w for w in urgency_words if re.search(rf'\b{re.escape(w)}\b', text, re.IGNORECASE)]
    urgency_score = min(100, len(urgency_hits) * 25)

    return {
        "phones": phones,
        "phone_numbers": phones,
        "upi_ids": upi_ids,
        "urls": urls,
        "crypto_addresses": crypto,
        "amounts": amounts,
        "urgency_triggers": urgency_hits,
        "urgency_score": urgency_score,
        "urgency_detected": len(urgency_hits) > 0,
        "urgency_count": len(urgency_hits)
    }


@tool(name="analyze_url_threat", description="Analyzes a suspicious URL or domain for typosquatting, brand impersonation, suspicious TLDs, and phishing patterns.")
def analyze_url_threat(url: str) -> Dict[str, Any]:
    """Inspects URL structure, domain characteristics, TLD risk, and brand spoofing."""
    if not url:
        return {"is_suspicious": False, "risk_score": 0, "signals": [], "flags": []}

    signals = []
    risk_score = 0

    parsed = urllib.parse.urlparse(url if "://" in url else f"http://{url}")
    domain = (parsed.netloc or parsed.path).lower().split(":")[0]

    # Check for IP address as host
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
        signals.append("Direct IP address host used instead of registered domain name.")
        risk_score += 45

    # Check for URL Shorteners
    if domain in URL_SHORTENERS or any(domain.endswith(f".{s}") for s in URL_SHORTENERS):
        signals.append(f"URL shortener '{domain}' detected. Masking destination domains is heavily abused in phishing attacks.")
        risk_score += 40

    # Check TLD
    matched_tld = None
    for tld in SUSPICIOUS_TLDS:
        if domain.endswith(tld):
            matched_tld = tld
            signals.append(f"Suspicious high-risk TLD detected: '{tld}' (often used in cheap disposable phishing domains).")
            risk_score += 35
            break

    # Check APK download link
    if parsed.path.lower().endswith(".apk"):
        signals.append("Direct Android APK executable download link detected. High likelihood of banking trojan or spyware.")
        risk_score += 55

    # Brand typosquatting / spoofing check
    impersonated_brand = None
    for brand in TARGET_BRANDS:
        if brand in domain and not (domain.endswith(f"{brand}.com") or domain.endswith(f"{brand}.in") or domain.endswith(f"{brand}.org")):
            impersonated_brand = brand
            signals.append(f"Potential brand impersonation detected: Domain mentions '{brand.upper()}' but is not an official domain.")
            risk_score += 40
            break

    # Hyphen count & subdomain depth
    hyphens = domain.count("-")
    if hyphens >= 2:
        signals.append(f"Excessive hyphens ({hyphens}) in domain name, typical of phishing disguise.")
        risk_score += 20

    subdomains = domain.split(".")
    if len(subdomains) > 3:
        signals.append("Deep subdomain structure detected, masquerading as legitimate portal.")
        risk_score += 15

    risk_score = min(100, risk_score)
    is_suspicious = risk_score >= 35

    return {
        "url": url,
        "domain": domain,
        "is_suspicious": is_suspicious,
        "risk_score": risk_score,
        "matched_tld": matched_tld,
        "impersonated_brand": impersonated_brand,
        "signals": signals,
        "flags": signals
    }


class SignatureMatchResult(dict):
    """Dict subclass that allows list-like iteration and index access for compatibility."""
    def __iter__(self):
        return iter(self.get("all_matches", []))

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.get("all_matches", [])[item]
        return super().__getitem__(item)

    def __len__(self):
        return len(self.get("all_matches", []))


class ScamReportResult(dict):
    """Dict subclass that allows tuple-unpacking (md, html) for backward compatibility."""
    def __iter__(self):
        yield self["markdown_path"]
        yield self["html_path"]

    def __getitem__(self, item):
        if item == 0:
            return self["markdown_path"]
        if item == 1:
            return self["html_path"]
        return super().__getitem__(item)


@tool(name="match_scam_signatures", description="Matches extracted entities and context text against a catalog of known scam methodologies (UPI fraud, job scam, utility cutoff, etc.).")
def match_scam_signatures(entities_or_text: Any = "", text: Optional[str] = None) -> SignatureMatchResult:
    """Compares message text and entities against database of scam signatures."""
    if text is None:
        if isinstance(entities_or_text, dict):
            text = entities_or_text.get("raw_text", "")
            entities = entities_or_text
        else:
            text = str(entities_or_text)
            entities = extract_scam_entities(text)
    else:
        entities = entities_or_text if isinstance(entities_or_text, dict) else {}
        text = str(text)

    text_lower = text.lower()
    matched = []

    for pattern in KNOWN_SCAM_PATTERNS:
        match_reasons = []
        for kw in pattern["keywords"]:
            if kw.lower() in text_lower:
                match_reasons.append(kw)

        if match_reasons:
            matched.append({
                "id": pattern["id"],
                "name": pattern["name"],
                "category": pattern["category"],
                "severity": pattern["severity"],
                "base_score": pattern["base_score"],
                "description": pattern["description"],
                "golden_rule": pattern["golden_rule"],
                "matched_keywords": match_reasons
            })

    # Sort matches by base score descending
    matched.sort(key=lambda x: x["base_score"], reverse=True)

    return SignatureMatchResult({
        "pattern_count": len(matched),
        "primary_match": matched[0] if matched else None,
        "all_matches": matched
    })


@tool(name="compute_scam_risk_score", description="Computes an aggregate threat score (0-100), risk verdict, and key red flags based on entities, URL signals, and matched scam patterns.")
def compute_scam_risk_score(
    entities: Optional[Dict[str, Any]] = None,
    url_analyses: Optional[List[Dict[str, Any]]] = None,
    pattern_results: Optional[Any] = None,
    raw_text: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Calculates weighted risk score and severity verdict."""
    entities = entities if entities is not None else kwargs.get("entities", {})
    if url_analyses is None:
        url_analyses = kwargs.get("url_threats", [])
    if pattern_results is None:
        pattern_results = kwargs.get("matched_signatures", {})

    if isinstance(pattern_results, list):
        pattern_results = {
            "primary_match": pattern_results[0] if pattern_results else None,
            "all_matches": pattern_results
        }

    score = 0
    red_flags = []

    primary_pattern = pattern_results.get("primary_match") if isinstance(pattern_results, dict) else None
    if primary_pattern:
        score = max(score, primary_pattern.get("base_score", 0))
        red_flags.append(f"Known Threat Signature: Matched **{primary_pattern['name']}** ({primary_pattern['category']}).")

    # Add URL risks
    for u in url_analyses:
        if u.get("is_suspicious"):
            score = max(score, min(100, score + 15))
            for s in u.get("signals", []):
                red_flags.append(f"URL Threat: {s}")

    # Add urgency flags
    if entities.get("urgency_score", 0) >= 50 or entities.get("urgency_detected"):
        score = min(100, score + 10)
        triggers = ", ".join(entities.get("urgency_triggers", []))
        red_flags.append(f"Psychological Pressure: High urgency cues detected ({triggers}).")

    # Check UPI PIN traps
    all_context = f"{raw_text or ''} {str(entities)} {str(red_flags)}".lower()
    if entities.get("upi_ids") and any(w in all_context for w in ["pin", "receive", "refund", "cashback", "credit"]):
        score = max(score, 94)
        red_flags.append("UPI Trap: Asking to enter UPI PIN or click collect request to 'receive' money.")

    # Determine risk verdict
    if score >= 80:
        verdict = "CRITICAL RISK"
        color = "red"
        is_scam = True
    elif score >= 55:
        verdict = "HIGH RISK"
        color = "orange"
        is_scam = True
    elif score >= 30:
        verdict = "SUSPICIOUS / MEDIUM RISK"
        color = "yellow"
        is_scam = False
    else:
        verdict = "LOW RISK / LIKELY SAFE"
        color = "green"
        is_scam = False

    actions = [
        {"step": "Cease All Communication", "description": "Block the sender immediately on WhatsApp/SMS/calls. Do not click links or reply."},
        {"step": "Report to Cyber Helpline 1930", "description": "Immediately dial 1930 (National Cyber Crime Helpline) if any money was debited or identity data shared."},
        {"step": "File Official Cyber Complaint", "description": "Lodge an online cyber fraud complaint at https://cybercrime.gov.in with screenshots and transaction details."},
        {"step": "Protect Banking & UPI Access", "description": "If you shared OTP or clicked suspicious links, immediately freeze your UPI/ATM cards via your official bank app."}
    ]

    return {
        "risk_score": score,
        "risk_level": verdict,
        "verdict": verdict,
        "color": color,
        "is_scam": is_scam,
        "red_flags": red_flags,
        "safety_actions": [f"{a['step']}: {a['description']}" for a in actions],
        "action_steps": actions
    }


def generate_scam_report(investigation_data: Optional[Dict[str, Any]] = None, **kwargs) -> ScamReportResult:
    """Generates Markdown and HTML investigation reports and persists them in outputs/."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    md_filename = f"scam_investigation_{timestamp}.md"
    html_filename = f"scam_investigation_{timestamp}.html"

    out_dir = config.OUTPUTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / md_filename
    html_path = out_dir / html_filename

    if not investigation_data:
        assessment = kwargs.get("assessment", {})
        matched = kwargs.get("matched_signatures", [])
        primary = matched[0] if isinstance(matched, list) and matched else (matched.get("primary_match") if isinstance(matched, dict) else {})
        investigation_data = {
            "input_summary": kwargs.get("investigation_summary", "Unspecified correspondence"),
            "risk_assessment": assessment,
            "pattern_results": {"primary_match": primary},
            "entities": kwargs.get("entities", {}),
            "url_findings": kwargs.get("url_threats", []),
            "safety_actions": [{"step": "Safety Action", "description": a} if isinstance(a, str) else a for a in assessment.get("safety_actions", [])]
        }

    target_input = investigation_data.get("input_summary", "Unspecified correspondence")
    risk_info = investigation_data.get("risk_assessment", {})
    score = risk_info.get("risk_score", 0)
    verdict = risk_info.get("verdict", "UNKNOWN")
    primary_match = investigation_data.get("pattern_results", {}).get("primary_match", {}) or {}
    entities = investigation_data.get("entities", {})
    red_flags = risk_info.get("red_flags", [])
    raw_actions = investigation_data.get("safety_actions", [])
    actions = [{"step": a.split(":", 1)[0], "description": a.split(":", 1)[1].strip()} if isinstance(a, str) and ":" in a else ({"step": "Action", "description": a} if isinstance(a, str) else a) for a in raw_actions]

    # Format Markdown Report
    md_content = f"""# 🛡️ ScamShield AI — Forensic Investigation Report

**Investigation Reference:** `SCAM-{timestamp}`  
**Date:** {datetime.datetime.now().strftime("%B %d, %Y - %H:%M:%S")}  
**Threat Level:** **{verdict}** (Risk Score: {score}/100)  
**Primary Pattern:** {primary_match.get('name', 'Unclassified Threat')}  

---

## 1. Executive Summary
TaskFlow ScamShield evaluated the submitted correspondence against heuristic IOC extractors, known scam repositories, and domain reputation datasets.

- **Threat Verdict:** `{verdict}`
- **Calculated Risk Score:** `{score} / 100`
- **Archetype Classification:** {primary_match.get('name', 'Generic Suspicious Activity')}
- **Category:** {primary_match.get('category', 'Social Engineering')}

> **Core Safety Axiom:**  
> *{primary_match.get('golden_rule', 'Never share OTPs, passwords, or enter UPI PINs for unsolicited requests.')}*

---

## 2. Evidence & Red Flags Detected
"""
    for flag in red_flags:
        md_content += f"- ⚠️ **{flag}**\n"

    md_content += f"""
---

## 3. Extracted Indicators of Compromise (IOCs)
- **Phone Numbers:** {', '.join([f'`{p}`' for p in entities.get('phones', [])]) if entities.get('phones') else 'None extracted'}
- **UPI Handles (VPAs):** {', '.join([f'`{u}`' for u in entities.get('upi_ids', [])]) if entities.get('upi_ids') else 'None extracted'}
- **URLs / Links Analyzed:** {', '.join([f'`{u}`' for u in entities.get('urls', [])]) if entities.get('urls') else 'None extracted'}
- **Monetary Amounts Mentioned:** {', '.join([f'`{a}`' for a in entities.get('amounts', [])]) if entities.get('amounts') else 'None extracted'}
- **Urgency Signals:** {', '.join(entities.get('urgency_triggers', [])) if entities.get('urgency_triggers') else 'None detected'}

---

## 4. Immediate Safety Action Plan
"""
    for act in actions:
        md_content += f"1. **{act.get('step', 'Action')}**: {act.get('description', '')}\n"

    md_content += """
---
*Report autonomously generated by TaskFlow AI ScamShield Forensic Investigation Suite. Report cyber crime to 1930 or https://cybercrime.gov.in.*
"""

    md_path.write_text(md_content, encoding="utf-8")

    # Format Standalone HTML Report
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ScamShield Forensic Report — {timestamp}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; margin: 0; line-height: 1.6; }}
    .container {{ max-width: 800px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 2rem; border: 1px solid #334155; }}
    .badge {{ display: inline-block; padding: 4px 12px; border-radius: 9999px; font-weight: 700; font-size: 0.85rem; text-transform: uppercase; }}
    .badge-red {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }}
    .badge-yellow {{ background: rgba(234, 179, 8, 0.2); color: #eab308; border: 1px solid #eab308; }}
    .badge-green {{ background: rgba(34, 197, 94, 0.2); color: #22c55e; border: 1px solid #22c55e; }}
    .score-banner {{ display: flex; align-items: center; justify-content: space-between; background: #0b1329; padding: 1.25rem 1.5rem; border-radius: 10px; margin: 1.5rem 0; }}
    .score-circle {{ font-size: 2.2rem; font-weight: 900; color: #ef4444; }}
    .axiom {{ background: rgba(99, 102, 241, 0.15); border-left: 4px solid #6366f1; padding: 1rem 1.25rem; border-radius: 6px; margin: 1.5rem 0; }}
    .red-flag {{ background: rgba(239, 68, 68, 0.1); border-left: 3px solid #ef4444; padding: 8px 12px; margin: 8px 0; border-radius: 4px; }}
    h1, h2, h3 {{ color: #f8fafc; }}
    code {{ background: #334155; padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #38bdf8; }}
    ol {{ padding-left: 1.5rem; }}
    li {{ margin: 6px 0; }}
  </style>
</head>
<body>
  <div class="container">
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <h1>🛡️ ScamShield Forensic Audit</h1>
      <span class="badge {'badge-red' if score >= 55 else ('badge-yellow' if score >= 30 else 'badge-green')}">{verdict}</span>
    </div>
    <p style="color:#94a3b8; font-size:0.9rem;">Reference: <code>SCAM-{timestamp}</code> | National Helpline: <strong>1930</strong></p>

    <div class="score-banner">
      <div>
        <h3 style="margin:0 0 6px 0;">{primary_match.get('name', 'Unclassified Threat')}</h3>
        <p style="margin:0; color:#cbd5e1; font-size:0.9rem;">{primary_match.get('description', 'Forensic scan complete.')}</p>
      </div>
      <div style="text-align:right;">
        <span style="font-size:0.8rem; text-transform:uppercase; color:#94a3b8;">Risk Index</span>
        <div class="score-circle">{score}<span style="font-size:1.1rem; color:#94a3b8;">/100</span></div>
      </div>
    </div>

    <div class="axiom">
      <strong>💡 Golden Security Rule:</strong><br>
      {primary_match.get('golden_rule', 'Never authorize transactions or enter UPI PINs for unsolicited incoming messages.')}
    </div>

    <h2>⚠️ Red Flags & Evidence</h2>
    {''.join([f'<div class="red-flag">⚠️ {f}</div>' for f in red_flags])}

    <h2>🔍 Extracted Indicators of Compromise (IOCs)</h2>
    <ul>
      <li><strong>Phone Numbers:</strong> {', '.join([f'<code>{p}</code>' for p in entities.get('phones', [])]) if entities.get('phones') else 'None'}</li>
      <li><strong>UPI Handles:</strong> {', '.join([f'<code>{u}</code>' for u in entities.get('upi_ids', [])]) if entities.get('upi_ids') else 'None'}</li>
      <li><strong>URLs Analyzed:</strong> {', '.join([f'<code>{u}</code>' for u in entities.get('urls', [])]) if entities.get('urls') else 'None'}</li>
      <li><strong>Amounts Mentioned:</strong> {', '.join([f'<code>{a}</code>' for a in entities.get('amounts', [])]) if entities.get('amounts') else 'None'}</li>
    </ul>

    <h2>🛡️ Actionable Safety Instructions</h2>
    <ol>
      {''.join([f"<li><strong>{act.get('step', 'Action')}:</strong> {act.get('description', '')}</li>" for act in actions])}
    </ol>
  </div>
</body>
</html>
"""
    html_path.write_text(html_content, encoding="utf-8")

    return ScamReportResult({
        "markdown_path": str(md_path),
        "html_path": str(html_path),
        "markdown_file": md_filename,
        "html_file": html_filename,
        "artifacts": [md_filename, html_filename]
    })
