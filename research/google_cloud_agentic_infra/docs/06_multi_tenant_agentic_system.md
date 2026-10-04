# Multi-Tenant Agentic AI System Architecture

**Source URL:** https://docs.cloud.google.com/architecture/multi-tenant-agentic-ai-system

---

Multi-tenant agentic AI system  |  Cloud Architecture Center  |  Google Cloud Documentation 

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

 Español – América Latina 

 Français 

 Indonesia 

 Italiano 

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
 " track-metadata-position="nav" track-metadata-eventdetail="nav" track-name="gcpCta" referrerpolicy="no-referrer-when-downgrade" track-type="freeTrial">Start free 

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

 On this page Architecture Agentic flow Products used Use case Enterprise-wide customer service Design alternatives Private access deployment Compute infrastructure Model Context Protocol (MCP) servers Design considerations Security, privacy, and compliance Reliability Operational efficiency Cost optimization Deployment What's next Contributors 

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
 Multi-tenant agentic AI system 

 Stay organized with collections

 Save and categorize content based on your preferences. 

 On this page Architecture Agentic flow Products used Use case Enterprise-wide customer service Design alternatives Private access deployment Compute infrastructure Model Context Protocol (MCP) servers Design considerations Security, privacy, and compliance Reliability Operational efficiency Cost optimization Deployment What's next Contributors 

 <div class="devsite-article-body clearfix
 ">

Last reviewed 2026-06-18 UTC 

This document provides a reference architecture to help you design and deploy a
multi-tenant agentic AI system on Google Cloud. As your
organization scales generative AI deployments, different business units require
specialized AI agents that access unique tools, follow specific operational
rules, and process sensitive data. Business units might develop fragmented
application silos within an organization, which can cause high operational
overhead, severe governance gaps, and a risk of data exposure. This architecture
shows you how to build a centralized system that lets you empower decentralized
teams with autonomous AI capabilities while you maintain unified security and
compliance. 

The intended audience for this document includes architects, developers, and
administrators who build and manage enterprise-grade, multi-agent systems in the
cloud. The document assumes that you have a foundational understanding of AI,
ML, and LLM concepts, and
of agentic AI . 

The deployment section of this document provides an
implementation strategy to help you build and deploy a multi-tenant agentic AI
system. 

### Architecture 

The following diagram shows an architecture for a multi-tenant agentic AI system
that follows a
 hub-and-spoke model .
A hub-and-spoke model is a network design where a central environment, which is
known as a hub , connects to multiple isolated environments, which are known as
 spokes . 

The architecture consists of the following components: 

 Component 
 Description 

 VPC Service Controls 

 The architecture uses VPC Service Controls to configure a service perimeter 
 at the organization level. This service perimeter provides a strict
 security boundary and it prevents data exfiltration.

 Routing hub 

The routing hub acts as the central ingress point for the architecture
 and it includes the following components: 

 External Application Load Balancer :
 Acts as
 the central ingress point for external or internal users. The load
 balancer ensures that only authenticated and safe traffic reaches the
 frontend portal.

 Google Cloud Armor 
 and Model Armor :
 The load balancer integrates
 Cloud Armor and Model Armor to inspect and
 scrub malicious prompts
 at the network edge. The routing hub uses
 Service Extensions 
 on the external Application Load Balancer to integrate Model Armor directly
 into the request flow.

 Identity-Aware Proxy (IAP) : Enforces a
 zero-trust
 model to verify user identity and context before any request
 reaches the application.

 Frontend portal : A serverless Cloud Run
 application that acts as a routing engine to route requests to the
 appropriate isolated tenant project.

 Central governance and security hub 

The central governance and security hub is a dedicated
 Google Cloud project that provides centralized
 Identity and Access Management (IAM), logging, monitoring,
 and security for the entire platform. This hub includes the following
 components: 

 Security Command Center : A service that monitors the entire
 multi-tenant agentic AI system for security risks.

 IAM : An access control framework that manages identities and permissions
 across the shared hubs and the tenant projects. This component provides centralized
 governance for all human and machine identities.

 Cloud Logging :
 A system that aggregates logs
 from the shared hubs and from the isolated tenant projects into the
 central governance and security hub.

 Tenant projects 

