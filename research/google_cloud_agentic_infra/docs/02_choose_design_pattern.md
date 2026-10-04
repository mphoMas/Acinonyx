# Choose a Design Pattern for Your Agentic AI System

**Source URL:** https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system

---

Choose a design pattern for your agentic AI system  |  Cloud Architecture Center  |  Google Cloud Documentation 

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
 " track-metadata-position="nav" track-type="freeTrial" track-name="gcpCta" referrerpolicy="no-referrer-when-downgrade" track-metadata-eventdetail="nav">Start free 

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

 On this page Overview of the design process Define your requirements Single-agent system Multi-agent systems Sequential pattern Parallel pattern Loop pattern Review and critique pattern Iterative refinement pattern Coordinator pattern Hierarchical task decomposition pattern Swarm pattern Reason and act (ReAct) pattern Human-in-the-loop pattern Custom logic pattern Compare design patterns Workflows that are deterministic Workflows that require dynamic orchestration Workflows that involve iteration Workflows that have special requirements What's next Contributors 

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
 Choose a design pattern for your agentic AI system 

 Stay organized with collections

 Save and categorize content based on your preferences. 

 On this page Overview of the design process Define your requirements Single-agent system Multi-agent systems Sequential pattern Parallel pattern Loop pattern Review and critique pattern Iterative refinement pattern Coordinator pattern Hierarchical task decomposition pattern Swarm pattern Reason and act (ReAct) pattern Human-in-the-loop pattern Custom logic pattern Compare design patterns Workflows that are deterministic Workflows that require dynamic orchestration Workflows that involve iteration Workflows that have special requirements What's next Contributors 

 <div class="devsite-article-body clearfix
 ">

Last reviewed 2026-05-28 UTC 

This document provides guidance to help you choose a design pattern for your agentic AI system.
 Agent design patterns are common
architectural approaches to build agentic applications. An agent design pattern
offers a distinct framework for organizing a system's components, integrating the
model, and orchestrating a single agent or multiple agents to accomplish a
workflow. 

 AI agents 
are effective for applications that solve open-ended problems, which might require
autonomous decision-making and complex multi-step workflow management. Agents
excel at solving problems in real-time by using external data and they excel at automating
knowledge-intensive tasks. AI agents are suitable when you need AI to complete
goal-focused tasks with some degree of autonomy. For other use cases, you can
use assistive and generative AI applications. To learn about the differences
between AI agents and non-agentic AI applications, see
 What is the difference between AI agents, AI assistants, and bots? 

This guide assumes that you have a foundational knowledge of agentic AI systems
and how their architecture differs from that of non-agentic systems, such as
those that use direct model reasoning or
 retrieval-augmented generation (RAG) . 

For a summary of the agent pattern guidance, see the
 compare design patterns section later in this document. 

### Overview of the design process 

The following are the high-level steps to choose a design pattern for your
agentic AI system. These steps are described in detail later in this document. 

 Define your requirements : Assess the characteristics of your
workload,including task complexity, latency and performance expectations,
cost budget, and the need for human involvement. 
 Review the common agent design patterns :
Learn about the common design patterns in this guide, which include both
single-agent systems and multi-agent systems. 
 Select a pattern :
Select the appropriate design pattern based on
your workload characteristics. 

This process isn't a one-time decision. You should periodically revisit these
steps to refine your architecture as your workload characteristics change, your
requirements evolve, or new Google Cloud features become available. 

### Define your requirements

The questions that follow aren't exhaustive checklists for planning. Use these
questions as a starting point to identify the primary goal of your agentic
system and to select the best design pattern. 

 Task characteristics : Can your task be completed in predefined workflow
steps or is the task open-ended? Does your task need to use an AI model to
orchestrate the workflow? 
 Latency and performance : Do you need to prioritize fast or interactive
responses at the cost of accuracy or high-quality responses? Or can your
application tolerate a delay to achieve a more accurate or thorough result? 
 Cost : What is your budget for inference costs? Can you support patterns
