"""
ScamShield — Autonomous Cyber Threat & Scam Investigation Agent.
Ingests screenshots, WhatsApp chats, SMS, emails, or URLs, performs multi-stage forensic analysis,
extracts indicators of compromise (IOCs), matches scam signatures, calculates risk scores,
and generates actionable safety advisories and audit reports.
"""

from typing import Dict, Any, List, Optional
import base64
from pathlib import Path
from taskflow.core.agent import BaseAgent
from taskflow.tools.scam_tools import (
    extract_scam_entities,
    analyze_url_threat,
    match_scam_signatures,
    compute_scam_risk_score,
    generate_scam_report,
)


class ScamShieldAgent(BaseAgent):
    def __init__(self, llm_provider=None):
        super().__init__(
            name="ScamShieldAgent",
            role="Autonomous Cyber Threat & Scam Investigation Specialist",
            system_instruction="""You are ScamShield AI, an autonomous cyber fraud investigator and digital forensics specialist.
Your mission is to protect citizens and enterprises from digital fraud, fake UPI payment/refund traps,
employment Telegram scams, electricity disconnection extortion, courier/customs digital arrest threats, and bank phishing.
You analyze evidence methodically, pinpoint exact red flags, explain the deception mechanism, and provide
clear, decisive, and immediate safety actions (including contacting 1930 Cyber Helpline and cybercrime.gov.in).""",
            tools=[extract_scam_entities, analyze_url_threat, match_scam_signatures, compute_scam_risk_score],
            llm_provider=llm_provider
        )

    def investigate(
        self,
        text: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_base64: Optional[str] = None,
        file_path: Optional[str] = None,
        sample_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes an autonomous multi-stage scam investigation on submitted text, screenshot, or file.
        """
        self._emit("start", {"agent": self.name, "task": "scam_investigation"})

        raw_evidence = text or ""

        # Handle preset demonstration sample
        if sample_id:
            from taskflow import config
            samples_dir = config.BASE_DIR / "demo_data" / "scam_samples"
            if sample_id == "upi_refund":
                img_p = samples_dir / "upi_refund_scam.png"
                if img_p.exists():
                    file_path = str(img_p)
                txt_p = samples_dir / "upi_refund_scam.txt"
                if txt_p.exists():
                    raw_evidence = txt_p.read_text(encoding="utf-8")
            elif sample_id == "telegram_job":
                txt_p = samples_dir / "telegram_job_scam.txt"
                if txt_p.exists():
                    raw_evidence = txt_p.read_text(encoding="utf-8")
            elif sample_id in ["electricity_cut", "electricity_sms"]:
                txt_p = samples_dir / "electricity_cut_sms.txt"
                if txt_p.exists():
                    raw_evidence = txt_p.read_text(encoding="utf-8")
            elif sample_id == "fedex_customs":
                txt_p = samples_dir / "fedex_customs_phish.txt"
                if txt_p.exists():
                    raw_evidence = txt_p.read_text(encoding="utf-8")

        # Stage 1: Ingestion & Multimodal OCR
        image_payload = None

        if image_base64:
            try:
                # Strip data URL prefix if present
                if "," in image_base64:
                    image_base64 = image_base64.split(",", 1)[1]
                image_bytes = base64.b64decode(image_base64)
            except Exception as e:
                self._emit("log", {"level": "warn", "message": f"Could not decode base64 image: {e}"})

        elif file_path:
            p = Path(file_path)
            if p.exists():
                if p.suffix.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
                    image_bytes = p.read_bytes()
                else:
                    raw_evidence += "\n" + p.read_text(encoding="utf-8", errors="ignore")

        if image_bytes:
            image_payload = [{"data": image_bytes, "mime_type": "image/png"}]
            self._emit("reasoning", {
                "step": "OCR & Vision Inspection",
                "details": f"Analyzing image screenshot ({len(image_bytes)} bytes) using Gemini Vision OCR..."
            })

            # Call Gemini Vision to extract text and describe visual anomalies
            ocr_prompt = (
                "You are an expert digital forensics examiner. Examine this screenshot/image thoroughly. "
                "1. Transcribe all visible text exactly (including SMS headers, sender names, WhatsApp timestamps, UPI handles, amounts). "
                "2. Identify any logos (PhonePe, GPay, Paytm, SBI, FedEx, Police) and note if they appear fake, spoofed, or low-resolution. "
                "3. Provide the full transcribed text content."
            )
            ocr_res = self.llm.generate(prompt=ocr_prompt, images=image_payload)
            extracted_image_text = ocr_res.content or ""
            raw_evidence = f"{raw_evidence}\n\n[Extracted from Screenshot]:\n{extracted_image_text}".strip()
            self._emit("tool_result", {"tool": "gemini_vision_ocr", "extracted_len": len(extracted_image_text)})

        if not raw_evidence:
            raw_evidence = "Urgent: Your account is blocked. Call customer care immediately."

        # Stage 2: Entity Extraction (IOCs)
        self._emit("reasoning", {
            "step": "Entity & Indicator Extraction",
            "details": "Scanning evidence for phone numbers, UPI VPAs, URLs, financial amounts, and psychological urgency triggers..."
        })
        entities = extract_scam_entities(raw_evidence)
        self._emit("tool_result", {
            "tool": "extract_scam_entities",
            "phones": entities.get("phones", []),
            "upi_ids": entities.get("upi_ids", []),
            "urls": entities.get("urls", []),
            "amounts": entities.get("amounts", []),
            "urgency_triggers": entities.get("urgency_triggers", [])
        })

        # Stage 3: URL & Domain Threat Analysis
        url_findings = []
        for u in entities.get("urls", []):
            self._emit("reasoning", {
                "step": "URL Threat Inspection",
                "details": f"Analyzing link: {u} for typosquatting, suspicious TLDs, and credential harvesting patterns..."
            })
            u_analysis = analyze_url_threat(u)
            url_findings.append(u_analysis)
            self._emit("tool_result", {"tool": "analyze_url_threat", "url": u, "risk": u_analysis.get("risk_score", 0)})

        # Stage 4: Scam Pattern Matching
        self._emit("reasoning", {
            "step": "Pattern Signature Matching",
            "details": "Comparing threat signals against national & global fraud archetypes (UPI refund, job scam, digital arrest, utility cutoff)..."
        })
        pattern_results = match_scam_signatures(entities, raw_evidence)
        primary = pattern_results.get("primary_match")
        self._emit("tool_result", {
            "tool": "match_scam_signatures",
            "matched_pattern": primary.get("name") if primary else "Unclassified",
            "category": primary.get("category") if primary else "Unknown"
        })

        # Stage 5: Risk Scoring & Threat Verdict
        self._emit("reasoning", {
            "step": "Risk Scoring & Assessment",
            "details": "Calculating weighted threat index and formulating evidence breakdown..."
        })
        risk_info = compute_scam_risk_score(entities, url_findings, pattern_results)

        # Stage 6: Formulate Actionable Countermeasures
        actions = []
        if risk_info.get("is_scam"):
            if "upi" in str(primary).lower() or entities.get("upi_ids"):
                actions.append({
                    "step": "DO NOT Enter UPI PIN",
                    "description": "Never type your 4 or 6 digit UPI PIN or approve collect requests. Receiving money or refunds NEVER requires a PIN."
                })
            if entities.get("urls"):
                actions.append({
                    "step": "Do NOT Click or Download",
                    "description": "Never open unverified links or download APK files. They frequently install remote access trojans (AnyDesk, SMS forwarders)."
                })
            if entities.get("phones"):
                actions.append({
                    "step": "Block & Report Sender",
                    "description": f"Block the sender number(s) {', '.join(entities['phones'])} on WhatsApp and report as spam on Truecaller."
                })
            actions.append({
                "step": "Report to Cyber Helpline (1930)",
                "description": "If any money was transferred, call the National Cyber Crime Reporting Helpline at **1930** within the golden hour, or file a complaint at **cybercrime.gov.in**."
            })
        else:
            actions.append({
                "step": "Standard Vigilance",
                "description": "No explicit known scam signatures detected. Continue to verify sender identity through official customer support channels."
            })

        # Stage 7: Generate Deliverables (Markdown & HTML Reports)
        investigation_data = {
            "input_summary": raw_evidence[:200] + "..." if len(raw_evidence) > 200 else raw_evidence,
            "entities": entities,
            "url_findings": url_findings,
            "pattern_results": pattern_results,
            "risk_assessment": risk_info,
            "safety_actions": actions
        }
        md_file, html_file = generate_scam_report(investigation_data)
        self._emit("tool_result", {"tool": "generate_scam_report", "md_file": md_file, "html_file": html_file})

        # Format comprehensive response summary
        primary_name = primary.get("name", "Social Engineering Threat") if primary else "Suspicious Message"
        score = risk_info.get("risk_score", 0)
        verdict = risk_info.get("verdict", "HIGH RISK")

        red_flags_markdown = "\n".join([f"- ⚠️ **{f}**" for f in risk_info.get("red_flags", [])]) or "- No critical red flags identified."
        actions_markdown = "\n".join([f"{i+1}. **{a['step']}**: {a['description']}" for i, a in enumerate(actions)])

        iocs_list = []
        if entities.get("phones"):
            iocs_list.append(f"**Phone:** `{', '.join(entities['phones'])}`")
        if entities.get("upi_ids"):
            iocs_list.append(f"**UPI VPA:** `{', '.join(entities['upi_ids'])}`")
        if entities.get("urls"):
            iocs_list.append(f"**Link:** `{', '.join(entities['urls'])}`")
        if entities.get("amounts"):
            iocs_list.append(f"**Amount:** `{', '.join(entities['amounts'])}`")
        iocs_markdown = " • ".join(iocs_list) if iocs_list else "None detected"

        summary_reply = f"""### 🛡️ ScamShield AI — Forensic Investigation Complete

**Threat Assessment:** **{verdict}**  
**Threat Risk Index:** `🔴 {score} / 100`  
**Identified Scam Archetype:** **{primary_name}**  

---

#### 💡 Golden Protection Rule:
> **{primary.get('golden_rule', 'Never authorize payments, enter UPI PINs, or share OTPs for unsolicited messages.') if primary else 'Always verify sender credentials through official verified channels.'}**

---

#### ⚠️ Evidence & Red Flags:
{red_flags_markdown}

---

#### 🔍 Extracted Indicators of Compromise (IOCs):
{iocs_markdown}

---

#### 🚨 Immediate Safety Action Plan:
{actions_markdown}
"""

        self._emit("complete", {"agent": self.name, "verdict": verdict, "score": score})

        return {
            "success": True,
            "verdict": verdict,
            "risk_score": score,
            "risk_level": verdict,
            "is_scam": risk_info.get("is_scam", False),
            "primary_pattern": primary_name,
            "evidence_chain": risk_info.get("red_flags", []),
            "entities": entities,
            "url_findings": url_findings,
            "red_flags": risk_info.get("red_flags", []),
            "safety_actions": actions,
            "summary": summary_reply,
            "reply": summary_reply,
            "markdown_report": md_file,
            "html_report": html_file,
            "artifacts": [md_file, html_file],
            "raw_evidence": raw_evidence
        }
