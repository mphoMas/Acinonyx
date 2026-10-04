# Single-Agent AI System with ADK and Cloud Run

**Source URL:** https://docs.cloud.google.com/architecture/single-agent-ai-system-adk-cloud-run

---

Single-agent AI system using ADK and Cloud Run  |  Cloud Architecture Center  |  Google Cloud Documentation 

 Skip to main content

 <tab class="devsite-dropdown
 devsite-dropdown-full
 devsite-active
 devsite-clickable
 ">

 Documentation

 close 

 <div class="devsite-tabs-dropdown-column
 ">

 <ul class="devsite-tabs-dropdown-section
 ">

 Get Started 

 <ul class="devsite-tabs-dropdown-section
 ">

 Get Started with Google Cloud

 Product List

 Cloud Customer Care

 <div class="devsite-tabs-dropdown-column
 ">

 <ul class="devsite-tabs-dropdown-section
 ">

 Featured Products 

 <ul class="devsite-tabs-dropdown-section
 ">

 Agent Platform

 Apigee API Management

 BigQuery

 Compute Engine

 Cloud CDN

 Cloud Run

 Cloud Storage

 Cloud SQL

 Gemini Enterprise

 Google Kubernetes Engine

 Looker

 <div class="devsite-tabs-dropdown-column
 ">

 <ul class="devsite-tabs-dropdown-section
 ">

 Cross-product Tools 

 <ul class="devsite-tabs-dropdown-section
 ">

 Access and resources management

 Costs and usage management

 Infrastructure as code

 SDK, languages, frameworks, and tools

 <div class="devsite-tabs-dropdown-column
 ">

 <ul class="devsite-tabs-dropdown-section
 ">

 Technology Areas 

 <ul class="devsite-tabs-dropdown-section
 ">

 AI and ML

 Application development

 Application hosting

 Compute

 Data analytics and pipelines

 Databases

 Distributed, hybrid, and multicloud

 Industry solutions

 Migration

 Networking

 Observability and monitoring

 Security

 Storage

 More 

 / 

 Console

 English 

 Deutsch 

 Español 

 Español – América Latina 

 Français 

 Indonesia 

 Italiano 

 Português 

 Português – Brasil 

 עברית 

 中文 – 简体 

 中文 – 繁體 

 日本語 

 한국어 

 Sign in

 <div class="devsite-collapsible-section

 devsite-header-no-lower-tabs
 " style="transform: translate3d(0px, 0px, 0px);">

 <li class="devsite-breadcrumb-item
 ">

 Documentation

 <li class="devsite-breadcrumb-item
 ">

 Cloud Architecture Center

 <a href="//console.cloud.google.com/freetrial" class="cloud-free-trial-button button button-primary
 " referrerpolicy="no-referrer-when-downgrade" track-name="gcpCta" track-metadata-position="nav" track-type="freeTrial" track-metadata-eventdetail="nav">Start free 

 Documentation

 <ul class="devsite-nav-responsive-tabs devsite-nav-has-menu
 ">

 More

 Console

 < Architecture Center home 

 What's new 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Fundamentals 
 Content overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Well-Architected Framework 
 Overview What's new <li class="devsite-nav-item
 devsite-nav-heading">

 Pillars 
 <li class="devsite-nav-item
 devsite-nav-expandable">

 Operational excellence 
 Overview Ensure operational readiness and performance using CloudOps Manage incidents and problems Manage and optimize cloud resources Automate and manage change Continuously improve and innovate View on one page <li class="devsite-nav-item
 devsite-nav-expandable">

 Security, privacy, and compliance 
 Overview Implement security by design Implement zero trust Implement shift-left security Implement preemptive cyber defense Use AI securely and responsibly Use AI for security Meet regulatory, compliance, and privacy needs Shared responsibility and shared fate View on one page <li class="devsite-nav-item
 devsite-nav-expandable">

 Reliability 
 Overview Define reliability based on user-experience goals Set realistic targets for reliability Build high availability through redundancy Take advantage of horizontal scalability Detect potential failures by using observability Design for graceful degradation Perform testing for recovery from failures Perform testing for recovery from data loss Conduct thorough postmortems View on one page <li class="devsite-nav-item
 devsite-nav-expandable">

 Cost optimization 
 Overview Align spending with business value Foster a culture of cost awareness Optimize resource usage Optimize continuously View on one page <li class="devsite-nav-item
 devsite-nav-expandable">

 Performance optimization 
 Overview Plan resource allocation Take advantage of elasticity Promote modular design Continuously monitor and improve performance View on one page <li class="devsite-nav-item
 devsite-nav-expandable">

 Sustainability 
 Overview Use low-carbon regions Optimize AI and ML workloads Optimize resource usage Develop energy-efficient software Optimize data and storage Continuously measure and improve Promote a culture of sustainability Align with industry guidelines View on one page View all the pillars on one page <li class="devsite-nav-item
 devsite-nav-heading">

 Cross-pillar perspectives 
 <li class="devsite-nav-item
 devsite-nav-expandable">

 AI and ML 
 Overview Operational excellence Security Reliability Cost optimization Performance optimization View on one page <li class="devsite-nav-item
 devsite-nav-expandable">

 Financial services (FS) 
 Overview Operational excellence Security Reliability Cost optimization Performance optimization View on one page <li class="devsite-nav-item
 devsite-nav-expandable">

 Deployment archetypes 
 Overview Zonal Regional Multi-regional Global Hybrid Multicloud Comparative analysis What's next <li class="devsite-nav-item
 devsite-nav-expandable">

 Reference architectures 
 Single-zone deployment on Compute Engine Regional deployment on Compute Engine Multi-regional deployment on Compute Engine Global deployment on Compute Engine and Spanner <li class="devsite-nav-item
 devsite-nav-expandable">

 Landing zone design 
 Landing zones overview Decide identity onboarding Decide resource hierarchy <li class="devsite-nav-item
 devsite-nav-expandable">

 Network design 
 Decide network design Implement network design Decide security <li class="devsite-nav-item
 devsite-nav-expandable">

 Enterprise foundations blueprint 
 Overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Architecture 
 Authentication and authorization Organization structure Networking Detective controls Preventative controls Deployment methodology Operations best practices Deploy the blueprint 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 AI and machine learning 
 Content overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Agentic AI 
 Overview Choose agentic architecture components Choose an agent design pattern Multi-agent AI system Multi-agent private networking patterns Multi-tenant agentic AI system Single-agent AI system using ADK and Cloud Run <li class="devsite-nav-item
 devsite-nav-expandable">

 Use cases 
 Administer interactive learning Automate data science workflows Build a cross-cloud open data lakehouse Build a trusted agentic system with Google Maps Platform Classify multimodal data Implement agentic analytics for distributed data Enable live bidirectional multimodal streaming Multimodal GraphRAG resource orchestration Orchestrate access to disparate systems Orchestrate security operations workflows <li class="devsite-nav-item
 devsite-nav-expandable">

 Generative AI 
 Overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Generative AI with RAG 
 Overview Private connectivity for RAG-capable generative AI applications RAG infrastructure using Gemini Enterprise and Agent Platform RAG infrastructure using Agent Platform and Vector Search RAG infrastructure using Agent Platform and AlloyDB RAG infrastructure using GKE and Cloud SQL GraphRAG infrastructure using Agent Platform and Spanner Graph Harness CI/CD pipeline for RAG applications Deploy an enterprise generative AI and ML model Deploy and operate generative AI applications Networking for AI inference model serving on all backends Networking for AI inference model serving on GKE <li class="devsite-nav-item
 devsite-nav-expandable">

 Use cases 
 Automate utilization-review of health insurance claims Generate personalized marketing campaigns Generate personalized product recommendations Generate podcasts from audio Generate solutions for customer support questions <li class="devsite-nav-item
 devsite-nav-expandable">

 ML applications and operations 
 Overview Best practices for implementing ML on Google Cloud Guidelines for high-quality, predictive ML solutions MLOps using TensorFlow Extended, Agent Platform Pipelines, and Cloud Build MLOps: Continuous delivery and automation pipelines in machine learning <li class="devsite-nav-item
 devsite-nav-expandable">

 Build an ML vision analytics solution with Dataflow and Cloud Vision API 
 Reference architecture Deploy the architecture Confidential computing for data analytics and AI Cross-silo and cross-device federated learning Implement two-tower retrieval with large-scale candidate generation Model development and data labeling with Labelbox C3 AI architecture <li class="devsite-nav-item
 devsite-nav-expandable">

 AI and ML infrastructure 
 Optimize AI and ML workloads with Cloud Storage FUSE Optimize AI and ML workloads with Managed Lustre 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Application development 
 Content overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Development approaches and styles 
 Patterns for scalable and resilient apps <li class="devsite-nav-item
 devsite-nav-expandable">

 Development platform management 
 <li class="devsite-nav-item
 devsite-nav-expandable">

 Deploy an enterprise developer platform 
 Overview Architecture Developer platform controls Service architecture Logging and monitoring Operations Costs and attributions Deployment methodology Cymbal Bank example Mapping BeyondProd principles Deploy the blueprint Best practices for cost-optimized Kubernetes applications on GKE <li class="devsite-nav-item
 devsite-nav-expandable">

 Expose service mesh applications through GKE Gateway 
 Reference architecture Deploy the architecture <li class="devsite-nav-item
 devsite-nav-expandable">

 Build globally distributed applications using GKE Gateway and Cloud Service Mesh 
 Reference architecture Deploy the architecture Patterns and practices for identity and access governance on Google Cloud Resource management with ServiceNow Select a managed container runtime environment <li class="devsite-nav-item
 devsite-nav-expandable">

 DevOps and development lifecycle 
 Architecture decision records overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Develop and deliver apps with a deployment pipeline 
 Reference architecture Deploy the architecture DevOps Research and Assessment (DORA) capabilities <li class="devsite-nav-item
 devsite-nav-expandable">

 Application architectures 
 <li class="devsite-nav-item
 devsite-nav-expandable">

 Apache Guacamole on GKE and Cloud SQL 
 Reference architecture Deploy the architecture <li class="devsite-nav-item
 devsite-nav-expandable">

 Chrome Remote Desktop on Compute Engine 
 Set up for Linux Set up for Windows <li class="devsite-nav-item
 devsite-nav-expandable">

 Connected device architectures on Google Cloud 
 Overview Standalone MQTT broker IoT platform product Device to Pub/Sub connection to Google Cloud Best practices for running an IoT backend Best practices for automatically provisioning and configuring edge and bare metal systems and servers <li class="devsite-nav-item
 devsite-nav-expandable">

 Manage and scale networking for Windows applications that run on managed Kubernetes 
 Reference architecture Deploy the architecture Website hosting 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Big data and analytics 
 Content overview <li class="devsite-nav-item
 devsite-nav-expandable">

 End-to-end architectures 
 Import data into a secured BigQuery data warehouse <li class="devsite-nav-item
 devsite-nav-expandable">

 Data mesh on Google Cloud 
 Architecture and functions in a data mesh Design a self-service data platform for a data mesh Build data products in a data mesh Discover and consume data products in a data mesh Enterprise data management and analytics platform <li class="devsite-nav-item
 devsite-nav-expandable">

 BigQuery backup automation 
 Reference architecture Deploy the architecture <li class="devsite-nav-item
 devsite-nav-expandable">

 Load and process data 
 Continuous data replication to BigQuery using Striim 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Databases 
 Content overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Oracle workloads 
 Overview Enterprise application with Oracle Database on Compute Engine Enterprise application on Compute Engine with Oracle Exadata Oracle E-Business Suite with Oracle Database on Compute Engine Oracle E-Business Suite on Compute Engine with Oracle Exadata Oracle PeopleSoft on Compute Engine with Oracle Exadata Multi-cloud database management Microsoft SQL Server Always On availability group 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Hybrid and multicloud 
 Content overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Build hybrid and multicloud architectures 
 Overview Drivers, considerations, strategy, and patterns Plan a hybrid and multicloud strategy Architectural approaches to adopt a hybrid or multicloud architecture Other considerations What's next <li class="devsite-nav-item
 devsite-nav-break"> View the guide as a single page <li class="devsite-nav-item
 devsite-nav-expandable">

 Hybrid and multicloud architecture patterns 
 Overview Distributed architecture patterns Tiered hybrid pattern Partitioned multicloud pattern Analytics hybrid and multicloud patterns Edge hybrid pattern Environment hybrid pattern Business continuity hybrid and multicloud patterns Cloud bursting pattern What's next <li class="devsite-nav-item
 devsite-nav-break"> View the guide as a single page <li class="devsite-nav-item
 devsite-nav-expandable">

 Hybrid and multicloud secure networking architecture patterns 
 Overview Design considerations Architecture patterns Mirrored pattern Meshed pattern Gated patterns Gated egress Gated ingress Gated egress and gated ingress Handover pattern General best practices What's next <li class="devsite-nav-item
 devsite-nav-break"> View the guide as a single page <li class="devsite-nav-item
 devsite-nav-expandable">

 Cross-Cloud Network for distributed applications 
 Overview Connectivity Service networking Network security Cross-Cloud Network inter-VPC connectivity using Network Connectivity Center Cross-Cloud Network inter-VPC connectivity with VPC Network Peering VPC Network Peering Cross-Cloud Network with NVAs and regional affinity Network Connectivity Center Cross-Cloud Network with NVAs and regional failover <li class="devsite-nav-item
 devsite-nav-expandable">

 Hybrid and multicloud applications 
 <li class="devsite-nav-item
 devsite-nav-expandable">

 Hybrid render farm 
 Build a hybrid render farm Patterns for connecting other cloud service providers with Google Cloud <li class="devsite-nav-item
 devsite-nav-expandable">

 Identity and access management 
 <li class="devsite-nav-item
 devsite-nav-expandable">

 Authenticate workforce users in a hybrid environment 
 Overview Implementation patterns Configure Active Directory for VMs to automatically join a domain Deploy an Active Directory forest on Compute Engine Patterns for using Active Directory in a hybrid environment <li class="devsite-nav-item
 devsite-nav-expandable">

 Third-party product integrations 
 Data management with Cohesity Helios and Google Cloud 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Migration 
 Content overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Migrate to Google Cloud 
 Get started Assess and discover your workloads Plan and build your foundation Transfer your large datasets Deploy your workloads Migrate from manual deployments to automated, containerized deployments Optimize your environment Best practices for validating a migration plan Minimize costs <li class="devsite-nav-item
 devsite-nav-expandable">

 Migrate from AWS to Google Cloud 
 Get started Migrate Amazon EC2 to Compute Engine Migrate Amazon S3 to Cloud Storage Migrate Amazon EKS to GKE Migrate from Amazon RDS and Amazon Aurora for MySQL to Cloud SQL for MySQL Migrate from Amazon RDS and Amazon Aurora for PostgreSQL to Cloud SQL and AlloyDB for PostgreSQL Migrate from Amazon RDS for SQL Server to Cloud SQL for SQL Server Migrate from AWS Lambda to Cloud Run <li class="devsite-nav-item
 devsite-nav-expandable">

 Migrate from Azure to Google Cloud 
 Get started Migrate on-premises VMs Migrate to a Google Cloud VMware Engine platform <li class="devsite-nav-item
 devsite-nav-expandable">

 Application migration 
 <li class="devsite-nav-item
 devsite-nav-expandable">

 Migrate containers to Google Cloud 
 Migrate from Kubernetes to GKE <li class="devsite-nav-item
 devsite-nav-expandable">

 Migrate across Google Cloud regions 
 Get started Design resilient single-region environments on Google Cloud Architect your workloads Prepare data and batch workloads for migration across regions <li class="devsite-nav-item
 devsite-nav-expandable">

 Data and Database migration 
 <li class="devsite-nav-item
 devsite-nav-expandable">

 Database migration guide 
 Concepts, principles, and terminology Set up and run a database migration process <li class="devsite-nav-item
 devsite-nav-expandable">

 Networks for migrating enterprise workloads 
 Architectural approaches Networking for secure intra-cloud access Networking for internet-facing application delivery Networking for hybrid and multicloud workloads <li class="devsite-nav-item
 devsite-nav-expandable">

 Use RIOT Live Migration to migrate to Redis Enterprise Cloud 
 Reference architecture Deploy the architecture Define migration scope 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Monitoring and logging 
 Content overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Export logs and metrics 
 Cloud Monitoring metric export <li class="devsite-nav-item
 devsite-nav-expandable">

 Import logs from Cloud Storage to Cloud Logging 
 Reference architecture Deploy the architecture Stream logs from Google Cloud to Splunk <li class="devsite-nav-item
 devsite-nav-expandable">

 Hybrid and multicloud monitoring 
 Hybrid and multicloud monitoring and logging patterns <li class="devsite-nav-item
 devsite-nav-expandable">

 Log and monitor on-premises resources with BindPlane 
 Overview Log on-premises resources Monitor on-premises resources <li class="devsite-nav-item
 devsite-nav-expandable">

 Stream logs from Google Cloud to Datadog 
 Reference architecture Deploy the architecture 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Networking 
 Content overview Best practices and reference architectures for VPC design <li class="devsite-nav-item
 devsite-nav-expandable">

 Connect 
 Hub-and-spoke network architecture Patterns for connecting other cloud service providers with Google Cloud <li class="devsite-nav-item
 devsite-nav-expandable">

 Secure 
 Fortigate architecture in Google Cloud Secure virtual private cloud networks with the Palo Alto VM-Series NGFW VMware Engine network security using centralized appliances 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Reliability and disaster recovery 
 Content overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Infrastructure reliability guide 
 Overview of reliability Building blocks of reliability Assess reliability requirements Design reliable infrastructure Manage traffic and load Manage and monitor infrastructure What's next <li class="devsite-nav-item
 devsite-nav-expandable">

 Disaster recovery planning guide 
 Overview Building blocks Scenarios for data Scenarios for applications Architecting for locality-restricted workloads Use cases: locality-restricted data analytics applications Architecting for cloud infrastructure outages <li class="devsite-nav-item
 devsite-nav-expandable">

 Application availability 
 Patterns for using floating IP addresses in Compute Engine <li class="devsite-nav-item
 devsite-nav-expandable">

 Data availability 
 Continuous data replication to Cloud Spanner using Striim Google Workspace Backup with Afi.ai High availability of PostgreSQL clusters on Compute Engine Business continuity with CI/CD on Google Cloud 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Security and IAM 
 Content overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Identity and access management overview 
 Overview <li class="devsite-nav-item
 devsite-nav-expandable">

 Concepts 
 Overview of Google identity management Reference architectures Single sign-on <li class="devsite-nav-item
 devsite-nav-expandable">

 Best practices 
 Best practices for planning accounts and organizations Best practices for federating Google Cloud with an external identity provider <li class="devsite-nav-item
 devsite-nav-expandable">

 Assess and plan 
 Plan the onboarding process Federate with Active Directory Federate with Microsoft Entra ID Assess existing user accounts Assess onboarding plans Assess the impact of user account consolidation on federation <li class="devsite-nav-item
 devsite-nav-expandable">

 Deploy 
 Prepare your Google Workspace or Cloud Identity account <li class="devsite-nav-item
 devsite-nav-expandable">

 Set up federation 
 Microsoft Entra ID user provisioning and single sign-on Microsoft Entra ID B2B user provisioning and single sign-on Microsoft Entra ID My Apps portal integration Active Directory user account provisioning Active Directory single sign-on Keycloak single sign-on Okta user provisioning and single sign-on <li class="devsite-nav-item
 devsite-nav-expandable">

 Consolidate accounts 
 Overview Migrate consumer accounts Evict unwanted consumer accounts Sanitize Gmail accounts Remove Gmail from consumer accounts Reconcile orphaned managed user accounts <li class="devsite-nav-item
 devsite-nav-expandable">

 Resources 
 Example announcement <li class="devsite-nav-item
 devsite-nav-expandable">

 Application security 
 Best practices for securing your applications and APIs using Apigee <li class="devsite-nav-item
 devsite-nav-expandable">

 Use context-aware access to secure apps and resources 
 Secure apps and resources Best practices Design secure deployment pipelines Use Google Cloud Armor, load balancing, and Cloud CDN to deploy programmable global front ends <li class="devsite-nav-item
 devsite-nav-expandable">

 Secured serverless architecture 
 Architecture using Cloud Functions Architecture using Cloud Run <li class="devsite-nav-item
 devsite-nav-expandable">

 Compliance 
 Limit scope of compliance for PCI environments in Google Cloud PCI Data Security Standard compliance PCI DSS compliance on GKE Security blueprint: PCI on GKE Tokenize sensitive cardholder data for PCI DSS <li class="devsite-nav-item
 devsite-nav-expandable">

 Data and identity protection 
 Configure SaaS data protection for Google Workspace data with SpinOne De-identification and re-identification of PII in large-scale datasets using Cloud DLP Secure data environments in Google Cloud Security log analytics in Google Cloud <li class="devsite-nav-item
 devsite-nav-expandable">

 Mitigation and avoidance 
 <li class="devsite-nav-item
 devsite-nav-expandable">

 Automate malware scanning for files uploaded to Cloud Storage 
 Reference architecture Deploy the architecture Identify and prioritize security risks with Wiz Security Graph and Google Cloud <li class="devsite-nav-item
 devsite-nav-expandable">

 Network security 
 Secure virtual private cloud networks with the Palo Alto VM-Series NGFW 

 <li class="devsite-nav-item
 devsite-nav-expandable
 devsite-nav-accordion">

 Storage 
 Content overview Design an optimal storage strategy for your cloud workload Parallel file systems for HPC workloads Optimize AI and ML workloads with Cloud Storage FUSE Optimize AI and ML workloads with Managed Lustre 

 Get Started

 <a href="/docs/get-started" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Get Started with Google Cloud" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Get Started with Google Cloud

 <a href="/docs/product-list" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Product List" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Product List

 <a href="/support/docs" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Cloud Customer Care" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Cloud Customer Care

 Featured Products

 <a href="/products/gemini-enterprise-agent-platform" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Agent Platform" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Agent Platform

 <a href="/apigee" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Apigee API Management" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Apigee API Management

 <a href="/bigquery" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: BigQuery" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 BigQuery

 <a href="/products/compute" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Compute Engine" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Compute Engine

 <a href="/cdn" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Cloud CDN" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Cloud CDN

 <a href="/run" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Cloud Run" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Cloud Run

 <a href="/storage" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Cloud Storage" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Cloud Storage

 <a href="/sql" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Cloud SQL" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Cloud SQL

 <a href="/gemini/enterprise/docs" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Gemini Enterprise" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Gemini Enterprise

 <a href="/kubernetes-engine" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Google Kubernetes Engine" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Google Kubernetes Engine

 <a href="/looker" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Looker" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Looker

 Cross-product Tools

 <a href="/docs/access-resources" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Access and resources management" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Access and resources management

 <a href="/docs/costs-usage" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Costs and usage management" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Costs and usage management

 <a href="/docs/iac" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Infrastructure as code" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Infrastructure as code

 <a href="/docs/devtools" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: SDK, languages, frameworks, and tools" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 SDK, languages, frameworks, and tools

 Technology Areas

 <a href="/docs/ai-ml" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: AI and ML" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 AI and ML

 <a href="/docs/application-development" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Application development" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Application development

 <a href="/docs/application-hosting" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Application hosting" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Application hosting

 <a href="/docs/compute-area" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Compute" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Compute

 <a href="/docs/data" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Data analytics and pipelines" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Data analytics and pipelines

 <a href="/docs/databases" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Databases" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Databases

 <a href="/docs/dhm-cloud" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Distributed, hybrid, and multicloud" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Distributed, hybrid, and multicloud

 <a href="/docs/industry" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Industry solutions" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Industry solutions

 <a href="/docs/migration" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Migration" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Migration

 <a href="/docs/networking" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Networking" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Networking

 <a href="/docs/observability" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Observability and monitoring" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Observability and monitoring

 <a href="/docs/security" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Security" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Security

 <a href="/docs/storage" class="devsite-nav-title gc-analytics-event

 " data-category="Site-Wide Custom Events" data-label="Responsive Tab: Storage" track-type="navMenu" track-metadata-eventdetail="globalMenu" track-metadata-position="nav">

 Storage

 On this page Architecture Architecture components Agentic flow Products used Use cases Automated bug report triage Customer service Time-series forecasting Document retrieval Design alternatives Agent runtime AI model runtime Design considerations System design Security Reliability Operations Cost optimization Performance optimization Deployment What's next Contributors 

 <li class="devsite-breadcrumb-item
 ">

 Home

 <li class="devsite-breadcrumb-item
 ">

 Documentation

 <li class="devsite-breadcrumb-item
 ">

 Cloud Architecture Center