Each tenant project is a dedicated Google Cloud project for each
 business unit. Individual tenant projects are isolated environments that
 include the following components: 

 Principal Access Boundary Policy (PAB Policy) : PAB Policy provides internal hard isolation between
 different business units and they
 ensure that principals can only access resources within their approved
 boundaries.

 Agent Runtime on Gemini Enterprise Agent Platform : A runtime that hosts the specific business unit agent and
 executes custom orchestration
 code that you build by using Agent Development Kit (ADK) .

 Model Armor :
 A managed security service that inspects and filters malicious prompts
 and responses. It protects the tenant's agent and compute resources
 from threats like prompt injection attacks.

 Model Context Protocol (MCP) servers: 
 MCP server facilitates access between the tenant agent
 and tenant datastore.

 Tenant datastore : A dedicated data repository, such as
 BigQuery or
 AlloyDB for PostgreSQL , that
 stores specific business unit data. The agent performs

 retrieval-augmented generation (RAG) 
 to generate more accurate responses based on the context in the
 datastore. To maintain strict data sovereignty, only the tenant agents
 can access this data.

 Gemini models : For inference serving, the agents
 in this example architecture use the latest Gemini
 model on Gemini Enterprise Agent Platform .

### Agentic flow

The example multi-tenant system in the preceding architecture has the following
flow: 

 A user's request is routed through an external Application Load Balancer. Within the routing hub,
these checks are completed to help ensure that only authenticated and safe
traffic reaches the frontend portal:

 Cloud Armor applies security policies to absorb any initial Layer
4 network protocol-based
 distributed denial-of-service (DDoS) attacks .
Cloud Armor inspects the request and filters malicious traffic,
such as SQL injection (SQLi), cross-site scripting (XSS), and known bot
signatures. 
 Model Armor intercepts the payload to detect and reject
prompt injection attacks or malicious intent. 
 If any of these layers detect a threat or unauthorized access, then the
load balancer drops the request at the network edge. 
 If the security layers detect no threat and they validate the user's access,
then the load balancer routes the traffic to the backend service. 

 If the request passes all checks, the load balancer routes the request to the
frontend platform, which performs the following actions:

 Extracts the user's identity, such as the user's business unit or tenant
ID. 
 Uses IAP to verify the user's corporate identity and device
health. 
 Uses a dynamically maintained registry to identify the correct target
tenant. 

 The frontend portal routes the request to the tenant. To ensure that the
agent can't access other tenant projects or unauthorized Google Cloud
services, Agent Runtime uses a
PAB Policy to limit the resources that the agent can access. 
 Model Armor uses
 Sensitive Data Protection 
to inspect and dynamically mask any personally identifiable information (PII)
or restricted content. Model Armor performs an additional
check for malicious prompt injections from the request to ensure that the
agent only processes safe data. 

Gemini performs the following tasks to generate a response: 

 Performs an initial reasoning pass to understand the user's intent. 
 If Gemini determines that it lacks specific facts, then it
generates a plan to call the tenant's specific data tools:

 To verify whether a user has permission to access the data resources,
the agent verifies the user's identity and IAM role
bindings. 
 To retrieve context, the agent executes a tool call through the MCP
server to the tenant datastore. 
 The agent creates a
 grounded 
response by combining its internal logic with the newly retrieved,
tenant-specific facts. 

If Gemini doesn't need additional facts, then it generates a
response and sends the response to Model Armor. 

Model Armor inspects and dynamically masks any PII or
restricted content and sends the sanitized response to the tenant agent. This
final inspection helps to ensure that no sensitive data leaks in the output. 

The response is routed back to the user, from the tenant agent through the
frontend platform and then through the load balancer. 

### Products used

This reference architecture uses the following Google Cloud and
open-source products and tools, chosen for their serverless nature, scalability,
and security features: 

VPC Service Controls : A managed networking functionality that minimizes data
exfiltration risks for your Google Cloud resources. 

Cloud Load Balancing : A portfolio of high performance, scalable, global and
regional load balancers.

Google Cloud Armor : A network security service that offers web application
firewall (WAF) rules and helps to protect against DDoS and application attacks.

Model Armor : A service that provides protection for your generative and agentic AI
resources against prompt injection, sensitive data leaks, and harmful content. 

Identity-Aware Proxy (IAP) : A service that enables a zero-trust access model for your
applications and virtual machines.

