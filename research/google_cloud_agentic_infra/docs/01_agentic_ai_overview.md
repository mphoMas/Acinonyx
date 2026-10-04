# Overview of Agentic AI on Google Cloud

**Source URL:** https://docs.cloud.google.com/architecture/agentic-ai-overview

---

Agentic AI architecture guides  |  Cloud Architecture Center  |  Google Cloud Documentation 

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
 " track-metadata-eventdetail="nav" track-type="freeTrial" referrerpolicy="no-referrer-when-downgrade" track-name="gcpCta" track-metadata-position="nav">Start free 

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
 Agentic AI architecture guides 

 Stay organized with collections

 Save and categorize content based on your preferences. 

 <div class="devsite-article-body clearfix
 ">

Last reviewed 2025-11-25 UTC 

This document in the Architecture Center provides links to architecture guides
that you can use to build and deploy agentic AI applications in Google Cloud. 

 Architecture guide 
 Description 

 Administer interactive learning 

A high-level architecture to design a single-agent AI system that
 assesses a user's knowledge on a specific topic and generates a
 personalized learning experience. 

 Automate data
 science workflows 

A high-level architecture to design a multi-agent AI system that
 automates complex data analytics and machine learning tasks. 

 Build a borderless open data lakehouse 

A high-level architecture to build a borderless open data lakehouse
 that establishes a highly governed, secure pipeline from raw borderless
 silos to AI and agentic driven actions. 

 Build
 a trusted agentic system with Google Maps Platform 

A high-level architecture to build trustworthy and effective AI
 agents by grounding them in real-world maps and calendar data. 

 Classify multimodal data 

A high-level architecture to design a multi-agent AI system that
 analyzes disparate multimodal data and produces a high-confidence
 classification. 

 Guide technical workflows with
 bidirectional multimodal streaming 

A high-level architecture to build and deploy a multi-agent AI system
 that provides technical guidance and automated safety monitoring through
 a continuous, bidirectional stream of multimodal data. 

 Implement
 agentic analytics workflows for distributed data 

A high-level architecture for implementing cross-cloud analytics
 workflows that use AI agents. 

 Multimodal GraphRAG resource orchestration 

A high-level architecture to build and deploy a multi-agent AI system that
consolidates fragmented multimodal data into a searchable knowledge graph. 

 Orchestrate access to disparate
 enterprise systems 

A high-level architecture to design an agentic AI system that
 orchestrates interactions with disparate enterprise systems. 

 Orchestrate security operations workflows 

A high-level architecture to build a multi-agent AI system that
 orchestrates complex investigation and triage processes in a security
 operations center (SOC). 

 Choose a design pattern for your agentic
 AI system 

A design guide to help you choose a design pattern for your agentic
 AI system. 

 Choose your agentic AI architecture
 components 

A design guide to help you choose architectural components for your
 agentic AI applications in Google Cloud. 

 Multi-agent AI
 system 

A reference architecture to help you design a robust multi-agent AI
 system in Google Cloud. 

 Multi-tenant agentic AI system 

A reference architecture to help you design a robust multi-tenant
 agentic AI system in Google Cloud. 

 Single-agent AI system using
 ADK and Cloud Run 

A reference architecture to help you design a single-agent AI system
 by using Agent Development Kit (ADK) and Cloud Run with
 Gemini and Model Context Protocol (MCP). 

Was this helpful? 

 Send feedback

Except as otherwise noted, the content of this page is licensed under the Creative Commons Attribution 4.0 License , and code samples are licensed under the Apache 2.0 License . For details, see the Google Developers Site Policies . Java is a registered trademark of Oracle and/or its affiliates. 

Last updated 2025-11-25 UTC. 

 Need to tell us more?

 [[["Easy to understand","easyToUnderstand","thumb-up"],["Solved my problem","solvedMyProblem","thumb-up"],["Other","otherUp","thumb-up"]],[["Hard to understand","hardToUnderstand","thumb-down"],["Incorrect information or sample code","incorrectInformationOrSampleCode","thumb-down"],["Missing the information/samples I need","missingTheInformationSamplesINeed","thumb-down"],["Other","otherDown","thumb-down"]],["Last updated 2025-11-25 UTC."],[],[]]

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