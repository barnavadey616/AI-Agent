"""
F.R.Y.D.A.Y Project Video Demo Generator.
Renders an HD (1280x720 24fps) narrated presentation video explaining the entire project,
complete with futuristic cyber visuals, typography, telemetry cards, and voiceover audio.
"""

import os
import sys
import wave
import math
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import imageio
import imageio_ffmpeg
import pyttsx3
import numpy as np

WIDTH = 1280
HEIGHT = 720
FPS = 24

# Colors
BG_COLOR = (10, 17, 40)
CARD_BG = (16, 26, 60)
CARD_BORDER = (30, 58, 100)
CYAN = (0, 242, 254)
BLUE = (56, 189, 248)
AMAZON_ORANGE = (255, 153, 0)
EMERALD = (52, 211, 153)
ROSE = (244, 63, 94)
WHITE = (255, 255, 255)
MUTED = (148, 163, 184)
SUBTITLE_BG = (7, 12, 28)

# Fonts
FONT_DIR = Path("C:/Windows/Fonts")
FONT_TITLE = ImageFont.truetype(str(FONT_DIR / "segoeuib.ttf"), 42)
FONT_HEADING = ImageFont.truetype(str(FONT_DIR / "segoeuib.ttf"), 28)
FONT_SUBTITLE = ImageFont.truetype(str(FONT_DIR / "segoeuib.ttf"), 18)
FONT_BODY = ImageFont.truetype(str(FONT_DIR / "segoeui.ttf"), 17)
FONT_BODY_BOLD = ImageFont.truetype(str(FONT_DIR / "segoeuib.ttf"), 17)
FONT_CAPTION = ImageFont.truetype(str(FONT_DIR / "segoeui.ttf"), 14)
FONT_MONO = ImageFont.truetype(str(FONT_DIR / "consola.ttf"), 15)
FONT_BADGE = ImageFont.truetype(str(FONT_DIR / "segoeuib.ttf"), 12)

TEMP_DIR = Path("scratch/video_build")
TEMP_DIR.mkdir(parents=True, exist_ok=True)


def synthesize_speech(text: str, output_wav: Path) -> float:
    """Synthesizes speech using pyttsx3 and returns audio duration in seconds."""
    engine = pyttsx3.init()
    engine.setProperty("rate", 165)
    # Prefer female voice if available, else standard
    voices = engine.getProperty("voices")
    for v in voices:
        if "zira" in v.name.lower() or "female" in v.name.lower():
            engine.setProperty("voice", v.id)
            break
    engine.save_to_file(text, str(output_wav))
    engine.runAndWait()

    with wave.open(str(output_wav), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
        duration = frames / float(rate)
    return duration


def draw_card(draw: ImageDraw.ImageDraw, x1, y1, x2, y2, bg=CARD_BG, border=CARD_BORDER, radius=14):
    """Draws a rounded rectangular high-tech card."""
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=bg, outline=border, width=2)


def draw_header(draw: ImageDraw.ImageDraw, title: str, category: str = "AMAZON OPERATIONS AUTONOMOUS COPILOT"):
    """Draws standardized header and category badge."""
    # Category Badge
    draw.text((60, 32), f"⚡ {category.upper()}", font=FONT_BADGE, fill=AMAZON_ORANGE)
    # Title
    draw.text((60, 52), title, font=FONT_HEADING, fill=WHITE)
    # Glowing separator
    draw.line([(60, 96), (WIDTH - 60, 96)], fill=CYAN, width=2)


def draw_subtitles(draw: ImageDraw.ImageDraw, subtitle_text: str, progress: float = 1.0):
    """Draws a sleek bottom subtitle bar with progress indicator."""
    draw.rectangle([0, HEIGHT - 68, WIDTH, HEIGHT], fill=SUBTITLE_BG)
    draw.line([(0, HEIGHT - 68), (WIDTH, HEIGHT - 68)], fill=(20, 35, 75), width=1)
    
    # Progress bar line
    bar_w = int(WIDTH * progress)
    if bar_w > 0:
        draw.line([(0, HEIGHT - 68), (bar_w, HEIGHT - 68)], fill=CYAN, width=3)

    # Subtitle text
    draw.text((40, HEIGHT - 46), f"🎙️  {subtitle_text}", font=FONT_SUBTITLE, fill=WHITE)


