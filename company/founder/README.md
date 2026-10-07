# Mpho Mashile — Profile & Curriculum Vitae

> **Cloud Data Analyst & Agentic Systems Architect**  
> Location: Johannesburg, South Africa  
> Email: [mphoset@gmail.com](mailto:mphoset@gmail.com) | Phone: +27 78 05 05 277  
> LinkedIn: [linkedin.com/in/mpho-mashile-04ab896a](https://www.linkedin.com/in/mpho-mashile-04ab896a/)  
> Certifications: [credly.com/users/mpho-mashile](https://www.credly.com/users/mpho-mashile)  

**Attached Document:** [mpho_mashile_cv.pdf](mpho_mashile_cv.pdf)

---

## 🧭 Career Summary

A seasoned Cloud Data Analyst with over a decade of success designing and implementing data strategies that drive business growth. Expert in leveraging modern cloud technologies (Google Cloud Platform, BigQuery) and enterprise BI tools (Power BI, Looker Studio) to build automated ETL pipelines, develop impactful data models, and deliver actionable insights. A natural mentor passionate about developing analytics talent and advancing into scalable data architecture and autonomous multi-agent systems.

---

## 🛠️ Technical Skills & Competencies

| Domain | Technologies & Platforms | Proficiency |
|---|---|---|
| **Cloud & Data Platforms** | Google Cloud Platform (GCP), Microsoft Azure, AWS | Proficient |
| | BigQuery, SQL Server, SAP HANA | Expert |
| | SAS Platform Administration | Proficient |
| **Programming & Query Languages** | SQL (GoogleSQL, T-SQL, PL/SQL) | Expert |
| | DAX & Power Query | Proficient |
| | SAS (including Macro Coding) | Proficient |
| | Python (Automation, Data Engineering, Agentic Runtime) | Active / Advanced |
| **BI & Data Visualization** | Power BI | Expert |
| | Looker Studio | Proficient |
| | SAS Visual Analytics (VA) | Proficient |

---

## 💼 Professional Experience

### **Cloud Data Analyst** | *Harambee Youth Employment Accelerator*
*Jun 2024 – Present*
* Leverage Google Cloud Platform (GCP) and BigQuery to perform large-scale data analysis and engineering.
* Build and automate cloud-based ETL pipelines to ensure efficient, reliable data flow for downstream analytics.
* Design, develop, and maintain interactive Power BI dashboards to deliver actionable insights for executive business stakeholders.

### **Senior Data Analyst** | *RedM Professional Services*
*Apr 2023 – Jun 2024*
* Acted as primary data advisor for senior business leaders, translating strategic objectives into technical requirements for new data services and ensuring alignment throughout project lifecycles.
* Developed comprehensive data strategies and guided business leaders on requirements for modern data platforms.
* Oversaw end-to-end data flows from various sources and contributed to maintenance of data platforms and storage systems.
* Guided and mentored junior analysts, delegating tasks and fostering their skill development.

### **BI Data Analyst & Data Engineer** | *Nedbank*
*Jun 2019 – Mar 2023*
* Utilized SQL and data visualization tools to uncover trends, identify behavioral patterns, and inform product strategy.
* Designed and built robust data pipelines consolidating data from disparate legacy systems into a single source of truth that powered new banking product strategies.
* Automated ETL processes, enhancing efficiency and ensuring data integrity through rigorous cleansing and validation.
* Prepared and authored key regulatory reports for the Banking Association South Africa (BASA) on non-interest revenue.

### **Data Analyst** | *JD Group*
*Oct 2015 – Jun 2019*
* Automated multiple reporting processes, significantly reducing manual effort and turnaround latency.
* Tracked and analyzed complex retail datasets to identify commercial trends and process improvement opportunities.
* Collaborated closely with management to prioritize business needs and deliver data-driven insights.

### **Application Support** | *EOH*
*Sep 2014 – Sep 2015*
* Provided technical systems support, managed ticketed resolution workflows, and delivered systems training to internal teams.
* Developed business reports based on stakeholder requirements and supported nightly system batch runs.

---

## 🎓 Education & Certifications

* **Bachelor of Commerce in Information and Technology Management** (In Progress)  
  *MANCOSA* | *Jan 2024 – Dec 2026*
* **Google Cloud Certified: Professional Agentic Architect** (In Progress)  
  *Google Cloud Certifications* | *Path 4525 (Understand Google Cloud Agents)*
* **SAS Platform Administration**  
  *SAS Institute* | *Apr 2014*
* **Matriculation (with University Endorsement)**  
  *Makgoka High School* | *Dec 2006*

---

## 🔬 Professional Interests & Research Focus

* **Autonomous Agentic Systems & MAS:** Engineering multi-agent runtimes, Model Context Protocol (MCP) integrations, anti-sycophantic debate architectures, and CoALA/ReAct cognitive loops (*Project ACINONYX*).
* **Python Engineering:** Advanced automation, data manipulation pipelines, and agent orchestration.
* **Scalable Data Architecture:** Cloud-native enterprise lakehouses, BigQuery performance tuning, and Vertex AI Reasoning Engine.
* **Data Governance & Quality:** DAMA Body of Knowledge (DMBoK) framework and enterprise data stewardship.

---

## 🗄️ Cognitive Communication Vault & Linguistic Tracker

The runtime workspace stores the local SQL telemetry database that captures all interactions, user vocabulary, comprehension depth, and engagement metrics:

* **Database File:** [`comms_vault.db`](../../workspace/data/comms_vault.db) (SQLite WAL-mode database with FTS5 search)
* **CLI Tool:** [`comms_tracker.py`](../../scripts/comms_tracker.py)
* **Runtime Core:** [`mas.memory.CommsVault`](../../mas/memory/comms_vault.py)

### Key Schema Tables & Views:
1. `messages`: Full-fidelity user prompts, clean text, word counts, and estimated tokens.
2. `user_vocabulary`: Every unique word and technical term used by Mpho, occurrence frequency, category, and sample context.
3. `user_phrases`: Bigram and trigram patterns capturing signature conversational cadence.
4. `understanding_milestones`: Progression of topics tracked by depth (*Inquiry*, *Synthesis*, *Strategy*, *Execution*).
5. `daily_engagement` / `v_daily_activity`: Daily message counts, words written, and engagement activity.
6. `messages_fts`: FTS5 index for instant semantic retrieval across all past chats.

### Quick Commands:
```bash
# Sync latest chats from Antigravity transcripts
python3 scripts/comms_tracker.py sync

# View personal vocabulary and understanding scorecard
python3 scripts/comms_tracker.py profile

# View daily engagement activity
python3 scripts/comms_tracker.py activity

# Search past discussions
python3 scripts/comms_tracker.py search "swarm"
```