Identity and Access Management (IAM) : A system that lets you create and manage
permissions for Google Cloud resources. 

Cloud Run : A serverless compute platform that lets you run
containers directly on top of Google's scalable infrastructure. 

Gemini Enterprise Agent Platform : A comprehensive platform that
lets you build, scale, govern, and optimize enterprise‑grade AI agents.

Gemini : A family of multimodal AI models developed by Google.

Model Context Protocol (MCP) : An open-source standard for connecting AI applications to external
systems. 

Cloud Logging : A real-time log management system with storage, search,
analysis, and alerting. 

### Use case

Multi-tenant agentic AI systems are suitable for enterprise organizations that
want to scale generative AI deployments beyond a single application. To identify
use cases that this architecture is suitable for, analyze your business
processes and identify different teams that require their own specialized AI
agents that access unique tools and sensitive data. This approach helps you
empower decentralized teams with autonomous AI capabilities while you maintain
unified security and corporate compliance. 

The following is an example use case for a multi-tenant agentic AI system. 

### Enterprise-wide customer service

You can adapt this reference architecture to provide AI-powered customer service
across distinct business divisions. For example, to support an electronics
division and a home goods division, you deploy an electronics agent and a home
goods agent as two separate agents in separate tenant projects. These
specialized AI agents act as intelligent assistants that handle
division-specific support inquiries by accessing unique technical
specifications, warranties, or return policies. This automation lets human
support teams focus on more complex customer escalations. 

For this use case, the architecture provides the following benefits: 

 Strict data isolation : The multi-tenant design ensures that the support
knowledge for each division is strictly isolated. PAB Policy
provides guardrails that help ensure that an agent identity in one tenant can't
access data in another tenant. 
 Specialized agent knowledge : Because each agent resides in an isolated
tenant project, the agent only retrieves context from its division-specific
datastore. This targeted retrieval ensures high accuracy and prevents the
agent from confusing the policies of different business units. 
 Reduced cross-domain risk : The architecture helps to eliminate the risk of
data exposure between business units. Even if an agent identity is
compromised, the agent can't access unauthorized Google Cloud resources. 

This architecture is ideal for large retail organizations and enterprises that
manage multiple distinct brands or business units and that require strict data
sovereignty. 

### Design alternatives

This section presents alternative design approaches that you can consider for
your multi-tenant agentic AI deployment in Google Cloud. 

### Private access deployment

In the architecture that this document describes, users access the multi-tenant
agentic AI system over the public internet through a centrally exposed
external Application Load Balancer. If your organization requires a system that remains inaccessible
from the public internet, then you can adapt the architecture to use one of the
following private access strategies. 

### Block traffic with edge security policies

To allow traffic only from your organization's verified corporate IP addresses,
you can configure Cloud Armor security policies to deny any other
traffic. This high-priority security rule blocks all of the unauthorized
requests at the network edge. For an additional layer of security, you can use
IAP to require a valid corporate identity session and you can
configure IAM permissions for all users. 

This approach lets you take advantage of
 Cloud Armor edge security policies 
to offload DDoS
mitigation and WAF filtering, such as SQLi and XSS, and it provides a zero-trust
experience. However, the frontend IP address of the external Application Load Balancer remains
public and it might not meet the compliance requirements of some organizations. 

### Route traffic through an internal Application Load Balancer

The architecture in this document uses an external Application Load Balancer, which provides robust
Cloud Armor policies, more advanced security features, and lower
operational complexity compared to internal load balancers. However, the use of
an external load balancer means that traffic traverses the public internet. 

To keep traffic entirely within the private Google network, you can use an
 internal Application Load Balancer . The
use of an internal Application Load Balancer supports IAP for identity verification.
A global external Application Load Balancer evaluates IAP policies at the edge layer.
By contrast, an internal Application Load Balancer evaluates policies at the internal network layer.
Because traffic never traverses the public internet, the use of an
internal Application Load Balancer helps you to meet strict data sovereignty and zero-public IP
address requirements. 

To maintain low latency and comply with regional data residency requirements,
deploy a regional internal Application Load Balancer in each primary region. With a
regional internal Application Load Balancer, you route traffic from on-premises environments over
 Cloud Interconnect 
