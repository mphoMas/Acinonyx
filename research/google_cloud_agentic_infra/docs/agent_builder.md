# Gemini Enterprise Agent Platform (formerly Vertex AI) | Google Cloud

**Source URL:** https://cloud.google.com/products/agent-builder

---

Gemini Enterprise Agent Platform (formerly Vertex AI) | Google Cloud 

 Page Contents 

 Gemini Enterprise Agent Platform Features How It Works Common Uses Build and deploy AI agents Build with Gemini models Extract, summarize, and classify data Deploy a model for production use Train custom Models Generate a solution Pricing Business Case 
 Try Gemini in Agent Platform Documentation Sample code and notebooks Release notes 

All the power of Vertex AI you know and love, now within Gemini Enterprise Agent Platform. Read more in our announcement blog. 

### Gemini Enterprise Agent Platform 

### Innovate, build, and deploy enterprise ready agents

Gemini Enterprise Agent Platform is Google Cloud's comprehensive platform for developers to build, scale, govern and optimize agents. It's a single destination for technical teams to build agents that can transform enterprise applications and workflows into powerful agentic systems. 
 New customers get up to $300 in free credits to try Agent Platform and other Google Cloud products.  

 Try Agent Platform free 

 Contact sales 

### Product highlights

Accelerate agent development with unified data and AI 

Build generative AI apps quickly with Gemini 

Train, test, and tune ML models on a single platform 

From tokenmaxxing to ROI: See who is gaining the most ROI from AI and strategies that you can follow. 
Read the report 

Features 

### Build, scale, govern, and optimize enterprise grade AI agents

 Agent Platform is our open and comprehensive platform that empowers businesses to rapidly build, scale, govern and optimize enterprise-grade agents grounded in your enterprise data. It provides the full-stack foundation and extensive developer choice you need to transform your applications and workflows into powerful agentic systems at global scale. 

Scale agents from Agent Platform to your organization 
Use Gemini Enterprise app to securely register, manage, and govern your custom-built agents. 
 Learn about Gemini Enterprise app 

### Agent-powered development and workflows

Now available through Agent Platform, Google Antigravity provides a centralized app to steer, customize, and orchestrate agents. You can deploy multiple agents to simultaneously execute entire workflows like product launches—automating the code generation for your website, on-brand asset creation, and customer email production.  Download Antigravity and log in to the desktop application or Antigravity CLI using your standard Google Cloud credentials. 

### 200+ Google and third-party AI models and tools

Choose from Google’s latest multimodal models like Gemini 3.7 Flash, third-party models like Anthropic's Claude Model Family, and open models like Gemma in Model Garden . You can also customize models to your use case with a variety of tuning options . 
Our Model Evaluation service provides enterprise-grade tools for objective, data-driven assessment of generative AI models. 

Register to learn how AI agents are serving as dual engines for both cost savings and revenue generation 

### Open and integrated AI platform

Data scientists can move faster with Agent Platform tools for training, tuning, and deploying ML models. 
Agent platform notebooks , including your choice of Colab Enterprise or Workbench, are natively integrated with BigQuery providing a single surface across all data and AI workloads. 
Agent platform T raining and Prediction help you reduce training time and deploy models to production easily with your choice of open source frameworks and optimized AI infrastructure . 

### MLOps for predictive and generative AI

Agent Platform provides purpose-built MLOps tools for data scientists and ML engineers to automate, standardize, and manage ML projects. 
Modular tools help you collaborate across teams and improve models throughout the entire development lifecycle—identify the best model for a use case with Model Evaluation , orchestrate workflows with Pipelines , manage any model with Model Registry serve, share, and reuse ML features with Feature Store , and monitor models for input skew and drift. 

MLOps with Agent Platform: Model Evaluation 
No cost training 
 Get started 

How It Works 

### 

Agent Platform provides several options for agent building, model training and deployment: Agent Platform enables you to build, scale, govern and optimize enterprise ready agents in one unified platform Agent Studio gives you access to large generative AI models, including Gemini 3 , so you can evaluate, tune, and deploy them for use in your AI-powered applications Model Garden  lets you discover, test, customize, and deploy in Agent Platform and select open-source (OSS) models and assets Custom training  gives you complete control over the training process, including using your preferred ML framework, writing your own training code, and choosing hyperparameter tuning options 

 View documentation 

Common Uses 

### Build and deploy AI agents 

### Tutorials, quickstarts, & labs

### 

Unlock advanced AI capabilities with Agent Platform 

Build production-ready generative AI agents and applications on a platform that scales with you. Our Agent Platform provides a secure environment for developing and deploying AI models and applications. 
For developers, Agent Platform remains our advanced platform where you can build, customize, and fine-tune sophisticated agents using frameworks like the Agent Development Kit (ADK) . 

 View documentation 

View available models in Agent Platform 

101 real-world gen AI use cases with technical blueprints 

 Design agents in Agent Studio 

Get started with this codelab and build your first AI application today 

### Tutorials, quickstarts, & labs

### 

Unlock advanced AI capabilities with Agent Platform 

Build production-ready generative AI agents and applications on a platform that scales with you. Our Agent Platform provides a secure environment for developing and deploying AI models and applications. 
For developers, Agent Platform remains our advanced platform where you can build, customize, and fine-tune sophisticated agents using frameworks like the Agent Development Kit (ADK) . 

 View documentation 

View available models in Agent Platform 