Was this helpful? 

 Send feedback

### 
 Single-agent AI system using ADK and Cloud Run 

 Stay organized with collections

 Save and categorize content based on your preferences. 

 On this page Architecture Architecture components Agentic flow Products used Use cases Automated bug report triage Customer service Time-series forecasting Document retrieval Design alternatives Agent runtime AI model runtime Design considerations System design Security Reliability Operations Cost optimization Performance optimization Deployment What's next Contributors 

 <div class="devsite-article-body clearfix
 ">

Last reviewed 2025-12-09 UTC 

This document provides a reference architecture to help you design a
single-agent AI system on Google Cloud. The single-agent system in
this architecture is built by using Agent Development Kit (ADK) and it's deployed
on Cloud Run. You can also deploy the agent on
Agent Runtime on Gemini Enterprise Agent Platform or Google Kubernetes Engine (GKE). The architecture
uses
 Model Context Protocol (MCP) ,
which enables the agent to access and process information from multiple
sources so that it can provide context-rich insights. 

This document is intended for architects, developers, and administrators of AI
applications. It assumes that you have a basic understanding of AI, machine
learning (ML), and large language model (LLM) concepts. The document also
assumes that you have a foundational understanding of AI agents and models. It
doesn't provide specific guidance for designing and coding AI agents. 

