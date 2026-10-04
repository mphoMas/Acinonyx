# Multi-Agent Private Networking Patterns

**Source URL:** https://docs.cloud.google.com/architecture/multi-agent-private-networking-patterns

---

Multi-agent private networking patterns in Google Cloud  |  Cloud Architecture Center  |  Google Cloud Documentation 

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
 " track-type="freeTrial" track-metadata-position="nav" referrerpolicy="no-referrer-when-downgrade" track-metadata-eventdetail="nav" track-name="gcpCta">Start free 

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

 On this page Multi-agent design pattern Shared VPC Gemini Enterprise networking User chat to Gemini Enterprise apps Gemini Enterprise apps to custom agents Private networking for agent hosting platforms Agent Runtime networking Cloud Run networking GKE networking Agent network security Cloud NGFW IAP VPC Service Controls Model Armor Cloud Armor Secure Web Proxy CA Service A2A connection security MCP connection security What's next Contributors 

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
 Multi-agent private networking patterns in Google Cloud 

 Stay organized with collections

 Save and categorize content based on your preferences. 

 On this page Multi-agent design pattern Shared VPC Gemini Enterprise networking User chat to Gemini Enterprise apps Gemini Enterprise apps to custom agents Private networking for agent hosting platforms Agent Runtime networking Cloud Run networking GKE networking Agent network security Cloud NGFW IAP VPC Service Controls Model Armor Cloud Armor Secure Web Proxy CA Service A2A connection security MCP connection security What's next Contributors 

 <div class="devsite-article-body clearfix
 ">

Last reviewed 2026-04-16 UTC 

This document provides guidance to help you design private networking
infrastructure that supports a publicly accessible, multi-agent,
 Gemini Enterprise app with private connections between agents,
subagents, and tools. The network design provides private connections for agents
that are hosted in Agent Runtime on Gemini Enterprise Agent Platform, Cloud Run, Google Kubernetes Engine (GKE),
on-premises data centers, or in other clouds. The design also supports
connectivity to agents that run in internet locations. 

Multi-agent AI systems often involve organizationally sensitive or proprietary
data. Private networking lets you avoid exposing this traffic to the public
internet. This design uses Google Cloud network infrastructure,
Virtual Private Cloud (VPC) network resources, and private connectivity to
on-premises environments or cross-cloud networks. 

In the design that this document describes, agents communicate with other agents
and with tools by using the Agent2Agent (A2A) protocol and the Model Context
Protocol (MCP). Communications are made private by routing them through a
VPC network. To move traffic into and out of the
VPC network, this design uses a combination of
Private Service Connect endpoints,
Private Service Connect interfaces, and Cloud Run
Direct VPC egress. Cloud Next Generation Firewall (Cloud NGFW)
governs traffic that passes through the VPC network. Additional
security layers provide controlled internet egress by using Secure Web Proxy and
provide API service access policies by using a VPC Service Controls perimeter. 

The intended audience for this document includes architects, developers, and
administrators who build and manage cloud AI infrastructure and apps. This
document assumes that you have a foundational understanding of AI agents and
models and that you're familiar with Google Cloud networking concepts. 

### Multi-agent design pattern

A multi-agent Gemini Enterprise app requires a custom agent to
serve as an orchestrator or root agent for connections to tools and subagents.
To implement private connections to tools and subagents that are hosted in
Google Cloud or on-premises, the design uses a VPC network
with private IP addresses. The root agent is hosted within Google's
infrastructure, using Agent Engine, Cloud Run, or
GKE. The multi-agent design pattern highlights these
interactions: 

 Gemini Enterprise app interacting with custom root agents . 
Gemini Enterprise
apps present a managed user
interface with built-in security functions that expose custom agent
functionality. Custom-built root agents are registered with
Gemini Enterprise and they're made available in apps to end
users. The custom root agent acts as a top-level workflow orchestrator and
it delegates specialized tasks to subagents. This architecture uses custom
root agents that are hosted on Agent Runtime on Gemini Enterprise Agent Platform,
Cloud Run, or GKE. 
 Root agents interacting with subagents and tools . The core of the AI
system workflow and business logic resides in the root agent and in
specialized subagents. The flexibility in the agent framework, runtime, and
hosting platform allows for different options to connect root agents to
subagents and tools through the VPC network. By using
VPC networking for this part of the architecture, agents can
use private networking paths that you define that expose other private
endpoints, enterprise security controls, and broader network reachability. 

The architecture includes the following components: 

 Gemini Enterprise app : The frontend for users to access an in-app chat
interface and interact with the multi-agent AI system. Users can access
Gemini Enterprise apps through the public internet or
privately through hybrid connections. 
 Custom agents : Root agents that are built and registered with
Gemini Enterprise and that are hosted on
Agent Runtime, Cloud Run, or
GKE. These root agents function as orchestrators that
delegate tasks to subagents. 
 VPC network : A resource that you control to provide
agents with IP network connectivity to private endpoints and broader network
reachability. The VPC network provides a platform to
implement private connectivity and network security controls for agent
requests to other agents and tools. 
 Subagents : Specialized agents that are triggered by the root agent
workflow. Subagents communicate using the A2A protocol, which enables
interoperability between agents regardless of programming language and
runtime. 
 Tools : Remote systems that expose services such as APIs, data sources,
and workflow functions. These tools fetch data and perform actions or
transactions for agents. Tools are external to agents, and agents connect
and interact with tools by using the MCP specification. 

This high-level multi-agent design pattern highlights the networking components
that are in a multi-agent AI system. It can support many different types of
agent-to-agent routing patterns. For information about other AI system design
patterns, see Choose a design pattern for your agentic AI
system . 

### Shared VPC

The multi-agent design pattern uses Shared VPC to centralize networking
and security authority and responsibility. This design provides developers with
environments that help fulfill an organization's security needs. We recommend
that you use Shared VPC to centralize to simplify your network and
security configurations. 

In a Shared VPC architecture, a host project 
contains the shared network resources, including VPC networks,
Cloud Routers, subnets, firewalls, and Cloud DNS. Administrators can grant
 service projects access to use these resources. Service projects contain the
agent runtime resources, including Agent Runtime,
Cloud Run, GKE, Gemini Enterprise,
and app-specific load balancers. 

Shared VPC enforces a clear boundary between network and security
administrator personas and AI app developer personas: 

 Network and security administrators control the core infrastructure,
such as VPC routing, subnets, DNS peering, and firewall
policies. 
 AI app developers build agents in attached service projects without
having permissions to modify the underlying network infrastructure. 

When you centralize network and security deployments within a host project, you
create a single point of management for agent-to-agent and agent-to-service
communication. This design simplifies the enforcement of security policies
across many different service projects while ensuring consistent connectivity. 

You can incorporate your Shared VPC network into a 
Cross-Cloud Network by
using Network Connectivity Center (NCC) VPC spokes to add the
Shared VPC network as a workload VPC network. This
implementation provides the Shared VPC with full reachability to
NCC hub routes and with connectivity to service access points
from other spokes. 

Requests that are initiated from custom root agents use a private,
customer-managed VPC network to provide secure network paths to
subagents, tools, and services. VPC network routing governs
reachability to private endpoints. Cloud NGFW policies that are
applied to the VPC network govern network access. 

Agents gain secure access to private VPC network paths, including
connectivity to the following: 

 Other VPC networks through VPC network
peering, multi-NIC appliances, or NCC. 
 Private Service Connect endpoints for accessing producer