# ==============================================================================
# Scene Renderers
# ==============================================================================

def render_scene_1(t_norm: float, subtitle: str) -> Image.Image:
    """Scene 1: Title & Vision"""
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(im)

    # Center Hero Card
    draw_card(d, 120, 100, WIDTH - 120, HEIGHT - 120, bg=(14, 24, 56), border=CYAN, radius=20)
    
    # Badge
    d.text((180, 150), "⚡ AWS & AMAZON ENTERPRISE OPERATIONAL COPILOT", font=FONT_BADGE, fill=AMAZON_ORANGE)
    
    # Title
    d.text((180, 190), "F.R.Y.D.A.Y", font=FONT_TITLE, fill=CYAN)
    
    # Subtitle
    d.text((180, 265), "Next-Gen Autonomous AI Operations, Fulfillment & Supply Chain Copilot", font=FONT_HEADING, fill=WHITE)
    
    # Description
    desc = (
        "An enterprise multi-agent ReAct system engineered to solve actual operational bottlenecks for Amazon:\n"
        "auditing delivery delays, resolving FC conveyor jams, investigating concessions, detecting defective\n"
        "ASINs in reverse logistics, predicting seller stockouts, and neutralizing concession fraud."
    )
    d.text((180, 335), desc, font=FONT_BODY, fill=MUTED, spacing=8)
    
    # Tech pills
    pills = "Google Gemini 2.5 Flash  •  FastAPI + WebSockets  •  Hybrid Lexical/Semantic RAG  •  100% Automated Test Pass (47 Tests)"
    draw_card(d, 180, 480, WIDTH - 180, 530, bg=(10, 18, 42), border=BLUE, radius=10)
    d.text((200, 494), pills, font=FONT_CAPTION, fill=BLUE)

    draw_subtitles(d, subtitle, t_norm)
    return im


def render_scene_2(t_norm: float, subtitle: str) -> Image.Image:
    """Scene 2: Why Generic AI Fails"""
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(im)
    draw_header(d, "The Core Problem: Why Traditional AI Fails in Global Operations", "EXECUTIVE SUMMARY")

    # Left: Generic Chatbots
    draw_card(d, 60, 120, 620, HEIGHT - 90, border=ROSE)
    d.text((90, 145), "❌ Traditional Generic 'Chatbots'", font=FONT_HEADING, fill=ROSE)
    
    pts_left = [
        ("Surface-Level Text Generation:", "Outputs conversational text, but cannot query warehouse telemetry or shipment IDs."),
        ("High Hallucination Risk:", "An incorrect answer can shut down a fulfillment line or issue unauthorized refunds."),
        ("No Operational Action:", "Cannot dispatch technicians, reroute truck freight, or suppress defective Buy Boxes."),
        ("Disconnected from SOPs:", "Fails to strictly enforce authorized Amazon Standard Operating Procedures.")
    ]
    y = 210
    for title, desc in pts_left:
        d.text((90, y), f"• {title}", font=FONT_BODY_BOLD, fill=WHITE)
        d.text((110, y + 24), desc, font=FONT_CAPTION, fill=MUTED)
        y += 75

    # Right: F.R.Y.D.A.Y Copilot
    draw_card(d, 660, 120, WIDTH - 60, HEIGHT - 90, border=CYAN)
    d.text((690, 145), "⚡ F.R.Y.D.A.Y Autonomous Copilot", font=FONT_HEADING, fill=CYAN)
    
    pts_right = [
        ("Action-Oriented ReAct Engine:", "Executes real tools: audits tracking streams, queries SCADA metrics, and outputs reports."),
        ("Grounding in Official SOPs:", "Enforces SOP-FC-SAFE-2026, SOP-CS-CONCESS-04, and SOP-REVERSE-LOG-09 via hybrid RAG."),
        ("Real-Time Telemetry Auditing:", "Audits live Fulfillment Centers (ONT8, JFK8, ORD4) and carrier tracking in seconds."),
        ("Autonomous Directives:", "Triggers freight bypass routes, suppresses defective ASINs, and resolves WISMO cases.")
    ]
    y = 210
    for title, desc in pts_right:
        d.text((690, y), f"• {title}", font=FONT_BODY_BOLD, fill=EMERALD)
        d.text((710, y + 24), desc, font=FONT_CAPTION, fill=MUTED)
        y += 75

    draw_subtitles(d, subtitle, t_norm)
    return im