that require multiple calls to the model for a single request? 
 Human involvement : Does your task involve high-stakes decisions,
safety-critical operations, or subjective approvals that require human
judgment? 

If your workload is predictable or highly structured, or if it can be executed
with a single call to an AI model, it can be more cost effective to explore
non-agentic solutions for your task. For example, you might not need an agentic
workflow for tasks like summarizing a document, translating text, or classifying
customer feedback. For information about choosing architecture components for
generative AI applications that don't require an agentic infrastructure, see
 Choose models and infrastructure for your generative AI
application . 

The following sections describe common agent design patterns for building a
reliable and effective agentic AI system. 

### Single-agent system

A single-agent system uses an AI model, a defined set of tools, and a comprehensive
system prompt to autonomously handle a user request or to complete a specific task.
In this fundamental pattern, the agent relies on the model's reasoning
capabilities to interpret a user's request, plan a sequence of steps, and decide
which tools to use from a defined set. The system prompt shapes the agent's
behavior by defining its core task, persona, and operations,
and the specific conditions for using each tool. 

The following diagram shows a high-level view of a single agent pattern: 

A single-agent system is ideal for tasks that require multiple steps and access
to external data. For example, a customer support agent must query a database to
find an order status, or a research assistant needs to call APIs to summarize
recent news. A non-agentic system can't perform these tasks because it can't
autonomously use tools or execute a multi-step plan to synthesize a final
answer. 

If you're early in your agent development, we recommend that you start with a
single agent. When you start your agent development with a single-agent system,
you can focus on refining the core logic, prompt, and tool definitions of your
agent before adding more complex architectural components. 

A single agent's performance can be less effective when it uses more tools and
when tasks increase in complexity. You might observe this as increased latency,
incorrect tool selection or use, or a failure to complete the task. You can
often mitigate these issues by refining the agent's reasoning process with
techniques like the Reason and Act (ReAct) pattern . However,
if your workflow requires an agent to manage several distinct responsibilities,
these techniques might not be sufficient. For these cases, consider a
 multi-agent system , which can improve resilience and
performance by delegating specific skills to specialized agents. 

### Multi-agent systems

A multi-agent system orchestrates multiple specialized agents to solve a
complex problem that a single agent can't easily manage. The core principle is
to decompose a large objective into smaller sub-tasks and assign each sub-task
to a dedicated agent with a specific skill. These agents then interact through
collaborative or hierarchical workflows to achieve the final goal. Multi-agent
patterns provide a modular design that can improve the scalability, reliability,
and maintainability of the overall system compared to a single agent with a
monolithic prompt. 

In a multi-agent system, each agent requires a specific context to perform its
task effectively. Context can include documentation, historical preferences,
relevant links, conversational history, or any operational constraints. The
process of managing this information flow is called
 context engineering . Context engineering includes strategies such as isolating
context for a specific agent, persisting information across multiple steps, or
compressing large amounts of data to improve efficiency. 

Building a multi-agent system requires additional evaluation, security,
reliability, and cost considerations when compared to a single-agent system. For
example, multi-agent systems must implement precise access controls for each
specialized agent, design a robust orchestration system to ensure reliable
inter-agent communication, and manage the increased operational costs from the
computational overhead of running multiple agents. For an example reference
architecture to build a multi-agent system, see
 Multi-agent AI systems in Google Cloud . 

### Sequential pattern

The multi-agent sequential pattern executes a series of specialized agents in
a predefined, linear order where the output from one agent serves as the direct
input for the next agent. This pattern uses a
 sequential workflow agent that operates on predefined logic without having
to consult an AI model for the orchestration of its subagents. 

The following diagram shows a high-level view of a multi-agent sequential
pattern: 