The Deployment section of this document lists code samples that
you can use to learn how to build and deploy single-agent AI systems. 

### Architecture 

The following diagram shows an architecture for a single-agent AI system that's
deployed on Cloud Run: 

### Architecture components 

The example architecture consists of the following components: 

 Component 
 Description 

 Frontend 

 Users interact with the agent through a frontend, such as a chat
 interface, that runs as a serverless Cloud Run service.

 Agent 

 The agent receives user requests, interprets user intent, selects the
 appropriate tools, and then it synthesizes information to answer
 queries.

 Agent runtime 

 The agent is built by using ADK and
 it's deployed as a serverless Cloud Run
 service . You can also deploy the agent on Agent Runtime on Gemini Enterprise Agent Platform or as
 a containerized app on GKE .
 For information about how to choose an agent runtime, see Choose your agentic AI architecture
 components . 

 ADK 

 ADK provides tools and a framework to develop, test, and
 deploy agents. ADK abstracts the complexity of agent
 creation and lets AI developers focus on the agent's logic and
 capabilities. When you develop agents by using ADK, you
 can configure the agents to access and use built-in
 tools like Google Search.

 AI model and model runtime 

 For inference serving, the agent in this example architecture uses
 the Gemini AI model on Gemini Enterprise Agent Platform .

 MCP Toolbox 

 MCP Toolbox for Databases provides
 database-specific tools for the agent. It can handle complexities
 such as connection pooling and authentication.

 MCP clients, servers, and tools 

 MCP 
 facilitates access to tools by standardizing the interaction between
 agents and tools. For each agent-tool pair, an MCP client sends
 requests to an MCP server through which the agent accesses a tool
 such as a file system or an API. For example, external tools like the
 StackOverflow LangChain Tool and the Google Search tool can
 provide data and grounding.

 Observability 
 The agent is monitored by using Google Cloud Observability for
 logging, monitoring, and tracing. 