or over Cloud VPN 
directly to the internal IP address of the load balancer. A
regional internal Application Load Balancer supports regional Cloud Armor for
internal WAF protection. However, compared to an external Application Load Balancer,
regional internal Application Load Balancers support a limited set of Cloud Armor security
policies, lack advanced security features, and increase operational complexity. 

To further minimize latency and to help ensure high availability to meet your
disaster recovery requirements, you can deploy a cross-region internal Application Load Balancer .
With a cross-region internal Application Load Balancer, you use Cloud DNS with
 geolocation routing
policies to resolve the
internal URL of the application to the cross-region internal Application Load Balancer in the
Google Cloud region that's closest to the user. However, a cross-regional
configuration doesn't support any Cloud Armor integration. 

### Compute infrastructure

To prioritize a serverless-first approach that provides easier management and
lower operational overhead, the architecture in this document uses
Cloud Run for its compute infrastructure. You can also run
 containerized 
applications on
 GKE clusters .
Google Kubernetes Engine (GKE) is a container orchestration engine that automates
the deployment, scaling, and management of containerized applications.
GKE fully supports both internal and external
Application Load Balancers. For information about how to choose a compute
service for your workloads on Google Cloud, see Hosting Applications on
Google Cloud . 

### Model Context Protocol (MCP) servers

To enable the components of your agentic system to interact, you need to
establish clear communication protocols.
 MCP is an open protocol that
provides a standardized interface for agents to access and use necessary tools,
data, and other services. 

To connect your tenant agents to your datastore, consider your application
requirements to choose from the following MCP server deployment options. When
you choose between local and shared MCP deployments, consider the trade-offs
between data isolation and operational efficiency. 

 Local MCP server : A local MCP server, or a tenant-specific MCP server, is
an MCP server that you deploy within each tenant project and that provides
agents access to datastores and tools that are specific to that business
unit. 

The following are key features and considerations for local MCP servers: 

 Network : A project-level VPC Service Controls perimeter and
PAB Policy provide inherent security and isolation, which
helps to ensure no cross-tenant access. 
 Management : Individual developer and operations teams manage tenant
projects independently. This isolation provides autonomy for each business
unit. 
 Security : The fixed IAM boundaries of the tenant project
help minimize lateral risk surfaces and they don't require complex identity
mappings. 

Local MCP servers offer maximum isolation and they can handle highly sensitive
or regulated data access. However, if you deploy multiple local MCP servers,
then you increase your operational load. We recommend local MCP servers for
applications that require restrictive access to datastores that might contain
sensitive information. 

 Shared MCP server : A shared MCP server, or a global MCP server, is an MCP
server that you deploy in a shared services project. Shared MCP servers
provide access to tools and systems that are common across multiple tenants. 

The following are key features and considerations for shared MCP servers: 

 Network : To ensure that traffic doesn't traverse the public internet,
shared MCP servers require private connectivity, such as
 Private Service Connect or
 VPC Network Peering . 
 Management : A centralized operations team manages the implementation for
the entire system. This consolidated management optimizes operational
efficiency and removes the requirement to duplicate local implementations
across multiple tenants. 
 Security : You securely propagate the end-user identity from the agent in
the tenant project to the shared MCP server. To help ensure that users can
only access or modify data that they're permitted to, the shared MCP server
uses the propagated user identity to enforce fine-grained access control on
the backend system. 

Shared MCP servers centralize management for common tools, which reduces
duplication and optimizes operational efficiency. Although shared MCP servers
reduce management overhead, they require robust identity propagation and
authorization logic to maintain secure access. We recommend shared MCP servers
for interactions with common corporate systems and tools, such as expense
reporting tools, human resources (HR) systems, corporate-wide knowledge bases,
or attendance managers. 

In this architecture, you use MCP servers to standardize the connection between
your tenant agents and your datastores. Depending on your workload
requirements, you might use other types of agent tools to connect your agents
with specific external APIs and systems. For more information about agent tool
interactions, see
 Agent tools . 

### Design considerations

The following sections describe design factors, best practices, and
recommendations to consider when you use this reference architecture to develop
a topology that meets your specific requirements for security, reliability,
cost, and performance. The guidance in this section isn't exhaustive. Depending
on your workload's requirements and the products and features that you use,
there might be additional design factors and trade-offs that you should
consider. 

### Security, privacy, and compliance