Use the sequential pattern for highly structured, repeatable processes where
the sequence of operations doesn't change. For example, a data processing
pipeline might use this pattern to first have a data extraction agent pull raw
data, then pass that data to a data cleaning agent for formatting, which in turn
passes the clean data to a data loading agent to save it in a database. 

The sequential pattern can reduce latency and operational costs compared to a
pattern that uses an AI model to orchestrate task workflow. However, this
efficiency comes at the cost of flexibility. The rigid, predefined structure of
the pipeline makes it difficult to adapt to dynamic conditions or to skip
unnecessary steps, which can cause inefficient processing or lead to higher
cumulative latency if an unneeded step is slow. 

### Parallel pattern

The multi-agent parallel pattern , also known as a concurrent pattern ,
multiple specialized subagents perform a task or sub-tasks independently at the
same time. The outputs of the subagents are then synthesized to produce the
final consolidated response. Similar to a
 sequential pattern , the parallel pattern uses a
 parallel workflow agent to manage how and when the other agents run
without having to consult an AI model to orchestrate its subagents. 

The following diagram shows a high-level view of a multi-agent parallel
pattern: 

Use the parallel pattern when sub-tasks can be executed concurrently to reduce
latency or gather diverse perspectives, such as gathering data from disparate
sources or evaluating several options at once. For example, to analyze customer
feedback, a parallel agent might fan out a single feedback entry to four
specialized agents at the same time: a sentiment analysis agent, a keyword
extraction agent, a categorization agent, and an urgency detection agent. A
final agent gathers these four outputs into a single, comprehensive analysis of
that feedback. 

The parallel pattern can reduce overall latency compared to a sequential
approach because it can gather diverse information from multiple sources at the
same time. However, this approach introduces trade-offs in cost and complexity.
Running multiple agents in parallel can increase immediate resource utilization
and token consumption, which leads to higher operational costs. Furthermore, the
gather step requires complex logic to synthesize potentially conflicting
results, which adds to the development and maintenance overhead of the system. 

### Loop pattern

The multi-agent loop agent pattern repeatedly executes a sequence of
specialized subagents until a specific termination condition is met. This
pattern uses a
 loop workflow agent 
that, like other workflow agents, operates on predefined logic without
consulting an AI model for orchestration. After all of the subagents complete
their tasks, the loop agent evaluates whether an exit condition is met. The
condition can be a maximum number of iterations or a custom state. If the
exit condition isn't met, then the loop agent starts the sequence of subagents
again. You can implement a loop pattern where the exit condition is evaluated at
any point in the flow. Use the loop pattern for tasks that require
 iterative refinement 
or self-correction, such as generating content and having a critic agent review
it until it meets a quality standard. 

The following diagram shows a high-level view of a multi-agent loop pattern: 

The loop agent pattern provides a way to build complex, iterative workflows. It
enables agents to refine their own work and continue processing until a specific
quality or state is achieved. However, this pattern's primary trade-off is the
risk of an infinite loop. If the termination condition isn't correctly defined
or if the subagents fail to produce the state that's required to stop, the loop
can run indefinitely. This can lead to excessive operational costs, high
resource consumption, and potential system hangs. 

### Review and critique pattern

The multi-agent review and critique pattern , also known as the generator and
critic pattern , improves the quality and reliability of generated content by
using two specialized agents, typically in a sequential workflow. The review and
critique pattern is an implementation of the
 loop agent pattern . 

In the review and critique pattern, a generator agent creates an initial output,
such as a block of code or a summary of a document. Next, a critic agent
evaluates this output against a predefined set of criteria, such as factual
accuracy, adherence to formatting rules, or safety guidelines. Based on the
evaluation, the critic can approve the content, reject it, or return it to the
generator with feedback for revision. 

The following diagram shows a high-level view of a multi-agent review and
critique pattern: 