### Agentic flow

The example single-agent system in the preceding architecture has the following
flow: 

 A user enters a prompt through a frontend, such as a chat interface,
which runs as a serverless Cloud Run service. 
 The frontend forwards the prompt to the agent. 
 The agent uses the AI model to reason about the user's prompt and
synthesize a response:

 The AI model determines which tools to use to gather contextual
information or to perform a task. 
 The agent performs tool calls and it adds the response to its context. 
 The agent performs grounding and intermediate validation. 

### Products used

This reference architecture uses the following Google Cloud and open-source
products and tools: 

Cloud Run : A serverless compute platform that lets you run
containers directly on top of Google's scalable infrastructure. 

Gemini : A family of multimodal AI models developed by Google.

Gemini Enterprise Agent Platform : A comprehensive platform that
lets you build, scale, govern, and optimize enterprise‑grade AI agents.

Model Context Protocol (MCP) : An open-source standard for connecting AI applications to external
systems. 

MCP Toolbox for Databases : An open-source 
Model Context Protocol (MCP) server that lets AI agents securely connect to databases by managing database complexities like connection pooling, authentication, and observability. 

Google Cloud Observability : Observability services including Cloud Monitoring,
Cloud Logging, and Cloud Trace to help you understand the behavior,
health, and performance of your applications.

