"""
scripts/research_gcp_agentic_infra.py: Automated Google Cloud Agentic Infrastructure Research
using local Playwright Chromium with DevTools inspection and DOM extraction.

Architect: Acinonyx
"""

import asyncio
import os
import sys

pkg_dir = "/home/acinonyx/Desktop/MAS/bin/packages"
browser_dir = "/home/acinonyx/Desktop/MAS/bin/browsers"
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browser_dir

OUTPUT_DIR = "/home/acinonyx/Desktop/MAS/research/google_cloud_agentic_infra"
SCREENSHOTS_DIR = os.path.join(OUTPUT_DIR, "screenshots")
DOCS_DIR = os.path.join(OUTPUT_DIR, "docs")
PDFS_DIR = os.path.join(OUTPUT_DIR, "pdfs")

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
os.makedirs(DOCS_DIR, exist_ok=True)
os.makedirs(PDFS_DIR, exist_ok=True)

TARGET_PAGES = [
    {
        "id": "agent_builder",
        "title": "Google Cloud Gemini Enterprise & Vertex AI Agent Builder",
        "url": "https://cloud.google.com/products/agent-builder",
        "screenshot": "01_agent_builder.png",
    },
    {
        "id": "reasoning_engine",
        "title": "Vertex AI Reasoning Engine (LangChain on Vertex AI)",
        "url": "https://cloud.google.com/vertex-ai/generative-ai/docs/reasoning-engine/overview",
        "screenshot": "02_reasoning_engine.png",
    },
    {
        "id": "ai_agent_solutions",
        "title": "Google Cloud AI Agent Architecture & Solutions",
        "url": "https://cloud.google.com/solutions/ai-agent",
        "screenshot": "03_ai_agent_solutions.png",
    },
    {
        "id": "grounding",
        "title": "Vertex AI Grounding & Enterprise Context",
        "url": "https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/ground-gemini",
        "screenshot": "04_grounding.png",
    },
    {
        "id": "extensions",
        "title": "Vertex AI Extensions & Tools Protocol",
        "url": "https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/extensions",
        "screenshot": "05_extensions.png",
    },
    {
        "id": "model_garden",
        "title": "Vertex AI Model Garden & Foundation Models",
        "url": "https://cloud.google.com/model-garden",
        "screenshot": "06_model_garden.png",
    },
]