def render_scene_3(t_norm: float, subtitle: str) -> Image.Image:
    """Scene 3: Architecture"""
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(im)
    draw_header(d, "End-to-End System Architecture & Technology Stack", "TECHNICAL ARCHITECTURE")

    cols = [
        ("🧠 Autonomous Agent Core", CYAN, [
            ("ReAct Architecture", "Thought → Tool Call → Observation → Directive loop."),
            ("Google Gemini 2.5", "High-speed reasoning via official google-genai SDK."),
            ("Multi-Agent Swarm", "AmazonOps, ScamShield, Research, Cleaner, Triage.")
        ]),
        ("🛠️ Telemetry & Hybrid RAG", AMAZON_ORANGE, [
            ("9 Specialized Tools", "Analyzes tracking CSVs, picker UPH, and fraud scores."),
            ("Hybrid RAG Search", "BM25 lexical + semantic vector embeddings."),
            ("Amazon SOP Repository", "Pre-seeded with safety manuals, dispatch rules, and policies.")
        ]),
        ("⚡ Real-Time Web & Cloud", EMERALD, [
            ("FastAPI + WebSockets", "Streams live thought processes and observations."),
            ("Futuristic Stark UI", "Animated Arc Reactor background & iPhone fluid physics."),
            ("24/7 Zero Cold-Start", "Render cloud + GitHub Actions automated cron pings.")
        ])
    ]

    card_w = 360
    for idx, (title, color, items) in enumerate(cols):
        x1 = 60 + idx * (card_w + 40)
        x2 = x1 + card_w
        draw_card(d, x1, 120, x2, HEIGHT - 90, border=color)
        d.text((x1 + 20, 145), title, font=FONT_SUBTITLE, fill=color)
        
        y = 210
        for it_title, it_desc in items:
            d.text((x1 + 20, y), f"• {it_title}:", font=FONT_BODY_BOLD, fill=WHITE)
            d.text((x1 + 35, y + 24), it_desc, font=FONT_CAPTION, fill=MUTED)
            y += 85

    draw_subtitles(d, subtitle, t_norm)
    return im


def render_scene_4(t_norm: float, subtitle: str) -> Image.Image:
    """Scene 4: The 9 Amazon Capabilities"""
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(im)
    draw_header(d, "The 9 Mission-Critical Amazon Operational Capabilities", "AMAZON USE CASES MATRIX")

    scenarios = [
        ("📦 1. Delivery Delays", "Audits middle/last-mile shipments, isolates carrier bottlenecks.", CYAN),
        ("🏭 2. FC Bottlenecks", "Monitors SCADA metrics, detects mechanical conveyor jams.", AMAZON_ORANGE),
        ("📞 3. Customer Support", "WISMO investigation, formulates concession via SOP-CS-CONCESS-04.", BLUE),
        ("🔄 4. Reverse Logistics", "Detects defective ASIN return rates up to 22%, vendor chargebacks.", CYAN),
        ("📊 5. Seller Analytics", "Audits FBA stockout risks (<5 days supply) and Buy Box collapse.", EMERALD),
        ("🚚 6. Supply Disruptions", "Monitors NOAA storm feeds, reroutes 42 trucks around I-80 blizzard.", AMAZON_ORANGE),
        ("💰 7. Fraud Detection", "Cross-references POD photos & claim velocity to flag empty-box rings.", ROSE),
        ("👨‍💻 8. Internal SOPs", "Hybrid RAG search over authorized Amazon manuals (E-stops, safety).", BLUE),
        ("📝 9. Daily Ops Report", "Synthesizes network KPIs, carrier OTD (88.4%), and shift handoff briefs.", EMERALD)
    ]

    card_w = 360
    card_h = 115
    for idx, (title, desc, color) in enumerate(scenarios):
        r = idx // 3
        c = idx % 3
        x1 = 60 + c * (card_w + 40)
        y1 = 120 + r * (card_h + 20)
        x2 = x1 + card_w
        y2 = y1 + card_h
        
        draw_card(d, x1, y1, x2, y2, border=color)
        d.text((x1 + 16, y1 + 14), title, font=FONT_BODY_BOLD, fill=color)
        d.text((x1 + 16, y1 + 45), desc, font=FONT_CAPTION, fill=MUTED)

    draw_subtitles(d, subtitle, t_norm)
    return im