This pattern is suitable for tasks where outputs must be highly accurate or must
conform to strict constraints before they're presented to a user or used in a
downstream process. For example, in a code generation workflow, a generator
agent might write a function to fulfill a user's request. This generated code is
then passed to a critic agent that acts as a security auditor. The critic
agent's job is to check the code against a set of constraints, such as scanning
for security vulnerabilities or verifying that it passes all of the unit tests,
before the code is approved for use. 

The reviewer and critique pattern can improve output quality, accuracy, and
reliability because it adds a dedicated verification step. However, this quality
assurance comes at the direct cost of increased latency and operational
expenses. The workflow requires at least one additional model call for the
critic's evaluation. If the process includes revision loops where content is
sent back for refinement, then both latency and costs accumulate with each
iteration. 

### Iterative refinement pattern

The iterative refinement pattern uses a looping mechanism to progressively
improve an output over multiple cycles. The iterative refinement pattern is an
implementation of the loop agent pattern . 

In this pattern, one or more agents work within a loop to modify a result that's
stored in the session state during each iteration. The process continues until
the output meets a predefined quality threshold or it reaches a maximum number
of iterations, which prevents infinite loops. 

The following diagram shows a high-level view of a multi-agent iterative
refinement pattern: 

This pattern is suitable for complex generation tasks where the output is
difficult to achieve in a single step. Examples of such tasks include writing
and debugging a piece of code, developing a detailed multi-part plan, or
drafting and revising a long-form document. For example, in a creative writing
workflow, an agent might generate a draft of a blog post, critique the draft for
flow and tone, and then rewrite the draft based on that critique. This process
repeats in a loop until the agent's work meets a predefined quality standard or
until the repetition reaches a maximum number of iterations. 

The iterative refinement pattern can produce highly complex or polished outputs
that would be difficult to achieve in a single step. However, the looping
mechanism directly increases latency and operational costs with each cycle. This
pattern also adds architectural complexity, because it requires carefully
designed exit conditions—such as a quality evaluation or a maximum iteration
limit—to prevent excessive costs or uncontrolled execution. 

### Coordinator pattern

The multi-agent coordinator pattern uses a central agent, the coordinator ,
to direct a workflow. The coordinator analyzes and decomposes a user's request
into sub-tasks, and then it dispatches each sub-task to a specialized agent for
execution. Each specialized agent is an expert in a specific function, such as
querying a database or calling an API. 

A distinction of the coordinator pattern is its use of an AI model to
orchestrate and dynamically route tasks. By contrast, the parallel
pattern relies on a hardcoded workflow to dispatch tasks for
simultaneous execution without the need for AI model orchestration. 

The following diagram shows a high-level view of a multi-agent coordinator pattern: 

Use the coordinator pattern for automating structured business processes that
require adaptive routing. For example, a customer service agent can act as the
coordinator. The coordinator agent analyzes the request to determine whether
it's an order status request, product return, or refund request. Based on the
type of request, the coordinator routes the task to the appropriate specialized
agent. 

The coordinator pattern offers flexibility compared to more rigid, predefined
workflows. By using a model to route tasks, the coordinator can handle a wider
variety of inputs and adapt the workflow at runtime. However, this approach also
introduces trade-offs. Because the coordinator and each specialized agent rely
on a model for reasoning, this pattern results in more model calls than a
single-agent system. Although the coordinator pattern can lead to higher-quality
reasoning, it also increases token throughput, operational costs, and
overall latency when compared to a single-agent system. 

### Hierarchical task decomposition pattern

The multi-agent hierarchical task decomposition pattern organizes agents into
a multi-level hierarchy to solve complex problems that require extensive
planning. The hierarchical task decomposition pattern is an implementation of
the coordinator pattern . A top-level parent, or root ,
agent receives a complex task and it's responsible for decomposing the task into
several smaller, manageable sub-tasks. The root agent delegates each sub-task to
a specialized subagent at a lower level. This process can repeat through
multiple layers, with agents that progressively decompose their assigned tasks
until they can be executed directly by a worker agent at the lowest level. 