services. 
 Managed services that have private IP addresses, such as Cloud SQL. 
 Internal load balancer front ends and Compute Engine resources. 
 Google APIs through Private Google Access or through
Private Service Connect. 
 The internet, controlled through Secure Web Proxy. 
 Hybrid and cross-cloud destinations by using Cloud Interconnect,
Cloud VPN, router appliance, or SD-WAN. 
 Any endpoint destination that's reachable through VPC network
IP routing. 
 Other AI agents, tools, and supporting services. 

For more information about Shared VPC, see these resources: 

 Best practices and reference architectures for VPC design 
 Google Cloud Setup guided flow 
 Cross-Cloud Network inter-VPC connectivity
using
NCC 

### Gemini Enterprise networking

Gemini Enterprise apps are managed resources that operate in a
hosted environment outside of the VPC network, but within
Google's network. The following sections describe configuration for networking
between the user and the Gemini Enterprise app and describe
networking between the app and the agents. 

### User chat to Gemini Enterprise apps

Users chat with the Gemini Enterprise app by using a
browser-based app that sends requests to Google APIs and services. To enable
private user connectivity, you can configure the Google API URLs to resolve to
private IP address ranges that are routed over your VPC network.
For more information, see Configure private UI
access . 

### Gemini Enterprise apps to custom agents

You register custom agents with the Gemini Enterprise discovery
service. When you register an agent, Gemini Enterprise maps the name of
the agent to a specific target, either the 
Agent Runtime resource
URI 
or the A2A agent
URL .
Gemini Enterprise apps have a built-in chat interface that's
called the assistant . When a user
specifies an agent by using @agent_name , or when the assistant decides to
delegate, the app looks up the agent in the registry to find the associated
endpoint. 

When you register a root agent with Gemini Enterprise, you can
deploy that agent anywhere as a custom agent. Custom agents on
Agent Runtime and on Cloud Run can use
existing private network paths without configuring additional networking
resources. In order to deploy a custom agent on GKE, you must
expose the service with an external
Gateway .
For information about how to configure the external Gateway to be more secure,
see GKE networking later in this document. 

To make requests to custom agents, Gemini Enterprise uses the
Gemini Enterprise Agent Platform Discovery Engine Service
Account identity.
The network path and authorization mechanisms differ based on the hosting
platform that you use: 

 Custom agents on Agent Runtime : The
Agent Platform Discovery Engine service agent
includes the necessary Agent Platform Identity and Access Management (IAM)
roles to invoke Agent Runtime resources as a
built-in feature. The system routes requests that are made to the
Agent Platform API service over the Google network as an internal API call. 
 Custom agents on Cloud Run :
Gemini Enterprise apps use the Agent Platform
Discovery Engine service agent identity to make calls to the
stable run.app URL that's registered from the agent card. In order for the
AI agent Cloud Run service to authorize these calls, you must
grant the Cloud Run Invoker IAM role ( roles/run.invoker ) to
the Discovery Engine Service Agent. Requests to
Cloud Run are routed over the Google production network to
the Google Front End (GFE) for
Cloud Run ingress. 

 Custom agents on GKE : Gemini Enterprise apps use the
Agent Platform Discovery Engine service agent
identity to make calls to the URL that's registered from the agent card.
Public DNS must be able to resolve the hostname to an external IP address
that's managed by the Gateway. We recommend that you use the
 gke-l7-regional-external-managed load
balancer or the
 gke-l7-global-external-managed load balancer. For added security, we
recommend that Gemini Enterprise calls a GKE
hosted A2A agent by using Identity-Aware Proxy (IAP).
In order for IAP to authorize these calls, you must grant the
IAP-secured Web App User IAM role
( roles/iap.httpsResourceAccessor ) to the Discovery Engine
service agent. The Google production network routes requests to
GKE to the GFE for external Application Load Balancer ingress. 

To secure GKE Ingress from Gemini Enterprise,
see the IAP and
 Google Cloud Armor sections later in this document. 

### Private networking for agent hosting platforms

After a user initiates a request to the Gemini Enterprise app,
requests are initiated from custom root agents to subagents and tools. The
custom agent hosting platforms provide the interface between
Gemini Enterprise and your VPC networks. The
hosting platforms for your containerized agents and tools are
Agent Runtime, Cloud Run, and
GKE. 

When you choose an agent hosting platform, you need to consider the private
networking patterns, security controls, management control, level of
customization, and security compliance of each platform. For more information
about how to select an AI agent hosting platform, see Choose models and
infrastructure for your generative AI
application and Choose your
agentic AI architecture
components . 

You establish private VPC connectivity through different
mechanisms based on the agent hosting platform that you use: 

 Custom agents on Agent Runtime :
Private Service Connect interfaces connect the
Agent Runtime runtimes to the VPC
network. You create a network
attachment 
in a subnet of your VPC network and give
Agent Runtime permission to attach to it. Traffic
that's sent from Agent Runtime appears in the
VPC network as if it originated at the subnet IP address of
the attachment. The VPC network then routes the traffic to
the appropriate destination IP address. 
 Custom agents on Cloud Run : Cloud Run
Direct VPC egress connects the Cloud Run
service instances to the VPC network. The VPC
network that's specified when a Cloud Run service is deployed
can be from the Cloud Run service project or from its
Shared VPC host project. Traffic that's sent from
Cloud Run appears in the VPC network as if it
originated at the subnet IP address of the Direct VPC egress.
The VPC network then routes the traffic to the appropriate
destination IP address. 
 Custom agents on GKE : GKE clusters reside directly in the
VPC network and they use local subnet IP addresses. By
default, GKE egress traffic uses the Pod IP address as the
source IP address. If you configure masquerading, GKE egress
traffic uses the node IP address as the source IP address. All
GKE egress traffic is routed by the VPC
network. 

The following sections provide additional guidance for managing ingress and
egress requests into and out of the VPC network for each agent
hosting platform. The network considerations are applicable to both root agent
and subagent functionality. 

### Agent Runtime networking

This section describes private networking for root agents and subagents that are
hosted on Agent Runtime. If you're using
Agent Runtime to host your root agent, you must deploy
Gemini Enterprise and Agent Runtime in
the same project. 

Agent Runtime hosts containers on Google infrastructure
outside of your VPC network. To enable private connectivity to
other agents, you can connect your agent to your VPC network by
using the following methods: 

 To allow Agent Runtime agent traffic to egress to
your VPC network, use Private Service Connect
interfaces . 
 To allow agent traffic that's routed through your VPC
 network to ingress to your Agent Runtime agent,
 use Private Service Connect endpoints for Google
 APIs . 

To allow requests between your agents and other agents, set up both of the
preceding connections. 

### Agent Runtime egress to the VPC network

Agent Runtime uses a Google-managed tenant project for
network egress. The tenant network provides connectivity for agents to Google
APIs and for public internet egress, but it isn't directly connected to customer
VPC networks
 by default . 