def render_scene_5(t_norm: float, subtitle: str) -> Image.Image:
    """Scene 5: Demo 1 — Delays & Warehouse Jams"""
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(im)
    draw_header(d, "Live Operational Audit: Delivery Delays & Fulfillment Center Jams", "PILLARS 1 & 2")

    # Left: Delays
    draw_card(d, 60, 120, 620, HEIGHT - 90, border=CYAN)
    d.text((90, 145), "📦 Pillar 1: Delivery Delays Root Cause", font=FONT_SUBTITLE, fill=CYAN)
    d.text((90, 185), "Dataset: 100 Shipments Audited across AMZL, UPS & FedEx", font=FONT_CAPTION, fill=AMAZON_ORANGE)
    
    delays_info = [
        "Delayed Packages Detected: 8 Shipments (Average Delay: 17.8 Hours)",
        "Root Causes Isolated: SORT_JAM_ONT8 (3), WEATHER_STORM (2), CARRIER_OVERFLOW (2)",
        "Directive 1: Trigger AMZL Secondary Hub Bypass routing parcels through DLA4.",
        "Directive 2: Corridor Freeze Protocol: Divert ORD4 line-hauls via I-70 bypass.",
        "Directive 3: DSP Flex Injection: Transfer 250 overflow parcels to dedicated stations."
    ]
    y = 230
    for line in delays_info:
        d.text((90, y), f"• {line}", font=FONT_BODY, fill=WHITE if "Directive" in line else MUTED)
        y += 50

    # Right: Warehouse
    draw_card(d, 660, 120, WIDTH - 60, HEIGHT - 90, border=AMAZON_ORANGE)
    d.text((690, 145), "🏭 Pillar 2: Fulfillment Center Telemetry & Jams", font=FONT_SUBTITLE, fill=AMAZON_ORANGE)
    d.text((690, 185), "SCADA Telemetry: 24 Stations across ONT8, JFK8, ORD4, DFW7", font=FONT_CAPTION, fill=CYAN)

    wh_info = [
        "Active Mechanical Conveyor Jams Detected: 2 Active Incidents",
        "Incidents: ONT8 Inbound Dock 3 (Tape Machine Jam) & DFW7 AFE Sort (Sensor Fault)",
        "Critical Gridlock Alerts: 3 Stations exceeding maximum queue depths (>240 units)",
        "Directives: Dispatched RME maintenance technicians immediately with failure codes.",
        "Throughput Recovery: Flow rerouted to parallel induction lines to avoid line halts."
    ]
    y = 230
    for line in wh_info:
        d.text((690, y), f"• {line}", font=FONT_BODY, fill=WHITE if "Directive" in line else MUTED)
        y += 50

    draw_subtitles(d, subtitle, t_norm)
    return im


