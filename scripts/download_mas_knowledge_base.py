"""
scripts/download_mas_knowledge_base.py: Download and catalog seminal Multi-Agent Systems (MAS)
textbooks, foundational research papers, design pattern surveys, and tutorials.

Architect: Acinonyx
"""

import os
import sys
import time
import urllib.request
import urllib.error
from typing import Dict, List

PDF_DIR = "/home/acinonyx/Desktop/MAS/research/multi_agent_systems/pdfs"
KB_DIR = "/home/acinonyx/Desktop/MAS/research/multi_agent_systems/knowledge_base"
os.makedirs(PDF_DIR, exist_ok=True)
os.makedirs(KB_DIR, exist_ok=True)

TARGET_DOCUMENTS: List[Dict[str, str]] = [
    {
        "filename": "Multiagent_Systems_Algorithmic_Game_Theoretic_Shoham_LeytonBrown.pdf",
        "title": "Multiagent Systems: Algorithmic, Game-Theoretic, and Logical Foundations",
        "authors": "Yoav Shoham (Stanford) & Kevin Leyton-Brown (UBC)",
        "publisher": "Cambridge University Press (532 pages)",
        "category": "Foundational Textbook",
        "url": "https://www.masfoundations.org/mas.pdf",
        "summary": (
            "The definitive graduate-level textbook uniting distributed artificial intelligence, "
            "game theory, mechanism design, multi-agent learning, and logical theories of belief and intention."
        ),
    },
    {
        "filename": "CoALA_Cognitive_Architectures_for_Language_Agents.pdf",
        "title": "Cognitive Architectures for Language Agents (CoALA)",
        "authors": "Theodore R. Sumers, Shunyu Yao, Karthik Narasimhan, Thomas L. Griffiths (Princeton / DeepMind)",
        "publisher": "arXiv:2309.02427",
        "category": "Cognitive Architecture",
        "url": "https://arxiv.org/pdf/2309.02427",
        "summary": (
            "Proposes a landmark unified blueprint structuring language agents into Working Memory, "
            "Episodic/Semantic/Procedural Long-Term Memory, Perception, Action, and Internal Reasoning cycles."
        ),
    },
    {
        "filename": "AutoGen_Multi_Agent_Conversation_Framework.pdf",
        "title": "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation",
        "authors": "Qingyun Wu, Gagan Bansal, Jieyu Zhang, Yiran Wu, Chi Wang et al. (Microsoft Research)",
        "publisher": "arXiv:2308.08155",
        "category": "Framework & Architecture",
        "url": "https://arxiv.org/pdf/2308.08155",
        "summary": (
            "Multi-agent conversational architecture enabling customizable, conversable agents that "
            "integrate LLMs, human input, and tool execution in dynamic conversation topologies."
        ),
    },
    {
        "filename": "MetaGPT_Meta_Programming_Multi_Agent_Collaboration.pdf",
        "title": "MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework",
        "authors": "Sirui Hong, Mingchen Zhuge, Jonathan Chen, Xiawu Zheng, Chenglin Wu et al.",
        "publisher": "arXiv:2308.00352",
        "category": "Software Engineering MAS",
        "url": "https://arxiv.org/pdf/2308.00352",
        "summary": (
            "Encodes human Standard Operating Procedures (SOPs) into multi-agent workflows, utilizing "
            "structured communication interfaces (PRDs, architecture diagrams, data APIs) to reduce cascades of errors."
        ),
    },
    {
        "filename": "ChatDev_Communicative_Agents_for_Software_Development.pdf",
        "title": "Communicative Agents for Software Development",
        "authors": "Chen Qian, Wei Liu, Hongning Wang, Cheng Yang, Zhiyuan Liu, Maosong Sun et al. (Tsinghua)",
        "publisher": "arXiv:2307.07924",
        "category": "Virtual Software Enterprise",
        "url": "https://arxiv.org/pdf/2307.07924",
        "summary": (
            "Simulates a virtual software company with CEO, CPO, CTO, Programmer, and Reviewer chatting "
            "through multi-turn waterfall and agile phases (designing, coding, testing, documenting)."
        ),
    },
    {
        "filename": "LLM_Based_Multi_Agents_Survey_Progress_Challenges.pdf",
        "title": "Large Language Model based Multi-Agents: A Survey of Progress and Challenges",
        "authors": "Taicheng Guo, Xiuying Chen, Yaqi Wang, Ruidi Chang, Shichao Pei et al.",
        "publisher": "arXiv:2402.01680",
        "category": "Comprehensive Survey",
        "url": "https://arxiv.org/pdf/2402.01680",
        "summary": (
            "Exhaustive survey categorizing LLM-MAS agent profiling, communication topologies, "
            "environment interaction, collective intelligence mechanisms, and evaluation benchmarks."
        ),
    },
    {
        "filename": "LLM_Autonomous_Agents_Survey.pdf",
        "title": "A Survey on Large Language Model based Autonomous Agents",
        "authors": "Lei Wang, Chen Ma, Xueyang Feng, Zeyu Zhang, Hao Yang, Jingsen Zhang et al.",
        "publisher": "Frontiers of Computer Science / arXiv:2308.11432",
        "category": "Foundational Survey",
        "url": "https://arxiv.org/pdf/2308.11432",
        "summary": (
            "Surveys the architecture of autonomous agents: profiling, memory mechanisms, planning "
            "(feedback vs non-feedback), action execution (tool usage), and application ecosystems."
        ),
    },
    {
        "filename": "LLM_MultiAgent_Advances_Frontiers_Survey.pdf",
        "title": "A Survey on LLM-based Multi-Agent System: Recent Advances and New Frontiers in Application",
        "authors": "Haoyuan Peng, Shengjie Zhang, Yuntian Chen et al.",
        "publisher": "arXiv:2412.17481",
        "category": "Frontier Survey",
        "url": "https://arxiv.org/pdf/2412.17481",
        "summary": (
            "Analyzes latest advancements in multi-agent collaboration, game-theoretic negotiation, "
            "agent simulation in open environments, and self-improving agent swarms."
        ),
    },
]