### Use cases

This section describes possible use cases for the architecture that's described
in this document. 

### Automated bug report triage

You can adapt this reference architecture to automate triage for incoming bug
reports: understanding the issue, searching for duplicates, gathering relevant
technical context, and then creating a bug in the system. An AI-powered agent
can act as an intelligent assistant that can perform the initial investigation,
which lets human experts focus on more complex problem-solving. 

For this use case, the architecture provides the following benefits: 

 Faster resolution times : The agent automates the initial research and
context-gathering, which can significantly reduce the time that it takes to
assign and resolve bug tickets. 
 Improved accuracy and consistency : The agent can systematically
search across multiple data sources (internal databases, code repositories,
and the public web). This capability provides a more comprehensive and
consistent analysis than manual triage might allow. 
 Reduced manual workload : The agent can offload repetitive triage
tasks from IT support and engineering teams, which lets them focus on
higher-value work. 

This architecture is ideal for any organization that develops software and that
wants to improve the efficiency and effectiveness of its bug resolution process.
For more information and deployment options, see
 Software Bug Assistant - ADK Python Sample Agent 
and
 Tools Make an Agent: From Zero to Assistant with ADK . 

### Customer service

You can adapt this reference architecture to help provide a seamless and
personalized shopping experience for customers. An AI-powered agent can provide
customer service, recommend products, manage orders, and schedule services,
which lets human representatives focus on other tasks. 

For this use case, the architecture provides the following benefits: 

 Upselling and promotions : The agent can help increase sales by
suggesting products, services, and promotions. The agent's suggestions are
based on the customer's current order and relevant sales, the customer's
order history, and the items that are in their cart. 

 Order management and scheduling : The agent can increase efficiency
and reduce customer friction by managing the contents of a customer's
shopping cart and facilitating self-scheduling for services. 

 Reduced manual workload : The agent handles general inquiries, orders,
and scheduling, which enables human customer service agents to focus on
more complex customer issues. 

This architecture is ideal for any retail organization that wants to improve
their customer experience, increase sales, and simplify their order management
and scheduling. For more information and deployment options, see
 Cymbal Home & Garden Customer Service Agent . 

### Time-series forecasting

You can adapt this reference architecture to help predict outcomes, such as
demand forecasting, traffic patterns prediction, or machine failure analysis and
prediction. An AI-powered agent can analyze real-time data, historical trends,
and upcoming events. The agent can use these analyses to forecast outcomes for a
specified period of time. These forecasts can help you plan and help reduce the
time spent by human data analysts. 

This use case can benefit organizations in many scenarios, such as the
following: 

 Inventory management : By using advanced analytics combined with
historical sales data and market trends, the agent can help you plan
restock orders so that you can prepare for surges or lulls in customer
demand. 
 Travel routes : The agent can help save time and reduce travel costs
for delivery and service providers by analyzing real-time and historical
traffic patterns along with events like construction or road closures. 
 Avoid outages : The agent can help you avoid potential service
interruptions by helping to identify the root cause for historical outages.
It can also help predict future potential failure states so that you can
mitigate an issue before it becomes a problem. 

This architecture is ideal for any organization that needs to adapt to changing
patterns based on established trends. It's also ideal for organizations whose
customers can benefit from proactive insights that help them plan for the
future. For more information and deployment options, see
 Time Series Forecasting Agent with Google's ADK and MCP Toolbox . 

### Document retrieval

You can adapt this reference architecture to use
 RAG Engine on Gemini Enterprise Agent Platform 
and create an agent to manage contextual data retrieval. A document-retrieval
agent can fetch relevant data from a curated set of documents to provide factual
answers with citations to the source material. 

With a document-retrieval agent, you can help ensure that customers and
internal users get informed and context-aware responses to their queries. This
implementation can help reduce mistakes and inaccuracies by helping to ensure
that answers are based on the information that you validated. 

A document-retrieval architecture is ideal for knowledge bases about policy and
process, technical infrastructure, product capabilities, and other fact-based
documentation. For information about how to develop a retrieval-augmented
generation (RAG)-powered document retrieval agent, see
 Documentation Retrieval Agent . 

### Design alternatives

This section presents alternative design approaches that you can consider for
your AI agent deployment in Google Cloud. 

### Agent runtime

In the architecture that this document describes, the agent and its tools are
deployed on Cloud Run. You can also use GKE or
Agent Runtime as an alternative runtime. For information
about how to choose an agent runtime, see
 Agent runtime 
in "Choose your agentic AI architecture components". 

### AI model runtime

In the architecture that this document describes, the AI model runtime is
Agent Platform. You can also use Cloud Run or GKE as an alternative runtime. For
information about how to choose a model runtime, see
 Model runtime 
in "Choose your agentic AI architecture components". 

### Design considerations

This section provides guidance to help you use this reference architecture to
develop an architecture that meets your specific requirements for security,
reliability, cost, operational efficiency, and performance. 

### System design

This section provides guidance to help you choose Google Cloud regions for
your deployment and to select appropriate Google Cloud products and tools. 

### Region selection

When you select Google Cloud regions for your AI applications, consider
the following factors: 

 Availability of Google Cloud services 
in each region. 
 End-user
 latency 
requirements. 
 Cost 
of Google Cloud resources. 
 Regulatory requirements. 

To select appropriate Google Cloud locations for your applications, use
the following tools: 

 Google Cloud Region Picker :
An interactive web-based tool to select the optimal Google Cloud
region for your applications and data based on factors like carbon
footprint, cost, and latency. 
 Cloud Location Finder API :
A public API that provides a programmatic way to find deployment
locations in Google Cloud, Google Distributed Cloud, and other cloud
providers. 

### Agent design

This section provides general recommendations for designing AI agents. Detailed
guidance about writing agent code and logic is outside the scope of this
document. 

 Design focus 
 Recommendations 

 Agent definition and design 

 Clearly define the business goal of the agentic AI system and the task
 that each agent performs. 
 Choose an
 agent design pattern 
 that best meets your requirements. 
 Use ADK to efficiently create, deploy, and manage your
 agentic architecture. 

 Agent interactions 

 Design the human-facing agents in the architecture to support natural
 language interactions. 
 Ensure that each agent clearly communicates its actions and status to
 its dependent clients. 
 Design the agents to detect and handle ambiguous queries and nuanced
 interactions. 

 Context, tools, and data 

 Ensure that the agents have sufficient
 context to track multi-turn
 interactions and session parameters. 
 Clearly describe the purpose, arguments, and usage of the tools that
 the agents can use. 
 Ensure that the agents' responses are grounded in reliable data
 sources to reduce hallucinations. 
 Implement logic to handle no-match situations, such as when a prompt
 is off-topic. 