To connect agents to resources that are inside of your VPC
network, Agent Runtime uses 
Private Service Connect
interfaces .
Agent Runtime deploys a network interface in the tenant
project that connects to a network
attachment resource in your project. This
connection creates a secure data path between the
Agent Runtime runtime and the VPC
network. When you configure a Private Service Connect interface
in your Agent Runtime project, the system routes all of
the agent traffic that isn't destined for Google APIs to the VPC
network. 
 Note: Agent Runtime resources can access agents that are hosted in Agent Runtime and in Cloud Run directly over the Google production network without egressing to the VPC network. Agent Runtime has a private path to Google APIs and services that routes requests to the Agent Platform API for Agent Runtime and to .run.app URLs for Cloud Run. This traffic is subject to VPC Service Controls enforcement policies. For other security controls that are enforced by the VPC network, agent traffic must egress to the VPC network. To override default behavior and route Google API and Cloud Run service traffic to the VPC network, use private DNS peering . 

To deploy Agent Runtime VPC network
egress, see these resources: 

 Using Private Service Connect interface with
Agent Runtime . 
 Deploy an agent: Configure Private Service Connect
interface . 
 Set up a Private Service Connect interface for
Agent Platform resources: Set up a private DNS
peering . 
 Deploy an agent: Define environment variables 
 for explicit proxy. 

To further secure agents and the VPC network for
Agent Runtime egress, see these sections later in this
document: 

 Use Cloud NGFW policies and rules. 
 Configure VPC Service Controls protected resources. 
 Integrate Model Armor screening. 
 Deploy Secure Web Proxy for internet egress. 

### Agent Runtime ingress from the VPC network

Requests to agents that run on Agent Runtime are made by
using the Agent Platform API endpoint ( aiplatform.googleapis.com ). To
reach Google API endpoints by using private network paths from the
VPC network, use Private Google Access or use
 Private Service Connect endpoints
for Google APIs . 

Private users that make queries to agents need to resolve the
Agent Platform API endpoint hostname to the private IP address range for 
Private Google Access 
or to the IP address of the Private Service Connect endpoint for
Google
APIs . A
private managed Cloud DNS zone for
 googleapis.com 
resolves requests for the Agent Platform API. The VPC
network routes the request directly over the Google production network. 

If you use Private Google Access or
Private Service Connect for Google APIs, you can help protect
traffic from your VPC network to
Agent Runtime by using the following products and
features: 

 Agent Platform API authentication 
 VPC Service Controls 
 Model Armor 

### Additional Agent Runtime network considerations

Agent Runtime egress that uses
Private Service Connect interfaces can only route to RFC 1918 IP
address ranges in the VPC network. For specific destination
ranges that aren't routable by Agent Runtime egress, see
 Subnetwork IP range
requirements .
To reach non-routable IP address range destinations, use an explicit proxy
configuration on the agents and deploy proxy resources that use a routable IP
address in the VPC network. 

When Agent Runtime is deployed without a
Private Service Connect interface, it has access to the internet
by default. To protect against data exfiltration, disable the default access by
enabling VPC Service Controls. 

When Agent Runtime is deployed with a
Private Service Connect interface, direct internet egress is
disabled, regardless of VPC Service Controls. If you need your agent to access a
destination that Agent Runtime can't normally reach,
such as the internet, do the following: 

 Configure Secure Web Proxy in an
 RFC 1918 subnet
of your VPC network. You must configure the proxy in
 explicit proxy routing mode . 
 Create a Cloud DNS record for the Secure Web Proxy hostname. 
 Configure DNS peering 
for Agent Runtime to support agent DNS query
resolution to the private address of the Secure Web Proxy in the
VPC network. 
 When you deploy agents do the following:

 Define environment variables 
to use the explicit proxy by specifying the Secure Web Proxy hostname and
port. 
 If you're accessing a private destination, configure a private DNS zone
for that destination. 

After traffic from Agent Runtime egress reaches the
VPC network, it can reach any network destination that's routable
by the VPC network. For information about how to limit the scope
of egress network destinations that are available to
Agent Runtime agents, see the
 Cloud NGFW section later in this document. 

### Cloud Run networking

This section describes private networking for root agents and subagents that are
hosted on Cloud Run. Cloud Run hosts containers on
Google infrastructure outside of your VPC network. To enable
private connectivity to other agents, you can connect your agent to your
VPC network by using the following methods: 

 To allow Cloud Run agent traffic to egress to your
VPC network, use Direct VPC
egress . 
 To allow agent traffic that's routed through your VPC network
to ingress to your Cloud Run agent, use 
Private Service Connect endpoints for Google
APIs . 

To allow requests between your agents and other agents, set up both of the
preceding connections. 

### Cloud Run egress to the VPC network

To initiate Cloud Run connections into a VPC
network, we recommend that you use Direct VPC
egress . With Direct
VPC egress, Cloud Run instances connect directly
to the shared VPC network by using an IP address from the subnet
that you specify when you deploy Direct VPC egress. 

When you configure Direct VPC egress, do the following: 

 Configure the target subnet with Private Google Access 
enabled. 
 Configure traffic routing to route all traffic to the VPC
network . 

This configuration sends all traffic through the VPC network for
privacy and it sends requests from Cloud Run to other Google APIs
over the Google internal network. 

All of the DNS queries from
Cloud Run use the
Cloud DNS policy and zones that are associated with the
VPC network. No additional DNS peering configuration is required.
Agents that are hosted on Cloud Run resolve all of the
Cloud DNS private zones and public hostnames. 

For information about how to further secure agents and the VPC
network for Cloud Run egress, see these sections later in this
document: 

 Use Cloud NGFW policies and rules. 
 Configure VPC Service Controls protected resources. 
 Integrate Model Armor screening. 
 Deploy Secure Web Proxy for internet egress. 

### Cloud Run ingress from the VPC network

Cloud Run is a Google-managed platform that operates in an
environment outside of the VPC network. This environment hosts
the stable *.run.app URL endpoint for Cloud Run services that
run AI agent or tool workloads. These endpoints are served by the same GFE entry
point that serves *.googleapis.com API services. Cloud Run uses
the same underlying network paths that enable private connectivity for
Private Google Access and for Private Service Connect for
Google APIs. 

Private users on the VPC network that make queries to agents or
tools need to resolve the run.app hostname to the private IP address range for
 Private Google Access 
or to the IP address of the Private Service Connect endpoint for
Google
APIs . A
private managed Cloud DNS zone for the run.app 
URL 
resolves requests for Cloud Run services. The VPC
network routes the request directly over the Google production network. 

Setting Cloud Run ingress to
 Internal restricts access to your service
by permitting requests only from verified internal sources. Approved sources
include the following: 

 VPC networks of the Cloud Run service project. 
 The Shared VPC network that hosts the Direct VPC
egress endpoint. 
 Resources that are within the same VPC Service Controls perimeter. 
 Internal Application Load Balancers in the VPC network. 
 Google services like Cloud Scheduler and Pub/Sub that are within
the service project or VPC Service Controls perimeter. 

If you don't use a common VPC Service Controls perimeter to encompass both the
calling and called services, traffic that's from outside the
Cloud Run service project or the Shared VPC environment
is treated as external. Such traffic includes traffic from other Google Cloud
services like Agent Runtime and other
Cloud Run services. To satisfy the Cloud Run
Internal ingress check, this traffic must be routed in a way that it appears to
originate from within the target service's VPC network. 

To provide the necessary internal network attribution, you can do either of the
following: 

 Use Private Service Connect endpoints to allow services in other
VPCs or projects to connect to Google APIs and services,
including your Cloud Run service, by using a private IP
address within your VPC network. 
 Route traffic through an internal Application Load Balancer placed
within your VPC network in front of your
Cloud Run service. The load balancer funnels requests from
other services through the VPC network so they meet the
internal ingress criteria. 