The following diagram shows a high-level view of a multi-agent hierarchical
task decomposition pattern: 

Use the hierarchical task decomposition pattern for ambiguous, open-ended
problems that require multi-step reasoning, such as tasks that involve research,
planning, and synthesis. For example, to complete a complex research project, a
coordinator agent decomposes the high-level goal into multiple tasks such as
gathering information, analyzing the findings, and synthesizing the final
report. The coordinator agent then delegate those tasks to specialized
subagents, such as an agent for data gathering, an analysis agent, and an
agent that writes reports, to execute or further decompose. 

The hierarchical task decomposition pattern is ideal for solving highly complex
and ambiguous problems because it systematically decomposes them into
manageable sub-tasks. This pattern can result in more comprehensive and higher-quality
results than simpler patterns. However, this advanced capability introduces
significant trade-offs. The multi-level structure adds considerable
architectural complexity, which makes the system more difficult to design, debug, and
maintain. The multiple layers of delegation and reasoning also result in a high
number of model calls, which significantly increases both overall latency and
operational costs compared to other patterns. 

### Swarm pattern

The multi-agent swarm pattern uses a collaborative, all-to-all communication
approach. In this pattern, multiple specialized agents work together to iteratively refine a
solution to a complex problem. 

The following diagram shows a high-level view of a multi-agent swarm pattern: 

The swarm pattern uses a dispatcher agent to route a user request to a
collaborative group of specialized agents. The dispatcher agent interprets the
request and it determines which agent in the swarm is best suited to begin the
task. In this pattern, each agent can communicate with every other agent, which
allows them to share findings, critique proposals, and build upon each other's
work to iteratively refine a solution. Any agent in the swarm can hand off the
task to another agent that it determines is better suited to handle the next
step, or it can communicate the final response back to the user through the
coordinator agent. 

A swarm typically lacks a central supervisor or coordinator agent to keep the
process on track. The dispatcher agent doesn't orchestrate the agentic workflow,
unlike the
 coordinator pattern .
Instead, the dispatcher agent facilitates communication between the swarm
subagents and the user. To ensure that the swarm eventually stops and returns a
result, you must define an explicit exit condition. This
condition is often a maximum number of iterations, a time limit, or the
achievement of a specific goal, such as reaching a consensus. 

Use the swarm pattern for ambiguous or highly complex problems that benefit
from debate and iterative refinement. For example, designing a new product could
involve a market researcher agent, an engineering agent, and a financial
modeling agent. The agents would share initial ideas, debate the trade-offs
between features and costs, and collectively converge on a final design
specification that balances all of the competing requirements. 

The swarm pattern simulates a collaborative team of experts, therefore it can
produce exceptionally high-quality and creative solutions. However, it
represents the most complex and costly multi-agent pattern to implement. The
lack of an agent that uses an AI model to orchestrate can introduce the risk of
unproductive loops or the failure to converge on a solution. You must therefore
design sophisticated logic to manage the intricate inter-agent communication,
control the iterative workflow, and handle the significant operational costs and
latency that are associated with running a dynamic, multi-turn conversation
between multiple agents. 

### Reason and act (ReAct) pattern

The ReAct pattern is an approach that uses the AI model to frame
its thought processes and actions as a sequence of natural language
interactions. In this pattern, the agent operates in an iterative loop of
thought, action, and observation until an exit condition is met. 

 Thought : The model reasons about the task and it decides what to do
next. The model evaluates all of the information that it's gathered in order
to determine whether the user's request has been fully answered. 
 Action : Based on its thought process, the model takes one of two
actions:

 If the task isn't complete, it selects a tool and then it forms a query to
gather more information. 
 If the task is complete, it formulates the final answer to send to the user,
which ends the loop. 

 Observation : The model receives the output from the tool and it saves
relevant information in its memory. Because the model saves relevant output,
it can build on previous observations, which helps to prevent the model from
repeating itself or losing context. 