### Memory and session storage

The example architecture that's shown in this document doesn't include memory
or session storage. In a production environment, you can improve the responses
and add personalization by integrating state and memory into your agent. 

 Session :
A session is the conversational thread between a user and the agent, from
the initial interaction to the end of the dialogue. 
 State :
State is the data that the agent uses and collects within a specific
session. The state data that's collected includes the history of messages
that the user and agent exchanged, the results of any tool calls, and other
variables that the agent needs in order to understand the context of the
conversation. 

ADK can track sessions in short-term memory by using the
 Session object and state attributes. ADK also supports
 long-term memory 
across sessions with the same user, including through
 Memory Bank .
To store session state, you can also use services like
 Memorystore for Redis . 

For information about agent memory options, see
 Choose your agentic AI architecture components . 

### Security

This section describes design considerations and recommendations to design a
topology in Google Cloud that meets your workload's security requirements. 

 Component 
 Design considerations and recommendations 

 Agents 

AI agents introduce certain unique and critical security risks that
 conventional, deterministic security practices might not be able to
 mitigate adequately. Google recommends an
 approach that combines the strengths
 of deterministic security controls with dynamic, reasoning-based
 defenses. This approach is grounded in three core principles: human
 oversight, carefully defined agent autonomy, and observability. The
 following are specific recommendations that are aligned with these
 core principles. 

 Human oversight : An agentic AI system might sometimes
 fail or not perform as expected. For example, the model might generate
 inaccurate content or an agent might select inappropriate tools. In
 business-critical agentic AI systems, incorporate a
 human-in-the-loop flow to let human
 supervisors monitor, override, and pause agents. For
 example, human users can review the output of agents, approve or reject
 the outputs, and provide further guidance to correct errors or to make
 strategic decisions. This approach combines the efficiency of agentic AI
 systems with the critical thinking and domain expertise of human users.

 Access control for agents : Configure agent permissions
 by using Identity and Access Management (IAM) controls. Grant each agent only the
 permissions that it needs to perform its tasks and to communicate with
 tools and with other agents. This approach helps to minimize the
 potential impact of a security breach, because a compromised agent would
 have limited access to other parts of the system. For more information,
 see
 Agent Platform
 access control with IAM .

 Monitoring : Monitor agent behavior by using
 comprehensive tracing capabilities that give you visibility into every
 action that an agent takes, including its reasoning process, tool
 selection, and execution paths. For more information, see
 Logging an agent in
 Agent Runtime and
 Logging in the ADK . 

For more information about securing AI agents, see
 Safety and Security for AI Agents . 

 Agent Platform 

 Shared responsibility : Security is a shared
 responsibility. Agent Platform secures the underlying
 infrastructure and provides tools and security controls to help you
 protect your data, code, and models. You are responsible for properly
 configuring your services, managing access controls, and securing your
 applications. For more information, see

 Agent Platform shared responsibility . 

 Security controls : Agent Platform supports
 Google Cloud security controls that you can use to meet your
 requirements for data residency,
 customer-managed
 encryption keys (CMEK) , network security using
 VPC Service Controls , and
 Access Transparency . For more information,
 see the following documentation: 

 Security controls for
 Agent Platform 
 Security controls for Generative AI 

 Agent Platform and zero data retention 

 Safety : AI models might produce harmful responses,
 sometimes in response to malicious prompts. 

 To enhance safety and
 mitigate potential misuse of the agentic AI system, you can configure
 content filters to act as barriers to harmful inputs and responses. For
 more information, see
 Safety and content filters . 
 To inspect
 and sanitize inference requests and responses for threats like prompt
 injection and harmful content, you can use
 Model Armor .
 Model Armor helps you prevent malicious input, verify
 content safety, protect sensitive data, maintain compliance, and enforce
 safety and security policies consistently. 

 Model access : You can set up organization policies to
 limit the type and versions of AI models that can be used in a
 Google Cloud project. For more information, see
 Control access to Model Garden
 models . 

 Data protection : To discover and de-identify sensitive
 data in the prompts and responses and in log data, use the
 Cloud Data Loss Prevention API .
 For more information, see this video:
 Protecting sensitive data in AI apps .

 MCP 
 When you configure your agents to use MCP, ensure that access to
 external data and tools is authorized, implement privacy controls like
 encryption, apply filters to protect sensitive data, and monitor agent
 interactions. For more information, see
 MCP and Security . 

 A2A 

 Transport security : The A2A protocol mandates
 HTTPS for all A2A communication in production environments and it recommends
 Transport Layer Security (TLS) 
 versions 1.2 or higher. 

 Authentication : The A2A protocol delegates
 authentication to standard web mechanisms like HTTP headers and to
 standards like OAuth2 and OpenID Connect. Each agent advertises the
 authentication requirements in its Agent Card. For more information, see
 A2A authentication . 

 Cloud Run 

 Ingress security (for the frontend service) : To control
 access to the application,
 disable the
 default run.app URL of the frontend
 Cloud Run service and
 set up a regional external Application Load Balancer . In
 addition to load-balancing incoming traffic to the application, the load
 balancer handles SSL certificate management. For added protection, you can
 use
 Google Cloud Armor security policies to
 provide request filtering, DDoS protection, and rate limiting for the
 service. 

 User authentication :

 Users inside your organization : To authenticate
 internal user access to the frontend Cloud Run
 service, use Identity-Aware Proxy (IAP). When a
 user tries to access an IAP-secured resource,
 IAP performs authentication and authorization checks.

 Users outside your organization : To authenticate
 external user access to the frontend service, use Identity Platform or Firebase Authentication . To manage
 external user access, configure your application to handle a sign-in
 flow
 and to make authenticated API calls to the Cloud Run
 service.

 For more information, see Authenticating users .

 Container image security : To ensure that only
 authorized container images are deployed to Cloud Run, you
 can use

 Binary Authorization .
 To identify and mitigate security risks in the container images, use
 Artifact Analysis to automatically run vulnerability scans. For
 more information, see
 Container scanning overview . 

 Data residency : Cloud Run helps you meet
 data residency requirements. Your Cloud Run functions run within
 the selected
 region . 

For more guidance about container security, see
 General
 Cloud Run development tips . 

 All of the products in the architecture 

 Data encryption : By default, Google Cloud
 encrypts data at rest by using Google-owned and Google-managed encryption keys.
 To protect your agents' data by using encryption keys that you control,
 you can use CMEKs 
 that you create and manage in Cloud KMS. For information about
 Google Cloud services that are compatible with Cloud KMS,
 see
 Compatible
 services . 

 Mitigate data exfiltration risk : To reduce the risk of
 data exfiltration, create a
 VPC Service Controls perimeter
 around the infrastructure. VPC Service Controls supports all of the
 Google Cloud services that this reference architecture uses. 

 Access control : When you configure permissions for the
 resources in your topology, follow the principle of
 least privilege . 

 Cloud environment security : Use the tools in
 Security Command Center to detect
 vulnerabilities, identify and mitigate threats, define and deploy a
 security posture, and export data for further analysis. 

 Post-deployment optimization : After you deploy your
 application in Google Cloud, get recommendations to further
 optimize security by using Active Assist. Review the
 recommendations and apply them as appropriate for your environment. For
 more information, see
 Find recommendations in
 Active Assist . 