This section describes design considerations and recommendations to design a
topology in Google Cloud that meets your workload's security, privacy, and
compliance requirements. 

 Component 
 Design considerations and recommendations 

 Virtual Private Cloud (VPC) 
 Tenant isolation : In this architecture, you deploy
 each tenant in a dedicated Google Cloud project. To create a strict
 security boundary, combine tenant project-level isolation with
 PAB Policy and VPC Service Controls at
 the organization level. 

 IAM Access control : To implement the principle
 of least privilege , use a persona-based access model. For example, you
 can define custom IAM roles to ensure that a developer who
 builds an agent in one tenant can't access data in another tenant. 

 Cloud Armor 

 Edge and internal WAF protection :
 Cloud Armor provides security and WAF protection to defend the
 frontend portal against DDoS attacks and web vulnerabilities. A
 global external Application Load Balancer supports the full suite of advanced edge features,
 such as bot management and Google Cloud Armor Adaptive Protection . 

If you deploy a regional internal Application Load Balancer, then Cloud Armor
 operates with a restricted set of standard WAF policies. The restricted set
 of policies are tailored for internal network boundaries and it includes
 policies like SQLi and XSS protection. For more information, see Integrating Cloud Armor
 with other Google products . 

 Agent Platform 

 Shared model
 endpoints : To prevent abuse and ensure fair usage for shared model
 endpoints, implement one of the following strategies: 

 Tenant-level rate
 limiting : Enforce quotas in the frontend portal for each tenant before
 requests reach the shared endpoint. Enforce the quotas by doing the
 following:

 Extract the tenant identity from the IAP
 context. 
 Track usage against predefined limits for each tenant
 by using an external store like 
 Memorystore for Redis . 
 Reject requests from tenants that exceed their
 limits. 

 API Gateway : To enforce per-tenant quotas by using API
 keys and usage plans, implement API Gateway before
 the shared endpoint.

 Cloud Run 

 Content rendering : To enhance
 the security posture of the frontend portal, prioritize server-side
 rendering (SSR) over client-side
 rendering (CSR) . Compared to CSR, SSR offers these benefits: 

 Executes application logic and manages secrets
 within a controlled Google Cloud environment.
 Reduces the
 client-side attack surface and prevents sensitive data leaks to the user's
 untrusted browser. 
 Limits data exposure by sending only the necessary
 HTML to the client. 
 Provides centralized output encoding to defend
 against cross-site scripting (XSS) attacks. 

 Security Command Center Centralized security monitoring : To
 monitor for threats and enforce security policies such as multi-factor
 authentication (MFA) and data encryption, use the tools in the Security Command Center .

### More security recommendations

 Google Cloud Well-Architected Framework AI and ML perspective: Security 
 Google's Approach for Secure AI Agents: An Introduction 

### Reliability

This section describes design considerations and recommendations to build and
operate reliable infrastructure for your deployment in Google Cloud. 

 Component 
 Design considerations and recommendations 

 Cloud Load Balancing 
 Global routing : A global external Application Load Balancer provides a single Anycast IP address that
 automatically routes user traffic to the closest geographical Google edge.
 This configuration reduces latency through edge Secure Sockets Layer
 (SSL) termination. It also ensures high availability if a region
 experiences an outage because it intelligently reroutes traffic to healthy
 regional backends. 

 Tenant 
 Fault tolerance : To tolerate or handle agent-level failures,
 deploy agents in isolated tenant projects. This isolation helps to ensure
 that operational issues or security incidents stay within a single business
 unit and don't affect other resources or business units. 

 Agent Platform 
 Capacity planning : If the number of requests to the model exceeds
 the allocated capacity, then the model returns error
 code 429 . For workloads that are business critical and that require
 consistently high throughput, you can reserve throughput by using Provisioned Throughput . 

 Agent Runtime 

 Serverless scalability : Agents that are deployed on
 Agent Runtime scale independently based on
 demand. A sudden spike in usage in one tenant doesn't exhaust the compute
 resources or affect the availability of an agent in another tenant project.

 Error handling : To handle transient errors like error code 429
 rate limits, the agent orchestration logic uses exponential
 backoff . If a context deadline is exceeded, then the agent performs a graceful shutdown and
 it reports partial progress back to the user. For example, a context deadline
 can be exceeded due to slow tool calls, third-party API latency, processing
 massive datasets, or compute-intensive processing.