def download_file(doc: Dict[str, str]) -> bool:
    dest_path = os.path.join(PDF_DIR, doc["filename"])
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 100000:
        print(f"✓ Already present: {doc['filename']} ({os.path.getsize(dest_path):,} bytes)")
        return True

    print(f"⬇ Downloading: {doc['title']}...")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }
    req = urllib.request.Request(doc["url"], headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            content = response.read()

        if len(content) < 1000:
            print(f"✗ Failed (Too small: {len(content)} bytes): {doc['filename']}")
            return False

        with open(dest_path, "wb") as f:
            f.write(content)

        print(f"✓ Success: {doc['filename']} ({len(content):,} bytes, Magic: {content[:4]})")
        return True
    except Exception as exc:
        print(f"✗ Error downloading {doc['filename']}: {exc}")
        return False


def build_knowledge_base():
    """Generate structured markdown knowledge base and index for the collected literature."""
    index_md = os.path.join("/home/acinonyx/Desktop/MAS/research/multi_agent_systems", "README.md")
    content = [
        "# Multi-Agent Systems (MAS) Research & Design Knowledge Base",
        "",
        "This repository contains curated textbooks, foundational academic papers, architectural surveys,",
        "and design patterns for building autonomous multi-agent systems and enterprise swarm frameworks.",
        "",
        "## 📚 Curated PDF Library",
        "",
        "| Document | Category | Authors / Source | Status |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for doc in TARGET_DOCUMENTS:
        file_path = os.path.join(PDF_DIR, doc["filename"])
        size_str = f"{os.path.getsize(file_path) / (1024*1024):.2f} MB" if os.path.exists(file_path) else "Pending"
        status_icon = "✅ Downloaded" if os.path.exists(file_path) and os.path.getsize(file_path) > 100000 else "⏳ Failed"
        content.append(
            f"| **[{doc['title']}](pdfs/{doc['filename']})**<br>*{doc['summary']}* | `{doc['category']}` | {doc['authors']} ({doc['publisher']}) | {status_icon} ({size_str}) |"
        )

    content.extend([
        "",
        "---",
        "",
        "## 🏛️ Core Multi-Agent Architectural Patterns",
        "",
        "### 1. Classical Foundations (Shoham & Leyton-Brown)",
        "- **Game Theory & Mechanism Design**: Nash equilibria, Pareto optimality, auction mechanisms (Vickrey-Clarke-Groves), and voting protocols.",
        "- **Logical Frameworks**: BDI (Belief-Desire-Intention) architectures, epistemic logics, and distributed consensus.",
        "- **Communication & Interaction**: Speech act theory (KQML, FIPA-ACL), contract net protocols (CNP), and blackboard systems.",
        "",
        "### 2. Cognitive Architectures for Language Agents (CoALA)",
        "- **Working Memory**: Dynamic scratchpad maintaining immediate context, active goals, and perception inputs.",
        "- **Long-Term Memory Hierarchy**:",
        "  - *Episodic Memory*: Past trajectories, experiences, and reflections for few-shot in-context learning.",
        "  - *Semantic Memory*: Grounded domain knowledge, vector embeddings, and knowledge graph facts.",
        "  - *Procedural Memory*: System prompts, available tool schemas, and operational workflows.",
        "- **Action Space**: Internal actions (reasoning, reflection, memory retrieval) vs. External actions (MCP tool execution, environment changes, inter-agent messaging).",
        "",
        "### 3. Multi-Agent Conversation Topologies (AutoGen & MetaGPT)",
        "- **Hierarchical / Supervisor-Worker**: Centralized orchestrator decomposing complex RFPs into DAG sub-tasks dispatched to specialized agents.",
        "- **Peer-to-Peer / Joint Collaboration**: Communicative agents sharing a typed event bus (e.g., Architect -> Engineer -> QA Critic -> Red Team).",
        "- **Standard Operating Procedures (SOPs)**: Enforcing strict artifacts (PRD, OpenAPI specs, test reports) at handover gates to prevent error cascade.",
        "- **Reflexion & Critique Loops**: Iterative self-correction with bounded rounds ($K \\le 3$) and independent verification before state commits.",
        "",
        "---",
        "*Curated for Acinonyx Labs Autonomous Agentic Swarm Engineering.*",
    ])

    with open(index_md, "w", encoding="utf-8") as f:
        f.write("\n".join(content))

    print(f"\n✓ Generated Knowledge Base Index: {index_md}")


def main():
    print("==================================================================")
    print("   🐆 ACINONYX LABS: MULTI-AGENT SYSTEMS RESEARCH REPOSITORY     ")
    print("==================================================================\n")

    success_count = 0
    for doc in TARGET_DOCUMENTS:
        if download_file(doc):
            success_count += 1
        time.sleep(1.0)  # Courtesy delay between arXiv queries

    print(f"\n[DOWNLOAD COMPLETE]: {success_count}/{len(TARGET_DOCUMENTS)} documents verified.")
    build_knowledge_base()


if __name__ == "__main__":
    main()