The iterative loop terminates when
the agent finds a conclusive answer, reaches a preset maximum number of
iterations, or encounters an error that prevents it from continuing.
This iterative loop lets the agent dynamically build a plan, gather evidence,
and adjust its approach as it works toward a final answer. 

The following diagram shows a high-level view of the ReAct pattern: 

Use the ReAct pattern for complex, dynamic tasks that require continuous
planning and adaptation. For example, consider a robotics agent that must
generate a path to transition from an initial state to a goal state: 

 Thought : The model reasons about the optimal path to transition from its
current state to the goal state. During the thought process, the model
optimizes for metrics like time or energy. 
 Action : The model executes the next step in its plan by moving along a
calculated path segment. 
 Observation : The model observes and saves the new state of the
environment. The model saves its new position and any changes to the
environment that it perceives. 

This loop allows the agent to adhere to dynamic constraints, such as avoiding
new obstacles or following traffic regulations, by constantly updating its plan
based on new observations. The agent continues through its iterative loop until
it reaches its goal or encounters an error. 

A single ReAct agent can be simpler and more cost-effective to implement and
maintain than a complex multi-agent system. Model thinking provides a transcript
of the model's reasoning, which helps with debugging. However, this flexibility
introduces trade-offs. The iterative, multi-step nature of the loop can lead to
higher end-to-end latency compared to a single query. Furthermore, the agent's
effectiveness is highly dependent on the quality of the AI model's reasoning.
Therefore, an error or a misleading result from a tool in one observation step
can propagate and cause the final answer to be incorrect. 

### Human-in-the-loop pattern

The human-in-the-loop pattern integrates points for human intervention directly
into an agent's workflow. At a predefined checkpoint, the agent pauses its
execution and calls an external system to wait for a person to review its work.
This pattern lets a person approve a decision, correct an error, or provide
necessary input before the agent can continue. 

The following diagram shows a high-level view of a human-in-the-loop pattern: 

Use the human-in-the-loop pattern for tasks that require human oversight,
subjective judgment, or final approval for critical actions. Such actions
include approving a large financial transaction, validating the summary of a
sensitive document, or providing subjective feedback on generated creative
content. For example, an agent might be tasked with anonymizing a patient
dataset for research. The agent would automatically identify and redact all
protected health information, but it would pause at a final checkpoint. It would
then wait for a human compliance officer to manually validate the dataset and
approve its release, which helps to ensure that no sensitive data is exposed. 

The human-in-the-loop pattern improves safety and reliability by inserting
human judgment into critical decision points within the workflow. This pattern
can add significant architectural complexity because it requires you to build
and maintain the external system for user interaction. 

### Custom logic pattern

The custom logic pattern provides the maximum flexibility in your workflow
design. This approach lets you implement specific orchestration logic that uses
code, such as conditional statements, to create complex workflows with multiple
branching paths. 

The following diagram illustrates an example use of a custom logic pattern to
capture a refund process: 

In the preceding diagram, the following is the agentic workflow for the example
customer refund agent: 

 The user sends a query to the customer refund agent that acts as a
coordinator agent. 
 The coordinator's custom logic first invokes a parallel verifier agent,
which simultaneously dispatches two subagents: the purchaser verifier agent
and the refund eligibility agent. 
 After the results are gathered, the coordinator agent executes a tool to
check whether the request is eligible for a refund.

 If the user is eligible, then the coordinator routes the task
to a refund processor agent, which calls the process_refund tool. 
 If the user isn't eligible, then the coordinator routes the
task to a separate sequential flow, starting with the store credit
agent and the process credit decision agent. 

 The result from whichever path is taken is sent to the final response agent
to formulate the answer for the user. 

The customer refund agent example requires a unique solution for its logic-level
orchestration, which goes beyond the structured approaches that other patterns
offer. This workflow mixes patterns because it runs a parallel check, and then
it executes a custom conditional branch that routes to two entirely different
downstream processes. This type of complex, mixed-pattern workflow is the ideal
use case for the custom logic pattern. 