def render_scene_6(t_norm: float, subtitle: str) -> Image.Image:
    """Scene 6: Demo 2 — Customer Care & Reverse Logistics"""
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(im)
    draw_header(d, "Customer Concession Policy & Defective ASIN Reverse Logistics", "PILLARS 3 & 4")

    # Left: Customer Support
    draw_card(d, 60, 120, 620, HEIGHT - 90, border=BLUE)
    d.text((90, 145), "📞 Pillar 3: Customer Care & Order Investigation", font=FONT_SUBTITLE, fill=BLUE)
    d.text((90, 185), "Investigation Case: Order AMZ-1082-93821 (Delayed Transit)", font=FONT_CAPTION, fill=WHITE)
    
    cs_info = [
        "Tracking Scan: Carrier transit exception due to Midwest blizzard corridor.",
        "Policy Applied: SOP-CS-CONCESS-04 (Delayed Shipments > 12 Hours).",
        "Authorized Concession: $10.00 Prime Courtesy Credit + Free Expedited Re-order.",
        "Automated Communication: Drafted empathetic, professional customer email.",
        "Fulfillment Action: Triggered priority re-dispatch queue from secondary FC."
    ]
    y = 230
    for line in cs_info:
        d.text((90, y), f"• {line}", font=FONT_BODY, fill=WHITE if "Concession" in line or "Policy" in line else MUTED)
        y += 50

    # Right: Returns & Defective ASINs
    draw_card(d, 660, 120, WIDTH - 60, HEIGHT - 90, border=CYAN)
    d.text((690, 145), "🔄 Pillar 4: Reverse Logistics & Defective ASINs", font=FONT_SUBTITLE, fill=CYAN)
    d.text((690, 185), "Audit Standard: SOP-REVERSE-LOG-09 (Defect Threshold > 10%)", font=FONT_CAPTION, fill=WHITE)

    ret_info = [
        "Flagged Product: ASIN B0B12F98Q1 with 22.0% Return Rate (Normal < 5%).",
        "Defect Clustering: Broken glass bottles due to insufficient inner packaging cushion.",
        "Customer Sentiment: 'Arrived shattered and leaked inside box' in 84% of reviews.",
        "Autonomous Enforcement: Suppressed Buy Box immediately to prevent further shipments.",
        "Vendor Directive: Issued formal quality chargeback and packaging remediation demand."
    ]
    y = 230
    for line in ret_info:
        d.text((690, y), f"• {line}", font=FONT_BODY, fill=WHITE if "Enforcement" in line or "Flagged" in line else MUTED)
        y += 50

    draw_subtitles(d, subtitle, t_norm)
    return im


def render_scene_7(t_norm: float, subtitle: str) -> Image.Image:
    """Scene 7: Demo 3 — Supply Disruptions & Fraud"""
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(im)
    draw_header(d, "Supply Chain Weather Routing & Concession Abuse Forensics", "PILLARS 6 & 7")

    # Left: Supply Chain Disruptions
    draw_card(d, 60, 120, 620, HEIGHT - 90, border=EMERALD)
    d.text((90, 145), "🚚 Pillar 6: Supply Chain Weather Disruption Alerts", font=FONT_SUBTITLE, fill=EMERALD)
    d.text((90, 185), "Continuity Standard: SOP-SUPPLY-DISRUPT-02 (Severe Weather Bypass)", font=FONT_CAPTION, fill=WHITE)
    
    sc_info = [
        "External Feed: NOAA Severe Weather Radar detected Midwest Blizzard on I-80.",
        "Impact: 42 Line-Haul semi-trucks stalled on lanes ORD4 → JFK8 (24-36h delay).",
        "Autonomous Protocol: Executed emergency southern bypass routing via I-70 corridor.",
        "Customer Impact Mitigation: Automatically adjusted estimated delivery windows.",
        "Inventory Rebalancing: Shifted regional stock replenishment to southern distribution hubs."
    ]
    y = 230
    for line in sc_info:
        d.text((90, y), f"• {line}", font=FONT_BODY, fill=WHITE if "Autonomous" in line else MUTED)
        y += 50

    # Right: Fraud Detection
    draw_card(d, 660, 120, WIDTH - 60, HEIGHT - 90, border=ROSE)
    d.text((690, 145), "💰 Pillar 7: Trust & Safety: Concession Abuse Forensics", font=FONT_SUBTITLE, fill=ROSE)
    d.text((690, 185), "TRMS Fraud Telemetry: Claim Velocity & Delivery Geofence Verification", font=FONT_CAPTION, fill=WHITE)

    fr_info = [
        "Claim Velocity Audit: Flagged account with 6 missing-item claims in 14 days ($1,420).",
        "Proof-Of-Delivery Verification: AMZL photo POD confirms package delivered at porch.",
        "Tamper Seal Evidence: Courier scan weights match intact items leaving fulfillment center.",
        "Fraud Scoring: Calculated 94/100 risk score (Verdict: CONFIRMED_SERIAL_ABUSE).",
        "Action: Froze automated concession processing; generated forensic dossier for TRMS."
    ]
    y = 230
    for line in fr_info:
        d.text((690, y), f"• {line}", font=FONT_BODY, fill=WHITE if "Fraud Scoring" in line or "Action" in line else MUTED)
        y += 50

    draw_subtitles(d, subtitle, t_norm)
    return im