Internal Application Load Balancers with serverless network endpoint group (NEG)
backends create a VPC resource that's mapped directly to a
Cloud Run service. In this model, the load balancer terminates
client TLS connections with a trusted certificate. Internal Application Load Balancers support
additional security controls including Cloud Armor
 backend security policies and additional
 authorization
policies . 

By default, access to all Cloud Run services requires
IAM authentication. We recommend that you use an identity on a
per-service basis and grant the principal the
Cloud Run Invoker IAM role ( roles/run.invoker ). 

For information about how to configure Cloud Run ingress
controls, see these resources: 

 Restrict network endpoint ingress for Cloud Run services 
 Access control with IAM 
 Receive requests from your private network 
 Set up a regional internal Application Load Balancer with Cloud Run 

If you use Private Google Access or
 Private Service Connect endpoints
for Google APIs to send traffic from your
VPC network to Cloud Run, you can help protect
that traffic by using the following products and features: 

 Cloud Run ingress controls 
 Cloud Run authentication 
 VPC Service Controls 
 Model Armor 

If you use an internal Application Load Balancer to send traffic from your
VPC network to Cloud Run, you can help protect
that traffic by using the following products and features: 

 Cloud Run ingress controls 
 Cloud Run authentication 
 VPC Service Controls 
 Model Armor 
 Load balancer certificate validation 
 Cloud Armor backend security policies 
 Load balancer authorization policies 

### GKE networking

This section describes networking for agents that are based on
GKE. 

### GKE and Gemini Enterprise

As a host for AI agents and tools, GKE offers a highly
customizable platform for network and security controls. A multi-agent AI system
that's deployed on GKE can provide operational efficiency at
scale. It can tightly integrate with other Kubernetes apps and larger
microservices architectures. 

GKE clusters are Compute Engine VM nodes that run within
a subnet of the VPC network.
Gemini Enterprise apps are managed resources that operate in a
hosted environment outside of the VPC network. To enable
Gemini Enterprise apps to call custom agents that are hosted on
GKE, you must securely expose an external Gateway with a public
IP address and DNS name. Traffic flows from Gemini Enterprise
egress to the Google edge network where it takes an optimized route to the
GKE external load balancer. 

It's important to secure the GKE endpoint by using strong
authentication and authorization, Cloud Armor, and limited permissions.
To provide a comprehensive defense-in-depth model to secure AI agents that run
on GKE, consider the security controls that are described in the
following sections. 

### GKE mode of operation

GKE offers these modes of operation to balance management and
control: 

 Autopilot : Google automates the entire GKE cluster infrastructure, including
the control plane, node provisioning, security hardening, and scaling. 
 Standard : Google manages the control plane. You retain full
responsibility for node pool configurations, such as selecting machine
types, managing OS images, and manual scaling. 

### Infrastructure and control plane hardening

 Private GKE clusters : Provision nodes without public IP addresses, which
ensures that the runtime environment is isolated from direct internet
exposure. 
 Master authorized networks : Restrict administrative access to the
Kubernetes API to specific, trusted IP address ranges, which hardens the
control plane against unauthorized configuration changes. Secure the DNS
Endpoint for Kubernetes API by using Google Cloud's IAM
and VPC Service Controls. 

### Identity and access (zero trust)

 IAP : Acts as a gatekeeper at the load balancer level. It
ensures that only authenticated users with the correct IAM
permissions can access the agent endpoint. This approach effectively shifts
the security perimeter from the network to the individual user and their
device context. 

### Edge protection and traffic management

 Cloud Armor : Provides robust edge security, including
Web Application Firewall (WAF) rules to help block malicious payloads, DDoS
protection to help ensure uptime, and
rate limiting to help prevent service exhaustion. 
 Model Armor : Specifically designed for LLM safety,
Model Armor inspects and sanitizes prompts and responses in
real-time to prevent prompt injection and data exfiltration. 

### Internal network isolation

 Kubernetes network policies : Enforces granular, least-privilege
communication between microservices. By default, policies deny all traffic
unless you explicitly permit it, which prevents lateral movement within the
cluster. 

### GKE egress to the VPC network

The VPC network routes outbound connections from agents that are
hosted on GKE. The default GKE cluster network
mode is VPC-native ,
which provides the following attributes: 

 The GKE cluster uses alias IP address ranges. 
 Pod IP addresses are reserved by specifying the Pod IP range. 
 Pod IP addresses are natively routable within the cluster VPC
network and other connected VPC networks. 

If an agent Pod is communicating with a subagent Pod in the same node, then the
traffic is locally routed within the node network namespace. If the destination
agent Pod is on a different node within the cluster, then traffic is routed by
using the VPC network routing table. For an agent Pod to
communicate with other VPC resources like load balancers or
Private Service Connect endpoints, it can reach the destination
by using the same standard VPC routing, subject to firewall
rules. 

You can help protect traffic that leaves your GKE cluster by
using the following products and services: 

 Model Armor 
 Cloud NGFW 
 GKE network policies 
 Private GKE clusters 

### GKE ingress from the VPC network

Kubernetes Services provide access
to GKE resources. For a multi-agent AI system, we recommend that
you use a GKE
Gateway or a 
GKE Inference Gateway .
The Gateway provides enhanced capabilities with traffic control, operational
separation of resources, and security integrations. However, other ingress
service
options 
are available depending on your system requirements. 

The Gateway resource creates an Application Load Balancer and it provisions all of
the necessary load balancing components. The backend network endpoint groups of
the service are wired to provide load balancing directly to containers. To
expose a service internally for traffic that's sourced from the
VPC network, use the Gateway classes for regional internal Application Load Balancer
( gke-l7-rilb ) or cross-region internal Application Load Balancer
( gke-l7-cross-regional-internal-managed-mc ). 

Application Load Balancers provide additional security control points to protect
AI agents and tools that are hosted on GKE clusters: 

 Cloud Armor : Protects services by attaching a
Cloud Armor security policy to the backend services that are
managed by the Gateway. It provides WAF
screening, IP address and geo-based filtering, DDoS protection, and rate
limiting before traffic reaches the GKE cluster or
IAP. 
 IAP : Enabled on the backend service to control access to
apps by using IAM credentials, IAP enforces
zero-trust access policies. IAP authenticates and authorizes
the AI agents that access the cluster resources, including
Gemini Enterprise apps, custom agents, and external
resources. It requires callers to have an identity that's authenticated by
IAM and to have authorized permission to access the backend
service. 

If you send traffic from your VPC network to your
GKE service through a Gateway, you can help protect that traffic
by using the following products and features: 

 IAP 
 Cloud Armor 
 VPC Service Controls 
 Model Armor 

If you don't use a Gateway to send traffic from your VPC network
to your GKE service, you can help protect that traffic by using
the following products and services: 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 GKE network policies 
 GKE network isolation 
 Private GKE clusters 

For more information about securing GKE, see Network security
best
practices 
and Understand network security in
GKE . 

### Agent network security

To protect the network of a multi-agent AI system, you must secure
communications through both the VPC network and the API surface.
The VPC network dataplane addresses how agents and tools securely
connect. The API surface defines which identities and types of data exchanges
are allowed. Layering access controls across both the VPC network
and the API surface helps to enforce a highly controlled and resilient
security posture. 

### Cloud NGFW

Cloud NGFW acts as the network-level gatekeeper to secure A2A and
MCP communications. The firewall ensures that only authorized traffic can reach
the agent endpoints by verifying every incoming or outgoing connection to and
from other agents and tools. 

 Cloud NGFW is a distributed