### More security recommendations

 Well-Architected Framework AI and ML perspective: Security 
 Google's Approach for Secure AI Agents: An Introduction 

### Reliability

This section describes design considerations and recommendations to build and
operate reliable infrastructure for your deployment in Google Cloud. 

 Component 
 Design considerations and recommendations 

 Agent 

 Simulate failures : Before you deploy the agentic AI
 system to production, validate it by simulating a production
 environment. Identify and fix issues and unexpected behaviors.

 Scale horizontally : To help ensure high availability
 and fault tolerance, run multiple instances of your agent application
 behind a load balancer. This approach can also help reduce latency
 and timeouts by distributing requests across instances. Some agent
 runtimes handle load balancing for you automatically, such as with instance
 autoscaling in Cloud Run services .

 Recover from outages : To help ensure that the agent
 can gracefully handle restarts and maintain context, decouple state
 from runtime. To implement such a stateless agent application, use an
 external datastore like a database or a distributed cache. For
 example, you can use Memory Bank , Memorystore for Redis , or a database service like Cloud SQL .

 Handle errors : To enable diagnosis and
 troubleshooting of errors, implement logging, exception handling, and
 retry mechanisms.

 Agent Platform 

 Capacity planning : If the number of your requests
 exceeds the allocated capacity, then
 error code 429 is returned. For
 workloads that are business critical and consistently require high
 throughput, you can reserve throughput by using Provisioned Throughput .

 Model endpoint availability : If
 data can be shared across multiple regions or countries, you can
 use a global endpoint for the
 model.

 Cloud Run 

 Robustness to infrastructure outages :
 Cloud Run is a regional service. It stores data
 synchronously across multiple zones within a region and it automatically
 load-balances traffic across the zones. If a zone outage occurs,
 Cloud Run continues to run and data isn't lost. If a
 region outage occurs, the service stops running until Google resolves
 the outage.

 Horizontal scaling : Cloud Run services
 handle instance
 autoscaling for you. Autoscaling helps ensure that instances can
 handle all of the incoming requests, events, and CPU utilization
 that's needed to ensure high availability.

 All of the products in the architecture 

 Post-deployment optimization : After you deploy your
 application in Google Cloud, get recommendations to further
 optimize security by using Active Assist. Review the
 recommendations and apply them as appropriate for your environment. For
 more information, see
 Find
 recommendations in Active Assist .

For reliability principles and recommendations that are specific to AI and ML workloads, see
 AI and ML perspective: Reliability 
in the Well-Architected Framework.

### Operations

This section describes the factors to consider when you use this reference
architecture to design a Google Cloud topology that you can operate
efficiently. 

 Component 
 Design considerations and recommendations 

 Agent 

 Debugging and analysis : Implement structured logging
 within your agent application. Logging and tracing lets you capture
 key information in a structured format, such as which tools were
 called, the inputs and outputs of the agent, and the latency of each
 step.

 Agent Platform 

 Monitoring using logs : By default, agent logs that
 are written to the stdout and stderr streams
 are routed to Cloud Logging. For advanced logging, you can integrate
 the Python logger with Logging. If you need full control
 over logging and structured logs, use the Logging client.
 For more information, see Logging an agent and Logging in
 ADK .

 Continuous evaluation : Regularly perform a
 qualitative evaluation of the output of the agents and the trajectory
 or steps taken by the agents to produce the output. To implement
 agent evaluation, you can use the Gen AI evaluation service or the
 evaluation
 methods that ADK supports .

 Cloud Run 

 Health and performance : Monitor your
 Cloud Run services by using Google Cloud Observability. Set up
 alerts in Cloud Monitoring to notify you of potential issues, such as
 an increase in error rates, high latency, or abnormal resource
 utilization.

 Databases 

 Health and performance : Monitor your database by
 using Google Cloud Observability. Set up alerts in Monitoring
 to notify you of potential issues, such as an increase in error
 rates, high latency, or abnormal resource utilization.

 MCP 

 Database tools : To efficiently manage database tools
 for your AI agents and to ensure that the agents securely handle
 complexities like connection pooling and authentication, use the MCP Toolbox
 for Databases . It provides a centralized location to store and
 update database tools. You can share the tools across agents and
 update the tools without redeploying agents. The toolbox includes a
 wide range of tools for Google Cloud databases like
 AlloyDB for PostgreSQL and for third-party databases like MongoDB.

 Generative AI models : To enable AI agents to use
 Google generative AI models like Imagen and Veo, you can use MCP Servers
 for Google Cloud generative media APIs .

 Google security products and tools : To enable your
 AI agents to access Google security products and tools like
 Google Security Operations, Google Threat Intelligence, and
 Security Command Center, use MCP servers
 for Google security products .

 All of the Google Cloud products in the architecture 

 Tracing : Continuously gather and analyze trace data
 by using Trace. Trace data lets you rapidly identify and
 diagnose latency issues within complex agent workflows. You can
 perform in-depth analysis through visualizations in the Google Cloud console
 Trace explorer page. For more information, see Trace an agent .

For operational excellence principles and recommendations that are specific to AI and ML workloads, see
 AI and ML perspective: Operational excellence 
in the Well-Architected Framework.

### Cost optimization

This section provides guidance to optimize the cost of setting up and operating
a Google Cloud topology that you build by using this reference
architecture. 

 Component 
 Design considerations and recommendations 

 Agent Platform 

 Cost analysis and management : To analyze and manage
 Agent Platform costs, we recommend that you create baseline
 metrics for queries per second (QPS) and tokens per second (TPS). Then,
 monitor these metrics after deployment. The baseline also helps with
 capacity planning. For example, the baseline helps you determine when
 Provisioned Throughput 
 might be necessary. 

 Model selection : The
 model that
 you select for your AI application directly affects both costs and
 performance. To identify the model that provides an optimal balance
 between performance and cost for your specific use case, test models
 iteratively. We recommend that you start with the most cost-efficient
 model and progress gradually to more powerful options. 

 Cost-effective prompting : The length of your prompts
 (input) and the generated responses (output) directly affect performance
 and cost. Write prompts that are short, direct, and provide sufficient
 context. Design your prompts to get concise responses from the model.
 For example, include phrases such as "summarize in 2 sentences" or
 "list 3 key points". For more information, see the
 best practices for prompt design . 

 Context caching : To reduce the cost of requests that
 contain repeated content with high input token counts, use
 context caching . 

 Batch requests : When relevant, consider
 batch prediction . Batched requests
 incur a lower cost than standard requests. 

 Cloud Run 

 Resource allocation : When you create a
 Cloud Run service, you can specify the amount of memory
 and CPU to be allocated. Start with the default CPU and memory
 allocations. Observe the resource usage and cost over time, and adjust
 the allocation as necessary. For more information, see the following
 documentation: 

 Configure memory limits for services 
 Configure CPU
 limits for services 

 Rate optimization : If you can predict the CPU and
 memory requirements, you can save money with
 committed use discounts (CUDs) . 

 All of the products in the architecture 
 Post-deployment optimization : After you deploy your
 application in Google Cloud, get recommendations to further
 optimize cost by using Active Assist.
 Review the recommendations and apply
 them as appropriate for your environment. For more information, see
 Find recommendations in
 Active Assist . 