101 real-world gen AI use cases with technical blueprints 

 Design agents in Agent Studio 

Get started with this codelab and build your first AI application today 

### Build with Gemini models

### Tutorials, quickstarts, & labs

### Code sample

### 

Start building with Agent Studio 

Use Agent Studio to design, test, and manage prompts for Gemini models using natural language, code, images, or video. Try sample prompts for extracting text from images, image mock up to HTML, and even generate answers about uploaded images or videos. 
You can also start testing Gemini on Agent Platform with an API key . 

 Try Gemini on Agent Platform 

Set up the Agent Platform Gemini API 

 Guides and examples for building with Gemini models 

Featured Gemini models 

### 
Access Gemini models via the Gemini API in Agent Platform 

View code samples for Python, JavaScript, Java, Go, and Curl 

<div jsshadow="" class="rHGeGc-O1htCb-H9tDt DSMYFc RVFEFe" jsname="mNEYde" jscontroller="GPHYJd" jsaction="iFFCZc:Y0y4c;
 Rld2oe:gDkf4c;
 EDR5Je:QdOKJc;
 FzgWvd:RFVo1b;" data-is-menu-deferred="false" data-is-menu-hoisted="false" data-use-native-validation="true" data-stable-unique-label-id="ucj-5">

 Python 

 Python 
 JavaScript 
 Java 
 Go 
 Curl 

 from google import genai

client = genai.Client()

response = client.models.generate_content(
 model="gemini-2.5-flash",
 contents="Explain how AI works in a few words",
)

print(response.text) 

 contents = "Explain how AI works in a few words" , 

 content_copy 

 View more code samples 

Set up the Agent Platform Gemini API 

Learn multimodal design best practices 

 Repository for sample code and notebooks 

### Tutorials, quickstarts, & labs

### 

Start building with Agent Studio 

Use Agent Studio to design, test, and manage prompts for Gemini models using natural language, code, images, or video. Try sample prompts for extracting text from images, image mock up to HTML, and even generate answers about uploaded images or videos. 
You can also start testing Gemini on Agent Platform with an API key . 

 Try Gemini on Agent Platform 

Set up the Agent Platform Gemini API 

 Guides and examples for building with Gemini models 

Featured Gemini models 

### Code sample

### 
Access Gemini models via the Gemini API in Agent Platform 

View code samples for Python, JavaScript, Java, Go, and Curl 

<div jsshadow="" class="rHGeGc-O1htCb-H9tDt DSMYFc RVFEFe" jsname="mNEYde" jscontroller="GPHYJd" jsaction="iFFCZc:Y0y4c;
 Rld2oe:gDkf4c;
 EDR5Je:QdOKJc;
 FzgWvd:RFVo1b;" data-is-menu-deferred="false" data-is-menu-hoisted="false" data-use-native-validation="true" data-stable-unique-label-id="ucj-10">

 Python 

 Python 
 JavaScript 
 Java 
 Go 
 Curl 

 from google import genai

client = genai.Client()

response = client.models.generate_content(
 model="gemini-2.5-flash",
 contents="Explain how AI works in a few words",
)

print(response.text) 

 contents = "Explain how AI works in a few words" , 

 content_copy 

 View more code samples 

Set up the Agent Platform Gemini API 

Learn multimodal design best practices 

 Repository for sample code and notebooks 

### Extract, summarize, and classify data

### Tutorials, quickstarts, & labs

### 

Use gen AI for summarization, classification, and extraction 

Learn how to create text prompts for handling any number of tasks with Agent Platform's generative AI support. Some of the most common tasks are classification, summarization, and extraction. Gemini on Agent Platform lets you design prompts with flexibility in terms of their structure and format. 

 View text prompt design docs 

Overview of prompting strategies 

Learn about AI-powered prompt writing tools in Agent Studio 

View all generative AI prompt samples 

### Tutorials, quickstarts, & labs

### 

Use gen AI for summarization, classification, and extraction 

Learn how to create text prompts for handling any number of tasks with Agent Platform's generative AI support. Some of the most common tasks are classification, summarization, and extraction. Gemini on Agent Platform lets you design prompts with flexibility in terms of their structure and format. 

 View text prompt design docs 

Overview of prompting strategies 

Learn about AI-powered prompt writing tools in Agent Studio 

View all generative AI prompt samples 

### Deploy a model for production use

### Tutorials, quickstarts, & labs

### 

Deploy for batch or online predictions 

When you're ready to use your model to solve a real-world problem, register your model to Model Registry and use the Agent Platform prediction service for batch and online predictions.  

 Learn how to get predictions from an ML model 

Get hands on with a Agent Platform Predictions codelab 

Simplify model serving with custom prediction routines 

Use prebuilt containers for prediction and explanation 

Watch Prototype to Production , a video series that takes you from notebook code to a deployed model. 

### Tutorials, quickstarts, & labs

### 

Deploy for batch or online predictions 

When you're ready to use your model to solve a real-world problem, register your model to Model Registry and use the Agent Platform prediction service for batch and online predictions.  

 Learn how to get predictions from an ML model 

Get hands on with a Agent Platform Predictions codelab 

Simplify model serving with custom prediction routines 

Use prebuilt containers for prediction and explanation 

Watch Prototype to Production , a video series that takes you from notebook code to a deployed model. 

### Train custom Models

### Tutorials, quickstarts, & labs

### 

Custom Model training overview and documentation 

Get an overview of the custom training workflow in Agent Platform, the benefits of custom training, and