def render_scene_8(t_norm: float, subtitle: str) -> Image.Image:
    """Scene 8: UI / UX & Cloud Engineering"""
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(im)
    draw_header(d, "Futuristic Stark UI & Production Cloud Reliability", "UI / UX & DEPLOYMENT")

    # Left: Stark UI
    draw_card(d, 60, 120, 620, HEIGHT - 90, border=CYAN)
    d.text((90, 145), "⚛️ Holographic Stark Command Center", font=FONT_SUBTITLE, fill=CYAN)
    
    ui_info = [
        ("Mark LXXXV Arc Reactor:", "Animated SVG with 10 copper induction solenoid coils and counter-rotating telemetry rings."),
        ("iPhone Fluid Animations:", "iOS spring physics curves (cubic-bezier 0.32, 0.72, 0, 1) and active touch scaling."),
        ("ChatGPT-Style Sidebar:", "Recent searches persistence with glowing cyan-blue dots and user deletion rights."),
        ("1-Click Showcase Bar:", "9 scenario chips for instant demonstration with single-click execution.")
    ]
    y = 200
    for title, desc in ui_info:
        d.text((90, y), f"• {title}", font=FONT_BODY_BOLD, fill=WHITE)
        d.text((110, y + 24), desc, font=FONT_CAPTION, fill=MUTED)
        y += 65

    # Right: Cloud Deployment & Tests
    draw_card(d, 660, 120, WIDTH - 60, HEIGHT - 90, border=EMERALD)
    d.text((690, 145), "☁️ 24/7 Zero Cold-Start Deployment & 100% Tests", font=FONT_SUBTITLE, fill=EMERALD)

    dep_info = [
        ("Live Production Host:", "Hosted on Render at https://ai-agent-pr00.onrender.com with automated CI/CD."),
        ("Zero Cold-Start Pinger:", "GitHub Actions cron runs every 10 min to keep instance active 24/7 without sleep."),
        ("100% Test Pass Rate:", "47 out of 47 unit & integration tests passing across all tools and agent routes."),
        ("Full Backward Compatibility:", "Existing file organizer, research, cleaner, and ScamShield agents remain 100% intact.")
    ]
    y = 200
    for title, desc in dep_info:
        d.text((690, y), f"• {title}", font=FONT_BODY_BOLD, fill=WHITE)
        d.text((710, y + 24), desc, font=FONT_CAPTION, fill=MUTED)
        y += 65

    draw_subtitles(d, subtitle, t_norm)
    return im


def render_scene_9(t_norm: float, subtitle: str) -> Image.Image:
    """Scene 9: Conclusion & Live Access"""
    im = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    d = ImageDraw.Draw(im)

    draw_card(d, 120, 100, WIDTH - 120, HEIGHT - 120, bg=(14, 24, 56), border=CYAN, radius=20)
    
    d.text((180, 145), "⚡ EXPERIENCE F.R.Y.D.A.Y LIVE TODAY", font=FONT_BADGE, fill=AMAZON_ORANGE)
    d.text((180, 185), "F.R.Y.D.A.Y", font=FONT_TITLE, fill=CYAN)
    d.text((180, 260), "Amazon Operations Autonomous Copilot • Ready for Production", font=FONT_HEADING, fill=WHITE)

    links = [
        ("🌐 Live Deployed Application:", "https://ai-agent-pr00.onrender.com"),
        ("💻 Open-Source GitHub Repository:", "https://github.com/barnavadey616/AI-Agent"),
        ("📦 1-Click Operations Showcase:", "9 scenario chips ready for live evaluation"),
        ("🧪 Test Verification:", "100% test pass rate across 47 tests (Pytest)")
    ]
    y = 330
    for title, val in links:
        d.text((180, y), f"• {title}", font=FONT_BODY_BOLD, fill=AMAZON_ORANGE)
        d.text((200, y + 26), val, font=FONT_BODY, fill=BLUE)
        y += 60

    d.text((180, 560), "Thank you! Questions & Live Demonstration.", font=FONT_SUBTITLE, fill=EMERALD)

    draw_subtitles(d, subtitle, t_norm)
    return im