For reliability principles and recommendations that are specific to AI and ML workloads, see
 AI and ML perspective: Reliability 
in the Well-Architected Framework.

### Operational efficiency

This section describes the factors to consider when you use this reference
architecture to design a Google Cloud topology that you can operate
efficiently. 

 Component 
 Design considerations and recommendations 

 Google Cloud Observability 
 Centralized monitoring : Logging and
 Monitoring let you monitor the health and performance of the entire
 platform. You can set up alerts to proactively detect and troubleshoot
 issues without allowing access to sensitive data. 

 All of the products in the architecture 
 Standardized deployments : Using
 Agent Platform within a standardized tenant
 architecture pattern lets you establish a consistent baseline when you
 onboard new tenants. To reduce operational burden, automate the deployment
 process by using Infrastructure
 as Code (IaC) tools like Terraform. For Terraform code that you can use
 to build and deploy a multi-tenant agentic AI system, see the Deployment section of this document. 

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

 Token
 consumption : To manage costs and prevent your AI model from exceeding
 context windows, use the following strategies to manage context for the AI
 model: 

 Context summarization : Instead of saving an entire session
 conversation as context, use an AI model to summarize older conversation
 and less critical information. 
 Prune outputs :
 Identify and remove less relevant or verbose parts of tool outputs or
 retrieved context. For example, if you only need the column names from
 your data, you can remove excessive metadata from a database schema fetch.
 This strategy requires custom logic that uses heuristics, filtering, or a
 small language model (SLM) to extract the most important information. 
 Maximum token limit : To help prevent infinite loops and to help
 control costs, enforce a session maximum token limit. 

 Model endpoints : To manage API
 quotas and resource utilization, you can deploy
 Agent Platform endpoints in either a
 dedicated configuration or a shared configuration: 

 Dedicated endpoints : When you deploy endpoints within each
 tenant project, you provide inherent quota isolation. Each tenant's usage
 counts against its own project quotas, which prevents inter-tenant impact.
 Compared to shared endpoints, dedicated endpoints offer simpler quota
 management. However, dedicated endpoints prevent you from taking advantage
 of the potential cost savings of a shared endpoint. 
 Shared
 endpoints : To optimize costs, you can host a shared endpoint in the
 central governance and security hub. Because all of the tenants share the same
 pool of quotas, to prevent malicious attacks, you must implement
 mitigation strategies such as tenant-level rate limiting or quota
 enforcement with API Gateway. Compared to dedicated
 endpoints, shared endpoints are more cost-effective. However, shared
 endpoints require additional engineering effort and they can introduce
 latency and management overhead. 

For information about costs on
 Agent Platform, see Cost
 of building and deploying AI models in
 Agent Platform . 

 Cloud Run 
 Instrumentation : Instrumentation lets you monitor performance,
 troubleshoot issues, and track resource usage for each tenant. To identify
 the tenant for each request, extract the user identity from the context that
 IAP provides. For information about how to instrument your
 application, see Choose an
 instrumentation approach . 

 Model Armor 
 Centralized prompt filtering : To enforce strict governance and a
 zero-trust posture, this architecture deploys Model Armor at
 two layers: in the routing hub and within each tenant project. Although this
 two-layered approach helps to ensure data sovereignty, it increases latency
 and operational costs. To reduce costs and system complexity, filter all of
 the prompts and responses by deploying Model Armor
 exclusively in the routing hub. 

 All of the products in the architecture 

 Shared infrastructure : Shared core infrastructure components, such
 as the frontend portal, the central governance and security hub, and
 Agent Platform, can reduce costs compared to
 when you build a separate, custom stack for each agent. 

 Platform
 overhead : To distribute the shared costs of the central governance
 and security hub, use an allocation model that fits your tracking
 capabilities and usage patterns. We recommend that you use one of the
 following cost allocation models: 

 Even split allocation : An even split
 model allocates shared costs equally across all of the tenants. Use this
 model when the platform is a baseline utility or when the overhead of
 granular tracking outweighs the cost benefits. 
 Proportional allocation : A proportional model, or chargeback
 process , allocates shared costs based on the proportion of direct costs
 that each tenant incurs. Use this model when tenant consumption varies
 drastically and you have robust telemetry, such as Resource Manager labels and log parsing, to
 attribute costs accurately. 
 Fixed allocation : A fixed, or
 tiered, model allocates shared costs based on business-defined coefficients.
 Use this model when tenants require different service-level agreements
 (SLAs). A fixed model allocation lets you charge fixed rates for premium
 dedicated capabilities versus standard shared capabilities. 