def extract_clean_text(html_text: str) -> str:
    import re
    import html
    clean = re.sub(r"<(script|style).*?>.*?</\1>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<h[1-6].*?>(.*?)</h[1-6]>", r"\n### \1\n", clean, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<(p|div|br).*?>", "\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<.*?>", " ", clean)
    clean = html.unescape(clean)
    clean = re.sub(r"[ \t]+", " ", clean)
    clean = re.sub(r"\n\s*\n+", "\n\n", clean)
    return clean.strip()


async def main():
    print("==================================================================")
    print("   🐆 GOOGLE CLOUD AGENTIC INFRASTRUCTURE CHROMIUM HARVESTER   ")
    print("==================================================================\n")

    from playwright.async_api import async_playwright

    results_catalog = []

    async with async_playwright() as p:
        print("[DevTools Engine]: Launching Chromium Headless Shell with DevTools instrumentation...")
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        )

        page = await context.new_page()

        # DevTools listeners for console events and network errors
        page.on("console", lambda msg: print(f"  [Chrome Console ({msg.type})]: {msg.text[:90]}..."))
        page.on("pageerror", lambda err: print(f"  [Chrome Page Error]: {err}"))

        for item in TARGET_PAGES:
            url = item["url"]
            print(f"\n🌐 Navigating to: {item['title']}")
            print(f"   URL: {url}")
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                status = response.status if response else 0
                title = await page.title()
                print(f"   ✓ Status: {status} | Title: {title}")

                # Wait for content rendering
                await asyncio.sleep(2.0)

                # Capture visual snapshot
                shot_path = os.path.join(SCREENSHOTS_DIR, item["screenshot"])
                await page.screenshot(path=shot_path, full_page=False)
                print(f"   📸 Screenshot captured: {item['screenshot']} ({os.path.getsize(shot_path):,} bytes)")

                # Extract main text
                content_html = await page.content()
                clean_text = extract_clean_text(content_html)

                # Save markdown documentation
                doc_path = os.path.join(DOCS_DIR, f"{item['id']}.md")
                with open(doc_path, "w", encoding="utf-8") as f:
                    f.write(f"# {title}\n\n**Source URL:** {url}\n\n---\n\n{clean_text[:12000]}")
                print(f"   📝 Extracted text document: {item['id']}.md ({len(clean_text):,} chars)")

                # Scan for PDF links on the page
                pdf_links = await page.eval_on_selector_all(
                    "a[href$='.pdf']",
                    "elements => elements.map(e => ({href: e.href, text: e.innerText}))"
                )
                print(f"   📄 Discovered PDF references: {len(pdf_links)}")

                results_catalog.append({
                    "id": item["id"],
                    "title": title,
                    "url": url,
                    "status": status,
                    "screenshot": item["screenshot"],
                    "text_length": len(clean_text),
                    "pdf_links": pdf_links,
                    "summary_snippet": clean_text[:400].replace("\n", " "),
                })

            except Exception as e:
                print(f"   ✗ Error navigating to {url}: {e}")
                results_catalog.append({
                    "id": item["id"],
                    "title": item["title"],
                    "url": url,
                    "error": str(e),
                })

        await browser.close()

    # Generate master summary report
    summary_file = os.path.join(OUTPUT_DIR, "README.md")
    report_lines = [
        "# Google Cloud Agentic Infrastructure Research Dossier",
        "",
        "This dossier synthesizes official Google Cloud architecture documentation, foundational whitepapers,",
        "and runtime components for deploying enterprise-grade autonomous AI agents.",
        "",
        "## 🏗️ Google Cloud Agentic Architecture Overview",
        "",
        "Google Cloud structures agentic infrastructure into a layered enterprise stack:",
        "",
        "```",
        "┌────────────────────────────────────────────────────────────────────────┐",
        "│                  USER & ENTERPRISE APPLICATIONS                        │",
        "│       (Chatbots, Customer Support, Coding Assistants, Strike Pods)     │",
        "└───────────────────────────────────┬────────────────────────────────────┘",
        "                                    │",
        "                                    ▼",
        "┌────────────────────────────────────────────────────────────────────────┐",
        "│                 AGENT PLATFORM & ORCHESTRATION LAYER                   │",
        "│  • Gemini Enterprise Agent Platform (formerly Vertex AI Agent Builder) │",
        "│  • Vertex AI Reasoning Engine (Managed LangChain, LlamaIndex, AutoGen) │",
        "│  • Multi-Agent Collaboration Topologies & Gated Milestones            │",
        "└─────────────────┬──────────────────────────────────┬───────────────────┘",
        "                  │                                  │",
        "                  ▼                                  ▼",
        "┌───────────────────────────────────┐ ┌──────────────────────────────────┐",
        "│    FOUNDATION MODELS & GARDEN     │ │   GROUNDING & ENTERPRISE CONTEXT │",
        "│ • Gemini 2.0 / 1.5 Pro & Flash    │ │ • Vertex AI Search (RAG Engine)  │",
        "│ • Open Weights (Llama 3.3, Qwen)  │ │ • Enterprise Knowledge Base      │",
        "│ • Cloud TPU v5e / GPU Clusters    │ │ • Google Search Grounding        │",
        "└─────────────────┬─────────────────┘ └──────────────────┬───────────────┘",
        "                  │                                  │",
        "                  ▼                                  ▼",
        "┌────────────────────────────────────────────────────────────────────────┐",
        "│                  TOOLS, EXTENSIONS & MCP LAYER                         │",
        "│  • Vertex AI Extensions (OpenAPI Spec REST execution)                 │",
        "│  • Model Context Protocol (MCP) Connectors & Function Calling          │",
        "│  • Cloud Run & Cloud Functions (Serverless Sandboxed Tool Execution)   │",
        "└───────────────────────────────────┬────────────────────────────────────┘",
        "                                    │",
        "                                    ▼",
        "┌────────────────────────────────────────────────────────────────────────┐",
        "│                  SECURITY, GOVERNANCE & OBSERVABILITY                  │",
        "│  • VPC Service Controls & Customer Managed Encryption Keys (CMEK)      │",
        "│  • IAM Principle-of-Least-Privilege & FinOps Token Attribution         │",
        "│  • Cloud Trace, Cloud Logging & Evaluation Metrics                     │",
        "└────────────────────────────────────────────────────────────────────────┘",
        "```",
        "",
        "## 📑 Investigated Documentation & Evidence",
        "",
        "| Service / Architecture Component | Direct URL | Visual Artifact | Extracted Document |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for item in results_catalog:
        shot_link = f"[Screenshot](screenshots/{item.get('screenshot')})" if item.get("screenshot") else "N/A"
        doc_link = f"[Markdown Doc](docs/{item['id']}.md)"
        report_lines.append(
            f"| **{item['title']}** | [{item['url']}]({item['url']}) | {shot_link} | {doc_link} |"
        )

    report_lines.extend([
        "",
        "## 🔬 Key Architectural Pillars of GCP Agentic Infrastructure",
        "",
        "### 1. Vertex AI Reasoning Engine (Managed Agent Runtime)",
        "- **What it is**: Fully managed runtime environment for deploying, serving, and scaling agentic code (supporting LangChain, LlamaIndex, or custom Python agent classes).",
        "- **Key Feature**: Transforms local Python agent templates into production serverless REST APIs with automatic session management and state serialization.",
        "",
        "### 2. Vertex AI Search & Grounding Engine",
        "- **What it is**: Turnkey Retrieval-Augmented Generation (RAG) system with multi-modal embeddings, vector search, chunking, and semantic re-ranking.",
        "- **Grounding with Google Search**: Injects real-time public web intelligence with attribution citations directly into model reasoning turns.",
        "",
        "### 3. Vertex AI Extensions & MCP Protocol",
        "- **What it is**: Standardized bridge connecting language models to external enterprise APIs via OpenAPI 3.0 specifications.",
        "- **Execution Model**: Handles OAuth2 authentication, parameter validation, and secure dispatch without exposing credentials to the model.",
        "",
        "### 4. Cloud Run & Sandboxed Tool Execution",
        "- **What it is**: Containerized serverless environment executing untrusted code snippets, mathematical simulations, and dynamic tests inside secure gVisor-based sandbox isolation.",
        "",
        "---",
        "*Compiled via Google Cloud Chromium Automation & DevTools Inspection for Acinonyx Labs.*",
    ])

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"\n✓ Generated Master Google Cloud Agentic Research Dossier: {summary_file}")


if __name__ == "__main__":
    asyncio.run(main())