# ==============================================================================
# Main Video Generation Pipeline
# ==============================================================================

SCENES = [
    {
        "id": "scene_01",
        "renderer": render_scene_1,
        "narration": "Welcome to the presentation of F.R.Y.D.A.Y, an enterprise-grade autonomous AI copilot engineered for Amazon Global Logistics, Fulfillment Centers, and Customer Trust.",
        "subtitle": "Welcome to F.R.Y.D.A.Y: Autonomous AI Operations Copilot for Amazon"
    },
    {
        "id": "scene_02",
        "renderer": render_scene_2,
        "narration": "Traditional AI chatbots only generate text and hallucinate. In large-scale operations like Amazon, an AI agent must audit real-time telemetry, detect mechanical bottlenecks, and execute concrete operational directives.",
        "subtitle": "Why Generic AI Fails: Operations demands action, telemetry analysis, and SOP compliance"
    },
    {
        "id": "scene_03",
        "renderer": render_scene_3,
        "narration": "Our architecture is powered by a ReAct multi-agent loop with real-time WebSocket streaming, integrated with a hybrid RAG knowledge base seeded with official Amazon Standard Operating Procedures.",
        "subtitle": "System Architecture: ReAct agent loop, FastAPI WebSockets, Gemini 2.5, and Amazon SOP RAG"
    },
    {
        "id": "scene_04",
        "renderer": render_scene_4,
        "narration": "F.R.Y.D.A.Y solves nine mission-critical Amazon operational problems, from delivery delays and warehouse jams to customer concessions and supply chain weather diversions.",
        "subtitle": "The 9 Mission-Critical Capabilities: Delays, bottlenecks, concessions, returns, and fraud"
    },
    {
        "id": "scene_05",
        "renderer": render_scene_5,
        "narration": "In live logistics telemetry, the agent audits shipment tracking streams to trigger hub bypasses, and scans warehouse SCADA metrics to detect conveyor jams and dispatch maintenance teams.",
        "subtitle": "Live Telemetry: Auditing delivery delays, resolving ONT8 conveyor jams, and dispatching RME teams"
    },
    {
        "id": "scene_06",
        "renderer": render_scene_6,
        "narration": "For customer service, it evaluates tracking exceptions against policy to formulate concessions, while reverse logistics audits flag defective products and enforce vendor chargebacks.",
        "subtitle": "Customer Care & Reverse Logistics: Automated concessions and defective ASIN Buy Box suppression"
    },
    {
        "id": "scene_07",
        "renderer": render_scene_7,
        "narration": "During severe blizzards, the agent reroutes forty-two line-haul trucks around storm corridors, while trust and safety audits cross-reference delivery photos to neutralize empty-box fraud.",
        "subtitle": "Continuity & Fraud: Rerouting 42 trucks around I-80 blizzard, neutralizing concession abuse"
    },
    {
        "id": "scene_08",
        "renderer": render_scene_8,
        "narration": "The platform features an authentic Iron Man Arc Reactor interface, deployed live on Render with twenty-four-seven automated keep-alive heartbeats and forty-seven passing tests.",
        "subtitle": "Stark UI & Production Engineering: Arc Reactor HUD, 24/7 zero cold start, 100% tests passed"
    },
    {
        "id": "scene_09",
        "renderer": render_scene_9,
        "narration": "F.R.Y.D.A.Y is live, reliable, and ready for production. Try the live interactive demo at ai-agent-pr00.onrender.com. Thank you!",
        "subtitle": "Experience F.R.Y.D.A.Y live at https://ai-agent-pr00.onrender.com • Open-Source on GitHub"
    }
]


