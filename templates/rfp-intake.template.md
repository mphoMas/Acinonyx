# Acinonyx Client Engagement Brief & Scope Jail Specification

## 1. Client & Engagement Metadata
* **Client Organization:** [Enterprise Client Name]
* **Engagement Lead (ACG):** `client_director` / [Human Consultant Lead]
* **Technical Lead (ACG):** `chief_architect` / `data_engineer`
* **Engagement Date:** YYYY-MM-DD
* **Engagement Mode:** [Staged Assessment | Pilot Prototype | Full Production Deployment]
* **Contract Reference:** SOW-[YYYY-NNNN]

---

## 2. Executive Problem Statement
*Describe the client's current architectural crisis, data bottleneck, or AI scaling challenge in concrete, objective terms.*

---

## 3. Measurable Business Objectives & Target KPIs
| Objective | Current Baseline Metric | Target Success Metric | Measurement Timeline |
|---|---|---|---|
| E.g., BigQuery Query Latency | 45.0 seconds | $\le 2.0$ seconds | 30 days post-cutover |
| E.g., Daily ETL Pipeline Failures | 4 failures / week | 0 failures / month | Immediate on launch |
| E.g., Report Generation Latency | 3 business days | Real-time automated | End of Sprint 2 |

---

## 4. The Non-Negotiable "Scope Jail" (In-Scope vs. Out-of-Scope)

### ✅ Explicitly IN-SCOPE (Commitments)
1. [Deliverable 1: e.g., Migration of 15 legacy SQL Server stored procedures into dbt BigQuery models]
2. [Deliverable 2: e.g., Implementation of 3 Power BI executive dashboards on Gold marts]
3. [Deliverable 3: e.g., Deployment of ephemeral PR CI/CD dataset testing in GitHub Actions]

### 🚫 Strictly OUT-OF-SCOPE (Exclusions)
*To prevent scope creep and protect the squad's delivery velocity, the following items are strictly excluded from this engagement:*
1. [Exclusion 1: e.g., Integration with client legacy SAP ERP on-premise transactional database]
2. [Exclusion 2: e.g., Real-time Kafka streaming ingestion (batch ingestion via Cloud Storage only)]
3. [Exclusion 3: e.g., Custom mobile application development or frontend UI redesign]

---

## 5. Security, Data Boundaries & Compliance
* **Data Sovereignty:** [Client VPC / GCP Region e.g., `europe-west1` / `africa-south1`]
* **PII & Masking:** [Mandatory pseudonymization of customer IDs before landing in staging]
* **Access Control:** [IAM Least-Privilege service accounts; zero personal user credentials]
* **Auditability:** [All transactions logged to append-only JSONL audit trail]

---

## 6. Target Delivery Cadence (Shape Up Appetite)
* **Appetite Allocated:** [2-Week Spike | 6-Week Full Cycle]
* **Target Delivery Date:** YYYY-MM-DD
* **Dual-Run UAT Reconciliation Window:** Days [X] to [Y]
* **SRE Handover & Training:** Days [Y] to [Z]

---

## 7. Sign-off & Commercial Authorization
* **Client Authorized Signatory:** _______________________ Date: ______________
* **Acinonyx Client Director:** _______________________ Date: ______________