firewall service that's built into the VPC network fabric. It
offers these feature tiers that operate at different layers of the network
stack: 

 Cloud Next Generation Firewall Essentials : Provides stateful firewall packet filtering.
Policy rules are defined based on IP addresses (L3), protocols, and ports
(L4). 
 Cloud Next Generation Firewall Standard : Provides IP-based enforcement with Fully Qualified
Domain Name (FQDN) objects, geolocation objects, and feeds from
Google Threat Intelligence to block known malicious addresses. 
 Cloud Next Generation Firewall Enterprise : Provides true app (L7) inspection capabilities
with TLS decryption and intrusion detection and prevention system (IDPS)
capabilities to analyze payloads against advanced threat signatures. 

Cloud NGFW can be applied on the VPC network to
enforce firewall policy based on rules that are needed to target the agent
hosting platform that you used. 

 Agent Runtime : Agents that run in
Agent Runtime connect to the VPC
network by using Private Service Connect network attachments.
These attachments make the agent network interface appear within a subnet in
the VPC network. Cloud NGFW network firewall
policies are applied to the VPC network. The policies filter
traffic based on the source IP addresses from the subnet that's dedicated to
the Private Service Connect network attachment. For traffic
matching, you can use source IP address and destination IP address ranges. 
 Cloud Run : Cloud Run services that use
Direct VPC egress send traffic directly from instances that
run within a subnet that's specified in the VPC network.
Cloud NGFW network firewall policies apply to the subnet that's
used by Cloud Run to filter traffic. For traffic matching,
you can use source IP address and destination IP address ranges. 
 GKE : VPC-native GKE clusters 
give Pods IP addresses that are directly from the VPC network
secondary IP address ranges. Network firewall policies can filter traffic
based on IP address ranges for GKE nodes and Pods, and the
policies can use secure tags and
service accounts. Secure tags bind to the VM instances that act as
GKE nodes. Firewall rules can then target or source traffic
from nodes that have specific tags. Firewall rules can also target or source
traffic from GKE nodes based on the service account identity
that's associated with the node pool. 

### Default deny egress policy

Implementing a default deny strategy is a security best practice that adheres to
the principle of least
privilege . This
strategy ensures that only network traffic that's explicitly allowed is
permitted, while all other traffic is blocked by default. This implementation is
achieved by structuring firewall rules with high-priority ALLOW rules for
known, legitimate flows and a low-priority, catch-all DENY rule. All tiers of
Cloud NGFW allow rules based on source and destination IP address
ranges. 

Firewall policy rules can effectively match source traffic from the
Agent Runtime network
attachment 
subnet and from the Cloud Run Direct VPC
egress subnet. 

The following is an example default-deny egress policy: 

 Create network firewall policy and rules : Create a global or regional
 firewall policy and associate
it with the VPC network. Create firewall policy
rules 
that target traffic in the egress direction ( --direction=EGRESS ) based on
the source IP address ranges ( --src-ip-ranges=SRC_IP_RANGES ) and the
destination IP address ranges ( --dest-ip-ranges=DEST_IP_RANGES ). 
 Specific ALLOW rules : Use lower priority numbers, for example
100-1000. These rules precisely allow the network traffic that's required
for your AI agents to function. This traffic includes communication to other
internal services, load balancers, required Google APIs, or legitimate
external endpoints. Create a rule that matches source traffic from the
Agent Runtime network
attachment 
subnet or from the Cloud Run Direct VPC
egress subnet to the
destinations that you want. 
 General DENY rule : To ensure that the rule is last in the evaluation
order, use the highest priority number, for example 2147483647. This rule
denies traffic to any destination ( --dest-ip-ranges=0.0.0.0/0 ) that
doesn't match any of the preceding ALLOW rules. 

A default deny egress policy prevents AI agents from making any network
connections that aren't explicitly authorized and it blocks potential data
exfiltration or access to malicious sites. The policy confines the hosted agents
to only communicate with approved endpoints, which is crucial for maintaining
control over autonomous workloads. 

### Additional Cloud NGFW policy considerations

Beyond the default deny strategy that's available with all
Cloud NGFW tiers, you can further harden your multi-agent AI
network security by using paid-tier features: 

 Cloud NGFW Standard features :

 FQDN Objects for dynamic endpoints : AI agents often interact with
external APIs, model endpoints, or data sources whose IP addresses might
change. For consistent access to necessary services by domain name, use
FQDN objects in ALLOW rules. 
 Geolocation controls : If AI agents have compliance requirements or
if they shouldn't interact with services in specific geographic regions,
use geolocation objects ( --src-region-codes=SRC_COUNTRY_CODES ) in your
firewall rules to restrict traffic to or from those locations. 
 Google Threat Intelligence : Use Google Threat Intelligence
in egress filters to automatically block agents from connecting to known
malicious destinations, such as command and control (C2) servers,
anonymizers like Tor, and malware distribution sites. The use of
Google Threat Intelligence helps to contain the impact of a
potentially compromised agent. We recommend that you include these
destination filters in the higher priority number (lower evaluation
order) DENY rules. 

 Cloud NGFW Enterprise features :

 Layer 7 inspection : For agents that handle sensitive data or that
are exposed to higher risks, inspect packet payloads for threats like
malware, spyware, and exploits that aren't analyzed by network layer
firewall rules. 
 TLS inspection : To allow the inspection engine to analyze encrypted
traffic, enable TLS inspection. The use of TLS inspection is crucial
because most modern attacks and C2 communication are encrypted. 

For additional implementation considerations or limitations that might be
applicable to your environment, see these resources: 

 URL filtering service 
 Intrusion detection and prevention service 
 TLS inspection 

### IAP

 IAP secures ingress
requests to GKE clusters by providing a central authentication
and authorization layer for AI apps. IAP intercepts all of the
HTTPS requests that are destined for the Gateway, and it checks the identity and
permissions of the caller. IAP allows only authenticated and
authorized requests to pass to the backend service workload. IAP
on the Gateway load balancer only protects traffic that comes from outside the
cluster. Communication within the cluster doesn't pass through
IAP. 

To access AI apps that are hosted on GKE and that are protected
by IAP, principal user identities must be granted the
IAP-secured Web App User IAM role ( roles/iap.httpsResourceAccessor )
on the IAP-protected backend service resource. We recommend that
you configure a custom service account as the identity for deployed agents.
Using a custom service account lets you assign permissions more precisely
according to the principle of least privilege. 

Only grant the IAP-secured Web App User IAM role directly to the
service accounts of agents that are allowed to access other agents and tools
that are hosted on the GKE
 BackendConfig custom
resource. To allow Gemini Enterprise apps access, grant
permissions by binding the IAM role Discovery Engine Service
Account 
( roles/discoveryengine.serviceAgent ) for your Gemini Enterprise
project. 

### VPC Service Controls

 VPC Service Controls 
mitigates data exfiltration risks by strictly controlling access to Google APIs.
We recommend that you deploy a single macro perimeter that includes all
supported services. This approach provides the most robust defense against
exfiltration. To ensure consistent policy enforcement for
 Shared VPC architectures, it's crucial to
include both the host project and all of the associated service projects 
within the same service perimeter. 
 Note: Implementation of a VPC Service Controls perimeter requires organizational planning, data gathering, and testing. This organizational effort includes documenting and interviewing workload teams to map specific access patterns and use cases. For information about how to implement a service perimeter on new or existing environments, see Best practices for enabling VPC Service Controls . 