Use the custom logic pattern when you need fine-grained control over the agent's
execution or when your workflow doesn't fit one of the other patterns that's
described in this document. However, this approach increases development and
maintenance complexity. You are responsible for designing, implementing, and
debugging the entire orchestration flow, which requires more development effort
and can be more error-prone than using a predefined pattern that is supported by
a tool like
 Agent Development Kit (ADK) . 

For information about custom agents and how to implement custom logic using ADK, see
 Custom agents . 

### Compare design patterns

Choosing an agent pattern is a fundamental architectural decision. Each pattern
offers different trade-offs in flexibility, complexity, and performance. To
determine the appropriate pattern for your workload, consider the design
patterns in the following sections. 

### Workflows that are deterministic

Workflows that are deterministic include tasks that are predictable and
sequential, and that have a clearly defined workflow path from start to finish.
The steps in your tasks are known in advance, and the process doesn't change
much from one run to the next. 

The following are agent design patterns for workflows that are deterministic: 

 Multi-agent sequential pattern 

Use this pattern if your workload has the following characteristics: 

 Multi-step tasks that follow a predefined, rigid workflow. 
 Doesn't require model orchestration. 
 Fixed sequence of operations. The output of one agent is the direct
 input of the next agent in the sequence. 

 Multi-agent parallel pattern 

Use this pattern if your workload has the following characteristics: 

 Independent tasks that can be executed at the same time. 
 Doesn't require model orchestration. 
 Reduces overall latency by running sub-tasks simultaneously. 

 Multi-agent iterative
 refinement pattern 

Use this pattern if your workload has the following characteristics: 

 Open-ended or complex generation tasks that are difficult to complete
 in a single attempt. 
 Requires the agent to progressively improve the output over multiple
 cycles. 
 Doesn't require model orchestration. 
 Prioritizes output quality over latency. 

### Workflows that require dynamic orchestration

Workflows that require dynamic orchestration involve complex problems where
agents must decide how to proceed. In these workflows, the agentic AI system
dynamically plans, delegates, and coordinates tasks without a script. 

The following are agent design patterns for workflows that require dynamic
orchestration: 

 Single agent pattern 

Use this pattern if your workload has the following characteristics: 

 Structured and multi-step tasks that require the use of external tools.

 Requires fast development for a prototype of a solution as a proof of
 concept. 

 Multi-agent coordinator pattern 

Use this pattern if your workload has the following characteristics: 

 Requires dynamic routing to an appropriate specialized subagent for
 structured tasks with varied input. 
 High latency due to multiple calls to the coordinator AI model so that
 it can direct tasks to the appropriate subagent. 
 Can incur high cost due to multiple calls to the coordinator agent. 

 Multi-agent
 hierarchical task decomposition pattern 

Use this pattern if your workload has the following characteristics: 

 Requires multi-level model orchestration for complex, open-ended, and
 ambiguous tasks. 
 Requires comprehensive, high-quality results where decomposing
 ambiguity is the primary challenge. 
 High latency due to nested, multi-level decomposition that leads to
 multiple calls to the AI model for reasoning. 

 Multi-agent swarm pattern 

Use this pattern if your workload has the following characteristics: 

 Requires collaborative debate and iterative refinement from multiple
 specialized agents for highly complex, open-ended, or ambiguous tasks.

 Prioritizes the synthesis of multiple perspectives to create a
 comprehensive or creative solution. 
 High latency and operational costs due to dynamic, all-to-all
 communication between agents. 

### Workflows that involve iteration

Workflows that involve iteration include tasks where the final output is
achieved through cycles of refinement, feedback, and improvement. 

The following are agent design patterns for workflows that involve iteration: 

 ReAct pattern 