To estimate the cost of your Google Cloud resources, use the
 Google Cloud Pricing Calculator . 

For cost optimization principles and recommendations that are specific to AI and ML workloads, see
 AI and ML perspective: Cost optimization 
in the Well-Architected Framework.

### Performance optimization

This section describes design considerations and recommendations to design a
topology in Google Cloud that meets the performance requirements of your
workloads. 

 Component 
 Design considerations and recommendations 

 Agents 

 Model selection : When you select models for your
 agentic AI system, consider the capabilities that are required for the
 tasks that the agents need to perform. 

 Prompt optimization : To rapidly improve and optimize
 prompt performance at scale and to eliminate the need for manual
 rewriting, use the
 Agent Platform prompt optimizer .
 The optimizer helps you efficiently adapt prompts across different
 models. 

 Agent Platform 

 Model selection : The
 model that
 you select for your AI application directly affects both costs and
 performance. To identify the model that provides an optimal balance
 between performance and cost for your specific use case, test models
 iteratively. We recommend that you start with the most cost-efficient
 model and progress gradually to more powerful options. 

 Prompt engineering : The length of your prompts (input)
 and the generated responses (output) directly affect performance and
 cost. Write prompts that are short, direct, and provide sufficient
 context. Design your prompts to get concise responses from the model. For
 example, include phrases such as "summarize in 2 sentences" or "list 3
 key points". For more information, see the
 best practices for prompt design . 

 Context caching : To reduce latency for requests that
 contain repeated content with high input token counts, use
 context caching . 

 Cloud Run 

 Resource allocation : Depending on your performance
 requirements, configure the memory and CPU to be allocated to the
 Cloud Run service. For more information, see the following
 documentation: 

 Configure memory limits for services 

 Configure CPU
 limits for services 

For more performance optimization guidance, see
 General Cloud Run
 development tips . 

 All of the products in the architecture 
 Post-deployment optimization : After you deploy your
 application in Google Cloud, get recommendations to further
 optimize performance by using Active Assist.
 Review the recommendations and apply
 them as appropriate for your environment. For more information, see
 Find recommendations in
 Active Assist . 

For performance optimization principles and recommendations that are specific to AI and ML workloads, see
 AI and ML perspective: Performance optimization 
in the Well-Architected Framework.

### Deployment

Automated deployment for this reference architecture isn't available. Use the
following code samples to help you build a single-agent architecture: 

 Deploy a similar architecture by deploying the
 Software Bug Assistant - ADK Python Sample Agent . 
 Learn more about memory and state with
 Python Tutor - ADK State and Memory Example . 

For code samples to get started with using ADK together with MCP servers, see
 MCP Tools . 

For examples of additional single-agent AI systems, you can use the following
code samples. These code samples are fully functional starting points for
learning and experimentation. For optimal operation in production environments,
you must customize the code based on your specific business and technical
requirements. 

 Personalized shopping :
Provide personalized product recommendations for a specific brand,
merchant, or online marketplace. 
 Incident management :
Validate end-user token and identity on a per-request basis by using
dynamic identity propagation. 
 Order processing :
Process and store orders and orchestrate email confirmation with a
conditional human review for specified order quantities. 
 Data engineering :
Develop Dataform pipelines, troubleshoot pipeline issues, and
manage data engineering from complex SQL queries to data transformations and
data dependencies. 
 Documentation retrieval :
Use RAG to query documents that you upload to RAG Engine on Gemini Enterprise Agent Platform
and get answers with citations to documentation and code. 

### What's next

 Explore sample agents and tools in Agent Garden . 
 Build agents using ADK . 
 Deploy agents to Google Cloud . 
 Host MCP servers on Cloud Run . 
 Host AI apps and agents on Cloud Run . 
 Learn how to implement a
 RAG infrastructure for generative AI applications in Google Cloud . 

For an overview of architectural principles and recommendations that are specific to AI
and ML workloads in Google Cloud, see the
 AI and ML perspective 
in the Well-Architected Framework.

For more reference architectures, diagrams, and best practices, explore the
 Cloud Architecture Center .

### Contributors

 Kumar Dhanagopal | Cross-Product Solution Developer 
 Megan O'Keefe | Developer Advocate 
 Shir Meir Lador | Developer Relations Engineering Manager 

Was this helpful? 

 Send feedback

Except as otherwise noted, the content of this page is licensed under the Creative Commons Attribution 4.0 License , and code samples are licensed under the Apache 2.0 License . For details, see the Google Developers Site Policies . Java is a registered trademark of Oracle and/or its affiliates. 

Last updated 2025-12-09 UTC. 

 Need to tell us more?

 [[["Easy to understand","easyToUnderstand","thumb-up"],["Solved my problem","solvedMyProblem","thumb-up"],["Other","otherUp","thumb-up"]],[["Hard to understand","hardToUnderstand","thumb-down"],["Incorrect information or sample code","incorrectInformationOrSampleCode","thumb-down"],["Missing the information/samples I need","missingTheInformationSamplesINeed","thumb-down"],["Other","otherDown","thumb-down"]],["Last updated 2025-12-09 UTC."],[],[]]

### Products and pricing

 See all products

 Google Cloud pricing

 Google Cloud Marketplace

 Contact sales

### Support

 Community forums

 Support

 Release Notes

 System status

### Resources

 GitHub

 Getting Started with Google Cloud

 Code samples

 Cloud Architecture Center

 Training and Certification

### Engage

 Blog

 Events

 X (Twitter)

 Google Cloud on YouTube

 Google Cloud Tech on YouTube

 <a href="https://developer.android.com/" class="devsite-footer-sites-link
 gc-analytics-event" data-category="Site-Wide Custom Events" data-label="Footer Android Developers Link">
 Android

 <a href="https://developer.chrome.com/" class="devsite-footer-sites-link
 gc-analytics-event" data-category="Site-Wide Custom Events" data-label="Footer Chrome Link">
 Chrome

 <a href="https://firebase.google.com/" class="devsite-footer-sites-link
 gc-analytics-event" data-category="Site-Wide Custom Events" data-label="Footer Firebase Link">
 Firebase

 <a href="https://ai.google.com/" class="devsite-footer-sites-link
 gc-analytics-event" data-category="Site-Wide Custom Events" data-label="Footer Google AI Link">
 Google AI

 <li class="devsite-footer-utility-item
 ">

 About Google

 <li class="devsite-footer-utility-item
 devsite-footer-privacy-link">

 Privacy

 <li class="devsite-footer-utility-item
 ">

 Site terms

 <li class="devsite-footer-utility-item
 ">

 Google Cloud terms

 <li class="devsite-footer-utility-item
 glue-cookie-notification-bar-control">

 Manage cookies

 <li class="devsite-footer-utility-item
 devsite-footer-carbon-button">

 Our third decade of climate action: join us

 <li class="devsite-footer-utility-item
 devsite-footer-utility-button">

 Sign up for the Google Cloud newsletter 

 Subscribe

 English 

 Deutsch 

 Español 

 Español – América Latina 

 Français 

 Indonesia 

 Italiano 

 Português 

 Português – Brasil 

 עברית 

 中文 – 简体 

 中文 – 繁體 

 日本語 

 한국어