def main():
    print("==========================================================")
    print("Starting F.R.Y.D.A.Y Video Demo Generation Pipeline")
    print("==========================================================")

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    print(f"Using FFmpeg: {ffmpeg_exe}")

    scene_video_files = []

    for i, scene in enumerate(SCENES):
        scene_id = scene["id"]
        narration = scene["narration"]
        subtitle = scene["subtitle"]
        renderer = scene["renderer"]

        print(f"\n--- Processing Scene {i + 1}/{len(SCENES)}: {scene_id} ---")
        
        # 1. Synthesize audio
        audio_path = TEMP_DIR / f"{scene_id}.wav"
        duration = synthesize_speech(narration, audio_path)
        # Add 0.6s breathing padding at the end of each scene
        total_duration = duration + 0.6
        num_frames = int(total_duration * FPS)
        print(f"Audio Duration: {duration:.2f}s | Video Target: {total_duration:.2f}s ({num_frames} frames)")

        # 2. Render silent video
        silent_video_path = TEMP_DIR / f"{scene_id}_silent.mp4"
        writer = imageio.get_writer(
            str(silent_video_path),
            fps=FPS,
            codec="libx264",
            format="mp4",
            pixelformat="yuv420p",
            ffmpeg_log_level="error"
        )

        base_img = renderer(1.0, subtitle)
        for frame_idx in range(num_frames):
            t_norm = frame_idx / float(max(1, num_frames - 1))
            frame_img = base_img.copy()
            bar_w = int(WIDTH * t_norm)
            if bar_w > 0:
                d_prog = ImageDraw.Draw(frame_img)
                d_prog.line([(0, HEIGHT - 68), (bar_w, HEIGHT - 68)], fill=CYAN, width=3)
            writer.append_data(np.array(frame_img))

        writer.close()
        print(f"Silent video rendered: {silent_video_path.name}")

        # 3. Mux audio and video using FFmpeg
        muxed_scene_path = TEMP_DIR / f"{scene_id}_muxed.mp4"
        cmd_mux = [
            ffmpeg_exe,
            "-y",
            "-i", str(silent_video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(muxed_scene_path)
        ]
        res = subprocess.run(cmd_mux, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"FFmpeg muxing error in {scene_id}: {res.stderr}")
            sys.exit(1)

        print(f"Muxed video created: {muxed_scene_path.name}")
        scene_video_files.append(muxed_scene_path)

    # 4. Concatenate all scenes into final video
    print("\n--- Concatenating all scenes into final video ---")
    concat_list_path = TEMP_DIR / "concat_list.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in scene_video_files:
            f.write(f"file '{p.resolve().as_posix()}'\n")

    final_output_path = Path("FRYDAY_Project_Demo_Walkthrough.mp4")
    cmd_concat = [
        ffmpeg_exe,
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_path),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(final_output_path)
    ]
    res_concat = subprocess.run(cmd_concat, capture_output=True, text=True)
    if res_concat.returncode != 0:
        print(f"FFmpeg concat error: {res_concat.stderr}")
        sys.exit(1)

    print(f"\n[SUCCESS] Final Video Demo saved to: {final_output_path.resolve()}")
    print(f"File Size: {final_output_path.stat().st_size / (1024 * 1024):.2f} MB")

    # Copy to static directory for web playback
    static_video = Path("taskflow/server/static/FRYDAY_Project_Demo_Walkthrough.mp4")
    static_video.write_bytes(final_output_path.read_bytes())
    print(f"Web Static copy saved to: {static_video.resolve()}")

    # Copy to outputs/reports/
    reports_video = Path("outputs/reports/FRYDAY_Project_Demo_Walkthrough.mp4")
    reports_video.parent.mkdir(parents=True, exist_ok=True)
    reports_video.write_bytes(final_output_path.read_bytes())
    print(f"Reports copy saved to: {reports_video.resolve()}")


if __name__ == "__main__":
    main()