Use this pattern if your workload has the following characteristics: 

 Requires an agent to iteratively reason, act, and observe to build or
 adapt a plan for complex, open-ended, and dynamic tasks. 
 Prioritizes a more accurate and thorough result over latency. 

 Multi-agent loop pattern 

Use this pattern if your workload has the following characteristics: 

 Requires monitoring or polling tasks that repeat a predefined action,
 such as automated checks, until the agent meets an exit condition. 
 Unpredictable or long-running latency while waiting for an exit
 condition to be met. 

 Multi-agent review and critique
 pattern 

Use this pattern if your workload has the following characteristics: 

 Tasks require a distinct validation step before completion. 

 Multi-agent iterative
 refinement pattern 

Use this pattern if your workload has the following characteristics: 

 Open-ended or complex generation tasks that are difficult to complete
 in a single attempt. 
 Requires the agent to progressively improve the output over multiple
 cycles. 
 Doesn't require model orchestration. 
 Prioritizes output quality over latency. 

### Workflows that have special requirements

Workflows that have special requirements include tasks that don't follow common
agentic patterns. Your tasks can include unique business logic or require human
judgment and intervention at critical points. In this case, your agentic AI
system is custom-built for a single, specific purpose. 

The following are agent design patterns for workflows that have special
requirements: 

 Human-in-the-loop pattern 

Use this pattern if your workload has the following characteristics: 

 Requires human supervision due to high-stakes or subjective tasks
 that might include safety, reliability, and compliance requirements. 

 Custom logic pattern 

Use this pattern if your workload has the following characteristics: 

 Complex, branching logic that goes beyond a direct linear sequence.

 Requires maximum control to mix predefined rules with model reasoning.

 Requires fine-grained process control for a workflow that doesn't fit
 a standard template. 

### What's next

 Learn more about how to construct and manage multi-agent systems using ADK primitives . 
 Learn how to
 host AI apps and agents on Cloud Run . 
 Learn more about
 Agentic Design Patterns: A Hands-On Guide to Building Intelligent Systems . 
 Learn how to
 build an agent with ADK . 
 Learn more about how to build
 multi-agent AI systems in Google Cloud . 

For more reference architectures, diagrams, and best practices, explore the
 Cloud Architecture Center .

### Contributors

Author: Samantha He | Technical Writer 
Other contributors:
 Abdul Saleh | Software Engineer Amina Mansour | Tech Lead, Global Developer Relations & Strategic Content Amit Maraj | Developer Relations Engineer Casey West | Architecture Advocate, Google Cloud Jack Wotherspoon | Developer Advocate Joe Fernandez | Staff Technical Writer Joe Shirey | Cloud Developer Relations Manager Karl Weinmeister | Director of Cloud Product Developer Relations Kumar Dhanagopal | Cross-Product Solution Developer Lisa Shen | Senior Outbound Product Manager, Google Cloud Mandy Grover | Head of Architecture Center Mark Lu | Technical Writer Megan O'Keefe | Developer Advocate Olivier Bourgeois | Developer Relations Engineer Shir Meir Lador | Developer Relations Engineering Manager Vlad Kolesnikov | Developer Relations Engineer 

Was this helpful? 

 Send feedback

Except as otherwise noted, the content of this page is licensed under the Creative Commons Attribution 4.0 License , and code samples are licensed under the Apache 2.0 License . For details, see the Google Developers Site Policies . Java is a registered trademark of Oracle and/or its affiliates. 

Last updated 2026-05-28 UTC. 

 Need to tell us more?

 [[["Easy to understand","easyToUnderstand","thumb-up"],["Solved my problem","solvedMyProblem","thumb-up"],["Other","otherUp","thumb-up"]],[["Hard to understand","hardToUnderstand","thumb-down"],["Incorrect information or sample code","incorrectInformationOrSampleCode","thumb-down"],["Missing the information/samples I need","missingTheInformationSamplesINeed","thumb-down"],["Other","otherDown","thumb-down"]],["Last updated 2026-05-28 UTC."],[],[]]

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