To secure the interaction between Gemini Enterprise and
Cloud Run across project boundaries, consider the following
recommendations: 

 Deploy a single VPC Service Controls perimeter that encompasses both the
Gemini Enterprise and Cloud Run projects. 
 Add all supported VPC Service Controls services to the list of restricted
services. This approach helps to prevent unauthorized administrative
changes. 
 Enforce internal ingress and
 authorization settings to block all
public internet access to your Cloud Run services. 

Cloud Run services are secured by IAM. Callers
must be authenticated and they must have the Cloud Run
Invoker IAM role
( roles/run.invoker ) on the target service. The role is checked by validating a
token from the Authorization header. To successfully call the
Cloud Run service, service accounts, such as those used by 
Gemini Enterprise ,
must also be granted the Cloud Run Invoker role. 

When Gemini Enterprise and Cloud Run are deployed
in different projects, a VPC Service Controls perimeter is required in order to
set Cloud Run ingress to Internal. Without this perimeter,
cross-project calls from Gemini are treated as external traffic,
which forces you to set Cloud Run ingress to All—which leaves the
service exposed to the public internet. 

 Cloud Run ingress all is supported when both of these are
 true :

 VPC Service Controls isn't enabled. 
 Cloud Run and Gemini Enterprise aren't in
the same project. 

 Only Cloud Run ingress internal is supported for all other
configurations. 

### Additional VPC Service Controls considerations

When Cloud Run is deployed inside a VPC Service Controls
perimeter, we recommend that you implement the following policy guardrails to
help ensure comprehensive protection: 

 Restrict allowed ingress
settings :
Prevent developers from accidentally deploying public-facing endpoints by
setting the run.allowedIngress organization policy constraint. This
constraint only applies to new deployments. Prior deployments might not be
compliant. We recommend that you audit any existing Cloud Run
services within the perimeter and re-deploy or update any that don't meet
the required ingress and egress settings.

 To allow only internal requests, set the value to internal . 
 To allow requests through an external Application Load Balancer, set the
value to internal-and-cloud-load-balancing . 

 Restrict allowed VPC egress
settings :
To route all outbound requests through the VPC so that they
can be inspected by perimeter firewall rules, set the
 run.allowedVPCEgress organization policy constraint value to
 all-traffic . This setting requires that every Cloud Run
revision use Direct VPC egress or a
Serverless VPC Access connector. This constraint only applies to
new deployments. Prior deployments might not be compliant. We recommend that
you audit any existing Cloud Run services within the
perimeter and re-deploy or update any that don't meet the required ingress
and egress settings. 
 Colocate container images and services : The Artifact Registry repository that
contains your container images must reside within the same perimeter as the
Cloud Run service. Cross-perimeter image pulling is
automatically blocked unless you establish explicit ingress and egress
rules. 
 Manage access levels : VPC Service Controls ingress policy rules and
access levels that rely on IAM principal identities aren't
supported for Cloud Run invocations. You must instead manage
access with network-based criteria or device-based access levels. 

### Model Armor

 Model Armor is an API-based service that
provides enhanced security and safety for AI apps. AI agents interact with
Model Armor by making calls to sanitize user prompts before
they're sent to an LLM and to sanitize model responses before they're returned
to the user. Model Armor actively screens LLM prompts and
responses, which provides an important inspection point for detecting emerging
risks and provides a control point for implementing responsible AI standards. We
recommend that you use Model Armor to ensure compliance with data
residency requirements and with data sovereignty legal regulations. To use
Model Armor within a VPC Service Controls perimeter, you need to
configure a Private Service Connect endpoint for the
Model Armor regional endpoint within your VPC
network. 

Model Armor is a regional service that's accessed privately
through regional Private Service Connect
endpoints in the
VPC network. For example, the us-central1 service is called by
using the regional endpoint 
 modelarmor.us-central1.rep.googleapis.com . Regional endpoints help to ensure
data residency . 

To enable access for agents, configure the following components in every region
where the Model Armor service is required: 

 Create or identify an RFC
1918 subnet in the
VPC network region where the Model Armor
service resides. 
 Create a regional endpoint 
in the RFC 1918 subnet. 
 Create a Cloud DNS private zone 
and a record for the Model Armor regional endpoint hostname
(for example, modelarmor.us-central1.rep.googleapis.com ) that resolves to
the IP address of the regional endpoint. 
 For Agent Runtime interoperability, establish DNS
peering 
from Agent Runtime to the Cloud DNS private
zone that's associated with your VPC network. When agents
make requests to Model Armor, Cloud DNS resolves the
hostname requests to the IP address of the
Private Service Connect regional endpoint in the
VPC network. This step isn't required for agents that are
hosted in Cloud Run and GKE. 

To integrate
 Gemini Enterprise 
with Model Armor, create a Model Armor template in
the same project as Gemini Enterprise. The location of the
template and the Gemini Enterprise app must be the same. 

For more information about enabling Model Armor, see these
resources: 

 Model Armor integration with
Gemini Enterprise 
 Enable Model Armor in Gemini Enterprise 
 Supported Google APIs in supported regions 
 Model Armor integration with Google Cloud services 
 Data residency and endpoints 

### Cloud Armor

 Cloud Armor is a distributed
network security service that protects apps and services behind load balancers
before requests reach backend service runtimes. AI agent workloads involve high
volumes of inter-service communication that use A2A, MCP, and API calls.
Cloud Armor protection provides additional layers of resilience in the
security design with rate limiting, WAF screening, and custom rules that conform
to expected agentic requests. By attaching Cloud Armor security
policies to Application Load Balancer backend services, traffic can be filtered
for malicious requests and policed with rate limits, and DDoS attacks can be
mitigated. 

Cloud Armor can be deployed in an agent network architecture in the
following scenarios: 

 Cloud Run with internal Application Load Balancer :
Protect agents and tools that run on Cloud Run by using an
internal Application Load Balancer with serverless NEG backends. Apply
 backend security policies 
to the serverless NEG to enforce WAF rules for internal traffic and rate
limiting. To control agent communications, you can define additional custom
rules based on IP addresses and headers. 
 Gateway : Protect agents and tools that run on GKE by
using a Gateway resource definition for a global or regional external Application Load Balancer
with zonal NEG backends. Use the Kubernetes Gateway
API to apply
the GCPBackendPolicy resource with the defined Cloud Armor
security policy. If you use a regional external Application Load Balancer, Cloud Armor
supports backend security
policies with WAF
rules, IP address and geo-based controls, and rate limiting. Global external
Application Load Balancers support backend security policies and additional
 edge security policies 
with Google Cloud Armor Adaptive Protection and 
Google Threat Intelligence . 

### Secure Web Proxy

 Secure Web Proxy is a regional managed service
that's deployed within the VPC network to filter HTTP/S traffic
that originates within the VPC network or within any connected
networks. It acts as a centralized proxy and security enforcement point to
provide granular control and visibility for outbound internet traffic. It also
acts as an explicit proxy for internal service communications. 

Secure Web Proxy supports three deployment
modes : explicit proxy routing
mode, Private Service Connect service attachment mode, and next
hop mode. We recommend that you use Secure Web Proxy in explicit proxy routing
mode , which is the
focus of this document. In this mode, HTTP clients must be explicitly configured
to point directly to the Secure Web Proxy IP address or hostname. 