For more information about how to allocate shared services costs, see Cloud
 FinOps: Shared services cost allocation . 

 Centralized cost
 management : To accurately track the total cost of ownership (TCO) of your
 agentic AI system and attribute costs to individual business units, use
 labels and Cloud Billing export data. For more information about how to
 use labels for cost awareness, see Foster
 a culture of cost awareness . 

To estimate the cost of your Google Cloud resources, use the
 Google Cloud Pricing Calculator . 

For cost optimization principles and recommendations that are specific to AI and ML workloads, see
 AI and ML perspective: Cost optimization 
in the Well-Architected Framework.

### Deployment

To deploy this reference architecture, use the
 multi-tenant agentic AI Terraform 
example that's available in GitHub. 

### What's next

 Learn more about how to
 build an agent with ADK and Agents CLI in Agent Platform . 
 Learn how to
 use the Agent Platform remote MCP server . 
 Learn about
 best practices for enabling VPC Service Controls . 
 Learn how to
 manage deployed agents on Agent Runtime. 
 Learn about
 best practices for scaling and high traffic . 
 To implement just-in-time elevation strategies, explore how to use
 Privileged Access Manager . 

For an overview of architectural principles and recommendations that are specific to AI
and ML workloads in Google Cloud, see the
 AI and ML perspective 
in the Well-Architected Framework.

For more reference architectures, diagrams, and best practices, explore the
 Cloud Architecture Center .

### Contributors

Authors:
 Shivank Awasthi | Field Solutions Architect Utkarsh Bhardwaj | Technical Solutions Consultant, Agentic AI, Apps, Cloud Platforms, and Infrastructure 

Other contributors:
 Adrian Corona | Manager, Global Services Delivery, Security Agnieszka Kołkiewicz | GSD AI Manager Anmol Sachdeva | Ads Solutions Engineer, Global Business Ashish Agarwal | EMEA North lead, Global Services Delivery Ashmita Kapoor | JAPAC GenAI FSA, and Applied AI CE Manager Ashutosh Gupta | Director, Global Service Delivery Aspen Sherrill | Cloud Security Architect Chinmay Deshpande | Cloud Migration Consultant, Infrastructure Gaurav Taneja | EMEA South Infra, Data, AI, and GDC Delivery Lead Ishmeet Mehta | NorthAm Platform Specialist, Apps CE Joanna Nowek | AI Transformation Consultant Kumar Dhanagopal | Cross-Product Solution Developer Mark Schlagenhauf | Technical Writer, Networking Matthias Ziener | Manager, Global Service Delivery Olu Akinrolabu | Security Cloud Consultant Paweł Tokarski | EMEA South Infra, Data, AI, and GDC Delivery Lead Paweł Glica | Core EMEA Practise Lead Prabha Arya | Strategic Cloud Engineer Samantha He | Technical Writer Suchit Puri | Global AI Practice Lead Thomas Cliett | Director of delta AI Valentín Huerta | AI Engineer 

Was this helpful? 

 Send feedback

Except as otherwise noted, the content of this page is licensed under the Creative Commons Attribution 4.0 License , and code samples are licensed under the Apache 2.0 License . For details, see the Google Developers Site Policies . Java is a registered trademark of Oracle and/or its affiliates. 

Last updated 2026-06-18 UTC. 

 Need to tell us more?

 [[["Easy to understand","easyToUnderstand","thumb-up"],["Solved my problem","solvedMyProblem","thumb-up"],["Other","otherUp","thumb-up"]],[["Hard to understand","hardToUnderstand","thumb-down"],["Incorrect information or sample code","incorrectInformationOrSampleCode","thumb-down"],["Missing the information/samples I need","missingTheInformationSamplesINeed","thumb-down"],["Other","otherDown","thumb-down"]],["Last updated 2026-06-18 UTC."],[],[]]

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

 Español – América Latina 

 Français 

 Indonesia 

 Italiano 

 Português – Brasil 

 עברית 

 中文 – 简体 

 中文 – 繁體 

 日本語 

 한국어