To deploy Secure Web Proxy in your VPC network, you must configure a
frontend subnet and a proxy-only
subnet .
Secure Web Proxy is a fully managed service. When Secure Web Proxy is deployed, it
automatically deploys and configures Cloud Router and Cloud NAT in
your VPC network for specific integration with the proxy
resource. This configuration mandates that any outbound requests must pass
through Secure Web Proxy before they egress to the internet. 

Using Secure Web Proxy as an explicit proxy supports agent requests that come from
Agent Runtime Private Service Connect
interfaces, Cloud Run Direct VPC egress, and
VPC-native GKE clusters. When agents send requests
to Secure Web Proxy by using the HTTP CONNECT method, TCP session traffic is
tunneled to the proxy where security policy rules are applied. If the traffic is
allowed, Secure Web Proxy sends the traffic to the controlled internet egress or to
private network destinations that are routable by the VPC
network. 

### Explicit proxy routing

Agent Runtime egress requires that you use an explicit
proxy configuration in order for agents to reach internet destinations or
 non-routable IP address ranges 
in the VPC network. For Agent Runtime
interoperability, we recommend that you configure the Secure Web Proxy resource with
an RFC 1918 IP address from a frontend subnet in the VPC network.
With this configuration, Secure Web Proxy becomes directly reachable from
Agent Runtime. It can then proxy any connections to
non-routable IP address destinations that are in the VPC network
or in connected networks. 

To support agent hosting platform use of Secure Web Proxy in explicit routing mode,
configure these networking resources: 

 Create or identify an
 RFC 1918 subnet
in the VPC network to host the Secure Web Proxy resource. 
 Create a Cloud DNS record for the Secure Web Proxy hostname (for
example, swp.example.com ) that resolves to the IP address of the
Secure Web Proxy resource. 
 For Agent Runtime interoperability, establish DNS
peering 
from Agent Runtime to the Cloud DNS private
zone that's associated with your VPC network. When agents
make requests to Secure Web Proxy, Cloud DNS resolves the hostname
requests to the IP address of the Secure Web Proxy resource in the
VPC network. This step isn't required for agents that are
hosted in Cloud Run and GKE. 

### Agent proxy settings

The standard way to configure agent apps to use an HTTP(S) proxy is by setting
these environment variables: 

 HTTP_PROXY : The URL of the explicit proxy server for HTTP traffic (for
example, http://swp.example.com:8888 ). This
setup uses the HTTP CONNECT method from the client to the proxy. Even
though HTTP is specified, TLS encryption is maintained end-to-end through
the proxy from the agent runtime to the target endpoint. 
 HTTPS_PROXY : The URL of the explicit proxy server for HTTPS traffic (for
example, https://swp.example.com:8888 ).
Like the HTTP_PROXY setting, the HTTPS_PROXY setting uses TLS by default.
However, you can provide
an additional layer of encryption by enabling your own TLS encryption on top
of the default TLS. For more information, see
 Certificate Authority Service . 
 NO_PROXY : A comma-separated list of hostnames or IP addresses that
shouldn't go through the proxy. For example, if you add
 metadata.google.internal and 169.254.169.254 to the NO_PROXY list, then
workloads can directly access the metadata service for authentication and
authorization to Google APIs and services. 

When you use the env_vars argument to set variables during deployment, they
become available within the agent runtime environment (for example, when you use
 os.environ in Python). Most standard HTTP client libraries automatically
discover and use these environment variables to route traffic through the
specified proxy. This approach is common for Python apps and HTTP client
libraries like
 requests .
When you deploy agents, define environment variables for using Secure Web Proxy for
any private domains that the agents need to reach. Ensure that any private
domain destinations are also included in Cloud DNS. 

The following example shows a Agent Runtime proxy
deployment from an agent
object : 

 ## specify environment variables (dictionary) 
 env_vars = { 
 "OTHER_VARIABLE" : "OTHER_VALUE" , 
 "HTTP_PROXY" : "http://swp.example.com:8888" , 
 "HTTPS_PROXY" : "http://swp.example.com:8888" , 
 "NO_PROXY" : "localhost,127.0.0.1,metadata.google.internal,169.254.169.254,.googleapis.com,run.app,.gcr.io,.pkg.dev,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal" 
 } 

 remote_agent = aiplatform . agent_engines . create ( 
 agent = local_agent , 
 config = { 
 "display_name" : "Example agent using proxy" , 
 "env_vars" : env_vars , 
 ## ... other configs 
 }, 
 ) 

Cloud Run supports setting environment variables at the service
revision level. This approach overrides any environment variables with the same
name that were set within the container image. This approach is useful for
setting operational parameters like proxy variables when the service instances
start. 

The following example shows the command to set the environment variables when
you deploy a
Cloud Run service: 

 gcloud run deploy SERVICE_NAME \ 
--image = IMAGE_URL \ 
--set-env-vars = "HTTP_PROXY=http://swp.example.com:8888,HTTPS_PROXY=http://swp.example.com:8888,NO_PROXY=localhost,127.0.0.1,metadata.google.internal,169.254.169.254,.googleapis.com,run.app,.gcr.io,.pkg.dev,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal" 

To implement an explicit proxy configuration in GKE pods, define
a ConfigMap resource that specifies the proxy variables: 

 apiVersion: v1
kind: ConfigMap
metadata:
 name: agent-proxy-config
 namespace: ai-apps
data:
 HTTP_PROXY: "http://swp.example.com:8888"
 HTTPS_PROXY: "http://swp.example.com:8888"

 NO_PROXY: "localhost,127.0.0.1,metadata.google.internal,169.254.169.254,.googleapis.com,run.app,.gcr.io,.pkg.dev,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,.internal"

To apply the ConfigMap keys to the Pods, use the envFrom field in the
container manifest. This specification injects the environment variables into
the container at runtime. 

 apiVersion: apps/v1
kind: Deployment
metadata:
 name: subagent-app
spec:
 template:
 spec:
 containers:
 - name: my-container
 image: my-agent-app:latest
 envFrom:
 - configMapRef:
 name: agent-proxy-config

### CA Service

 CA Service (CA Service) 
is required when Secure Web Proxy or Cloud NGFW is configured for TLS
inspection. When TLS inspection is enabled and a workload's destination uses
TLS, CA Service creates and signs a certificate for that
destination. When the encrypted traffic for the real destination arrives at
Secure Web Proxy or Cloud NGFW, it decrypts the packet, inspects it,
and then enforces policies. If the policies allow the packet, the service
re-encrypts the packet for the final destination. You can also use
CA Service to provide certificates to other Google managed
services. 

CA Service is a managed service. After CA Service
is configured, it handles leaf certificate signing until the root CA certificate
expires. Root CA certificates must be updated to ensure that they don't expire. 

CA Service supports these capabilities to enable traffic
inspection and certificate management at scale in a multi-agent AI architecture: 

 TLS inspection : Use of a private CA is required for full TLS inspection.
To fully decrypt and analyze HTTPS payloads, the intermediary proxy device
(Secure Web Proxy or Cloud NGFW) needs to terminate the TLS session
with the client. The proxy must present a valid certificate that the client
accepts as trusted for the domain that's requested. 

CA Service can dynamically generate and sign a site-specific
impersonation certificate for the site that's requested. When the client has
the private root CA certificate installed in its trust store, it accepts
this dynamically created certificate as valid. The client trusts the
certificate that's sent by the proxy, so it sends the request. The proxy
terminates the TLS session, decrypts the packet, inspects the contents, and
then enforces policies. 

 Certificate distribution : Internal client resources like AI agents that
run on Agent Runtime, Cloud Run, or
GKE need the private root CA certificate added to their local
trust stores. By storing the root CA certificate public key in Secret Manager , AI agents can pull the certificate
on startup and add it to their system trust store. 

Internal server resources like internal Application Load Balancers need
certificates that are issued by the private CA to act as trusted server
endpoints and terminate client TLS sessions. Application Load Balancers
integrate with Certificate Manager issuance
configurations to automate the
CA Service signing the certificate request and deploying it
to the load balancer. 

For more information about certificate operations, see these resources: 

 Cloud Run: Configure secrets for services 
 GKE: Access private registries with private CA certificates 
 Secure Web Proxy: Enable TLS inspection 
 Cloud NGFW: TLS inspection overview 

### A2A connection security

Root agents communicate with a diverse array of subagents and MCP servers that
are deployed across various runtime hosting platforms. Each environment
introduces unique networking and security requirements that must be abstracted
by the A2A or MCP layer. 

The following diagram shows the components and possible connection paths that
are supported by this design guide: 

The preceding diagram summarizes these connection possibilities: 

 Users interact with the agentic system through a
Gemini Enterprise app. 
 The Gemini Enterprise app uses Google infrastructure to
connect to a root agent that runs in GKE,
Cloud Run, or Agent Runtime. 
 The Gemini Enterprise app and the root agents use Google
infrastructure to connect to Model Armor and the
Gemini LLM on Agent Platform. 
 The root agents can use Google infrastructure to connect to subagents that
run in Cloud Run or Agent Runtime. 
 The root agents can use private IP addresses to connect to subagents that
run in Agent Runtime, Cloud Run, and
GKE. These connections must be routed through a
VPC network. 
 Both root agents and subagents can connect to MCP servers that run on
Cloud Run or GKE. Agents that connect to the
MCP servers can use either Google infrastructure or a VPC
network. The MCP servers provide access to tools that are hosted in
Google Cloud, on-premises, in another cloud, or on the internet. 
 Services that are hosted on the internet can be reached directly through
Secure Web Proxy. 

The following sections provide resources for the runtime data paths and security
controls that are required for secure A2A interactions. This information serves
as the architectural standard for establishing private connectivity and
implementing the multi-layered defenses that are necessary to protect the
end-to-end data path between agents. 

### GKE source agent

The following table provides resources to help you protect traffic when
GKE is the source agent. This traffic travels through the
VPC network that hosts the GKE cluster. 

 Destination agent (data path) 
 Security control 

 Agent Runtime (internal) 

 VPC Service Controls 
 Model Armor 

 Cloud Run (internal) 

 VPC Service Controls 
 Model Armor 

 Cloud Run (Private Service Connect for Google APIs) 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 

 Cloud Run access (serverless NEG) 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 Internal Application Load Balancer certificate authorization 
 Cloud Armor 
 Private Service Connect endpoint 

 GKE 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 Internal Application Load Balancer certificate authorization 
 Cloud Armor 
 Private Service Connect endpoint 

 Internet through VPC network 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 Secure Web Proxy 

### Agent Runtime (internal) source agent

The following table provides resources to help you protect traffic when
Agent Runtime is the source agent and the traffic
travels directly over Google infrastructure. In these paths, no
VPC network is involved. 

 Destination agent (data path) 
 Security control 

 Agent Runtime (internal) 

 VPC Service Controls 

 Cloud Run (internal) 

 VPC Service Controls 

### Agent Runtime (Private Service Connect interface) source agent

The following table provides resources to help you protect traffic when
Agent Runtime is the source agent and the traffic uses a
Private Service Connect interface to travel through a
VPC network. 

 Destination agent (data path) 
 Security control 

 Cloud Run (Private Service Connect
 GoogleAPIs) 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 

 Cloud Run access (serverless NEG) 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 Internal Application Load Balancer certificate authorization 
 Cloud Armor 
 Private Service Connect
 endpoint 

 GKE 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 Internal Application Load Balancer certificate authorization 
 Cloud Armor 
 Private Service Connect
 endpoint 

 Internet through VPC network 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 Secure Web Proxy 

### Cloud Run (internal) source agent

The following table provides resources to help you protect traffic when
Cloud Run is the source agent and the traffic travels directly
over Google infrastructure. In these paths, no VPC network is
involved. 

 Destination agent (data path) 
 Security control 

 Agent Runtime (internal) 

 VPC Service Controls 

 Cloud Run (internal) 

 VPC Service Controls 

### Cloud Run (Direct VPC egress) source agent

The following table provides resources to help you protect traffic when
Cloud Run is the source agent and the traffic uses Direct
VPC egress to travel through a VPC network. 

 Destination agent (data path) 
 Security control 

 Cloud Run (Private Service Connect for Google APIs) 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 

 Cloud Run access (serverless NEG) 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 Internal Application Load Balancer certificate authorization 
 Cloud Armor 
 Private Service Connect endpoint 

 GKE 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 Internal Application Load Balancer certificate authorization 
 Cloud Armor 
 Private Service Connect endpoint 

 Internet through VPC network 

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 Secure Web Proxy 

 Agent Runtime Private Service Connect for Google APIs

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 

### MCP connection security

The following list outlines the hosting platforms and defense-in-depth controls
that are involved in securing the data path between agent runtimes and MCP
servers. For source agents in Agent Runtime, in
Cloud Run, or in GKE, use the following security
controls depending on the destination MCP server: 

 Internet :

 VPC Service Controls 
 Model Armor 
 Cloud NGFW 
 Secure Web Proxy 

 Google MCP :

 VPC Service Controls 
 Model Armor 

### What's next

 Read about how to build your agentic system:

 Choose your agentic AI architecture
components .

 Choose a design pattern for your agentic AI
system . 
 Multi-agent AI system in
Google Cloud . 

For more reference architectures, diagrams, and best practices, explore the
 Cloud Architecture Center .

### Contributors

Authors:
 Deepak Michael | Networking Specialist Customer Engineer Michael Larson | Customer Engineer, Networking Specialist Victor Moreno | Product Manager, Cloud Networking 

Other contributors:
 Christine Sizemore | Cloud Security Architect Aspen Sherrill | Cloud Security Architect Assaf Namer | Principal Cloud Security Architect David Tu | Customer Engineer Ammett Williams | Developer Relations Engineer Mark Schlagenhauf | Technical Writer, Networking 

Was this helpful? 

 Send feedback

Except as otherwise noted, the content of this page is licensed under the Creative Commons Attribution 4.0 License , and code samples are licensed under the Apache 2.0 License . For details, see the Google Developers Site Policies . Java is a registered trademark of Oracle and/or its affiliates. 

Last updated 2026-04-16 UTC. 

 Need to tell us more?

 [[["Easy to understand","easyToUnderstand","thumb-up"],["Solved my problem","solvedMyProblem","thumb-up"],["Other","otherUp","thumb-up"]],[["Hard to understand","hardToUnderstand","thumb-down"],["Incorrect information or sample code","incorrectInformationOrSampleCode","thumb-down"],["Missing the information/samples I need","missingTheInformationSamplesINeed","thumb-down"],["Other","otherDown","thumb-down"]],["Last updated 2026-04-16 UTC."],[],[]]

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