# Arepas Project Status Report
**Date:** January 7, 2026  
**Project:** Fine-Tuning AI for Historical Architectural Building Classification

---

## 1. Current State of the Project

### Overview
Arepas has successfully reached a strong technical foundation stage. We have built an enterprise-grade data loading and preprocessing infrastructure designed specifically for fine-tuning an AI vision model (OpenAI Vision) to categorize historical architectural buildings based on multiple attributes from the **Discover Denver Schema**.

### Current Capabilities

#### ✅ Completed Infrastructure
- **High-Performance Data Loading System**: Successfully processes building data with associated images at 1.0ms per building
- **Schema Integration**: Full integration with the 55-field Discover Denver Schema, including field types, validation rules, and valid options
- **Multi-Dataset Support**: Handles complex data structures across 19 datasets covering multiple neighborhoods and architectural styles
- **Image Management**: Efficient hash-based image indexing system that links building records to their photographs
- **Validation Framework**: Intelligent threshold-based validation system that flags data quality issues while maintaining flexibility

#### 📊 Data Processing Metrics
- **198 buildings** successfully loaded and processed
- **717+ images** indexed and matched to building records
- **98.4% image coverage** (176 out of 198 buildings have associated images)
- **19 datasets** across 2 architectural styles (Bungalows, Minimal Traditional)
- **Processing speed**: 1.0ms per building average

#### 🏛️ Architectural Styles & Neighborhoods Covered
**Style-Based Organization (data/ folder):**
- Bungalows: 9 neighborhoods (Clayton, Cole, Regis, Skyland, South City Park, Sunnyside, Villa Park, Westwood, Whittier)
- Minimal Traditional: 10 neighborhoods (Barnum, Clayton, Cole, Regis, Skyland, South City Park, Sunnyside, Valverde, Villa Park, Westwood)

**Neighborhood-Based Organization (data2/ folder):**
- Cole, Regis, Skyland, South City Park, Sunnyside
- Streetcar Commercial (3 locations: Gaylord, Pearl, Tennyson)

### Technical Architecture
The project uses a modular Python architecture with:
- **Configurable data loader** driven by JSON configuration files
- **Robust CSV parsing** with error recovery
- **Schema-based validation** with intelligent thresholds
- **Type-safe operations** throughout the codebase
- **Advanced logging** for debugging and monitoring

### Current Stage in Workflow
According to our project workflow, we are currently at **Stage 4: Schema Validation** and preparing for **Stage 5: Data Splitting**.

**Completed Stages:**
1. ✅ Project Setup
2. ✅ Load Datasets
3. ✅ Load Schema
4. ✅ Schema Validation (in progress)

**Next Stages:**
5. ⏭️ Split Train/Validation
6. ⏭️ Write Prompts
7. ⏭️ Fine-tune Model (iterative)

---

## 2. Detailed Summary: What We've Learned from Data Gathering

### Key Discoveries About the Dataset

#### 2.1 Data Structure Insights
Through our comprehensive data loading and validation work, we've uncovered several critical insights:

**Data Completeness Analysis:**
- The current dataset in our pipeline contains **minimal schema field coverage** - all 55 Discover Denver Schema fields show 0% coverage in the loaded records
- This suggests our CSV files contain **administrative and metadata fields** (id, address, city, coordinates, etc.) but **lack the architectural attribute fields** needed for classification
- However, examining the raw CSV files directly reveals that **full survey records DO contain rich architectural data** including:
  - Original Use, Current Use, Building Form, Architectural Style
  - Physical attributes: Stories, Roof Type, Roof Materials, Primary Cladding
  - Alterations and integrity assessments
  - Complex multipart fields (Window, Entrance, Chimney)
  - Historical narratives and significance statements

**This reveals an important finding**: Our data loading configuration may need adjustment to properly map the CSV columns to schema fields, OR we need to shift focus to the full survey records that contain complete architectural data.

#### 2.2 Data Quality Patterns

**Image Coverage:**
- Excellent: 98.4% of buildings have associated photographs (176 of 198)
- Most buildings have multiple images (3-8 photos per building on average)
- Images follow consistent naming convention: `{smithsonianNumber}_{address}.{randomHash}.jpg`
- Total of 717+ images available for training

**Survey Levels Represented:**
The data includes buildings surveyed at different levels:
- **Basic Survey**: Quick architectural assessment (most common in our current dataset)
- **Full Survey**: Comprehensive documentation with historical research (e.g., 3535 N Elizabeth St - the Colby Brothers House with extensive historical narrative)

#### 2.3 Architectural Classification Opportunities

**Rich Classification Attributes Available:**
From examining full survey records, we have access to:

1. **Physical Characteristics** (24 required fields):
   - Building Form (Bungalow, etc.)
   - Roof Type (Cross Gable, Hip-on-Gable, Hipped, etc.)
   - Primary Cladding (Brick with variations)
   - Stories (1, 1-1/2)
   - Setting (Set Back from Sidewalk)
   - Alterations across 5 categories (Additions, Entrances, Roof, Cladding, Windows)

2. **Multipart Features** (complex nested data):
   - **Windows**: Type (Double/Single Hung, Casement, Fixed), Features (Cottage Window, Divided Lights, Rowlock Sill), Location
   - **Entrances**: Type (Porch configurations), Location
   - **Chimneys**: Placement, Material, Features

3. **Style & Period**:
   - Architectural Style (Craftsman, No Clear Architectural Style, etc.)
   - Year Built (ranging from 1910s-1920s in current data)
   - Original vs. Current Use

4. **Preservation Context**:
   - Integrity Rating and Alteration Level (scale of 1-5)
   - National Register (NR) eligibility
   - Local designation potential
   - Assessment of Integrity (qualitative)

#### 2.4 Historical Context Discovered

**Significant Pattern - Colby Brothers Development:**
One full survey record (3535 N Elizabeth St) revealed a fascinating development pattern:
- Colby Brothers (Charles E. and Willis W. Colby) were brick manufacturers
- They platted an entire subdivision (Colby Subdivision, 1900)
- Built most houses on the 3500 blocks of Columbine and Elizabeth Streets
- Used their own brick in construction, creating architectural consistency
- Represents potential **architectural district** or **builder study opportunity**

This suggests similar patterns may exist throughout the dataset that could inform:
- District-level classification
- Builder/architect attribution
- Material and construction technique analysis

#### 2.5 Data Challenges Identified

**Field Coverage Gap:**
- Current loader configuration captures only 0/55 schema fields
- Need to either:
  - Adjust CSV-to-schema field mapping
  - Focus on full survey records only
  - Investigate why schema fields aren't being extracted

**Missing Images:**
- 22 buildings lack associated images (mostly in Villa Park and Valverde neighborhoods)
- May need supplementary photo collection or exclusion from vision model training

**Survey Level Variability:**
- Basic surveys lack historical narrative and detailed significance assessments
- Full surveys provide comprehensive data but are fewer in number
- Need to determine minimum data requirements for effective model training

---

## 3. Next Direction: Where the Project is Going

### Immediate Next Steps (Weeks 1-4)

#### Phase 1: Data Mapping Correction & Validation
**Priority: Critical**
1. **Investigate and fix the schema field mapping issue** that's resulting in 0% coverage
   - Review CSV column headers vs. schema field names
   - Adjust `configurable_loader.py` or JSON configuration to properly extract architectural attributes
   - Re-run validation to confirm schema fields are being populated

2. **Conduct full data audit** once mapping is fixed
   - Generate new field coverage report
   - Identify which architectural attributes have sufficient data for training
   - Document data completeness by survey level

3. **Curate training dataset**
   - Filter to buildings with images AND adequate schema field coverage
   - Decide on minimum field requirements (e.g., must have: Original Use, Building Form, Roof Type, Primary Cladding, Architectural Style)
   - Target: 150-180 buildings with complete data

#### Phase 2: Data Split & Organization
**Priority: High**
1. **Implement train/validation split** (80/20 or 70/30)
   - Stratify by architectural style and neighborhood to ensure representation
   - Ensure both sets have diverse examples of each classification category
   - Document split methodology

2. **Format data for OpenAI Vision fine-tuning**
   - Research OpenAI's current fine-tuning data format requirements
   - Create conversion scripts from our data structure to OpenAI format
   - Package images with corresponding attribute labels

### Medium-Term Goals (Months 2-3)

#### Phase 3: Prompt Engineering & Initial Model Training
**The Iterative Loop Begins**

1. **Develop classification prompts**
   - Start with high-level categories (Building Form, Architectural Style)
   - Design prompts that guide the model to identify visual features
   - Create validation prompts to test model understanding

2. **First fine-tuning iteration**
   - Train OpenAI Vision model on Building Form classification (e.g., Bungalow vs. other forms)
   - Use training set to teach, validation set to evaluate
   - Measure accuracy and identify failure patterns

3. **Iterative refinement**
   - Analyze where model struggles (e.g., distinguishing Craftsman vs. No Clear Style)
   - Refine prompts to emphasize discriminating visual features
   - Potentially add more training examples for challenging categories
   - Repeat fine-tuning with improved prompts

4. **Expand classification scope**
   - Once Building Form works well (target: >85% accuracy), add additional attributes:
     - Roof Type (Cross Gable, Hip-on-Gable, Hipped)
     - Primary Cladding (Brick variations)
     - Architectural Style
   - Eventually tackle complex multipart features (Window types, Entrance configurations)

### Long-Term Vision (Months 4-6)

#### Phase 4: Production Model & API Development

1. **Multi-attribute classification model**
   - Single model that can identify 10-15 key architectural attributes from images
   - Confidence scores for each prediction
   - Handle edge cases (ambiguous styles, altered buildings)

2. **API Development**
   - RESTful API endpoints for:
     - Single image classification
     - Batch processing
     - Comparison with human-labeled data
   - Integration with existing architectural survey databases

3. **Validation & Refinement**
   - Test against held-out test set (if data allows, create 3-way split)
   - Compare model predictions to expert architectural historian assessments
   - Document model limitations and use cases

#### Phase 5: Expansion & Applications

1. **Scale to additional data**
   - Process more neighborhoods and architectural styles
   - Potentially expand beyond Denver to other cities
   - Handle different survey formats and schemas

2. **Research applications**
   - Automated preliminary building surveys
   - Historic district analysis and boundary refinement
   - Identification of at-risk historic resources
   - Pattern detection (builder signatures, regional style variations)

3. **Tool development**
   - Web interface for architectural historians
   - Mobile app for field surveys
   - Integration with GIS mapping systems

---

## 4. Additional Opportunities

### Research & Academic Opportunities

1. **Historic Preservation Applications**
   - **Rapid survey augmentation**: Use AI to pre-classify buildings before historian review, dramatically reducing survey time
   - **District identification**: Analyze large areas to identify potential historic districts based on architectural consistency
   - **Integrity assessment**: Train model to detect alterations and assess preservation integrity from photos
   - **At-risk building monitoring**: Periodic re-photography and AI analysis to detect unauthorized alterations

2. **Architectural History Research**
   - **Builder/architect attribution**: Identify signatures of specific builders (like the Colby Brothers pattern we found) across large datasets
   - **Style evolution studies**: Track how architectural styles spread geographically and changed over time
   - **Material culture analysis**: Study regional preferences for materials and construction techniques
   - **Economic history**: Correlate building quality/style with historical economic data by neighborhood

3. **Urban Planning & Policy**
   - **Demolition/alteration impact modeling**: Predict what architectural character would be lost from proposed changes
   - **Infill compatibility**: Assess whether new construction proposals fit neighborhood architectural character
   - **Tourism development**: Identify and map architecturally significant corridors for heritage tourism
   - **Property value analysis**: Correlate architectural style/integrity with market values

### Technical Innovation Opportunities

1. **Multi-Modal AI Integration**
   - Combine vision model with text analysis of historical narratives
   - Cross-reference predictions with historical permit data, census records, newspaper archives
   - Create timeline visualizations showing neighborhood development patterns

2. **Crowdsourcing & Citizen Science**
   - Public web interface where community members can upload photos for analysis
   - Gamified validation system where users confirm/correct AI predictions
   - Build larger training dataset through community engagement

3. **Generative AI Applications**
   - Generate architectural descriptions from images for survey reports
   - Create synthetic training examples of rare architectural features
   - Restoration visualization: Show how altered buildings might have originally appeared

### Partnerships & Funding Opportunities

1. **Preservation Organizations**
   - **National Trust for Historic Preservation**: Tool could support their advocacy and survey programs nationwide
   - **State Historic Preservation Offices (SHPOs)**: 50 states conduct surveys; all could benefit from AI-assisted workflow
   - **Historic Denver**: Local partner for testing and validation

2. **Academic Collaborations**
   - **Architecture/Historic Preservation programs**: Joint research projects, student involvement
   - **Computer Science/AI programs**: Benchmark dataset for vision model research
   - **Digital Humanities initiatives**: Model for applying AI to cultural heritage documentation

3. **Government & Non-Profit Funding**
   - **National Endowment for the Humanities (NEH)**: Digital Humanities Advancement Grants
   - **National Park Service**: Historic Preservation Fund grants
   - **IMLS (Institute of Museum and Library Services)**: Collections care and management grants
   - **State humanities councils**: Public programs using the technology

### Scalability & Commercialization

1. **Software-as-a-Service Model**
   - Subscription service for preservation consultants and municipal planning departments
   - Tiered pricing based on usage volume
   - API access for integration with existing survey software

2. **Training & Consulting Services**
   - Workshops teaching architectural historians how to use AI tools
   - Custom model training for specific regions or building types
   - Consulting on digitization and data management for historic surveys

3. **Dataset Licensing**
   - Our curated, validated architectural image dataset has value for AI research
   - Benchmark dataset for computer vision in cultural heritage
   - Educational licensing for universities

---

## 5. How the Committee Can Best Support Us Right Now

### Critical Support Needs (Immediate)

#### 1. Data Quality Validation & Expert Review
**What we need:** Access to architectural historians or preservation specialists who can:
- Review a sample of our building records to confirm our understanding of schema fields
- Validate that our interpretation of architectural terms is correct (e.g., "Building Form" vs. "Architectural Style")
- Help prioritize which attributes are most critical for initial classification
- Provide guidance on acceptable accuracy thresholds for different use cases

**Why it matters:** We're about to begin prompt engineering and model training. Having expert validation now will prevent us from training the model on incorrect interpretations of architectural terminology.

**Time commitment:** 2-4 hours initially; then periodic consultation during model development

#### 2. Technical Guidance on OpenAI Vision Fine-Tuning
**What we need:** Someone with experience in:
- OpenAI's current vision model fine-tuning API (API changes frequently)
- Best practices for formatting training data for vision tasks
- Prompt engineering strategies for architectural/visual classification
- Managing iterative fine-tuning cycles and avoiding overfitting

**Why it matters:** We have strong data infrastructure but need expertise in the specific ML platform we're using. This will accelerate our move from "data ready" to "model training."

**Time commitment:** 3-5 hours consultation + availability for questions during training

#### 3. Data Mapping Troubleshooting
**What we need:** Help investigating why our schema fields show 0% coverage:
- Code review of our CSV-to-schema mapping logic
- Comparison of raw CSV data with schema expectations
- Guidance on handling inconsistent field names across survey types

**Why it matters:** This is currently blocking our progress to the next workflow stage. Without properly mapped data, we cannot train the model.

**Time commitment:** 2-3 hours paired troubleshooting session

### Strategic Support Needs (Next 1-2 Months)

#### 4. Connections to Potential Partners
**What would help:**
- Introductions to professionals at:
  - Historic Denver or Colorado SHPO
  - National Trust for Historic Preservation
  - Architecture/preservation programs at local universities
  - GIS/urban planning departments that might use this tool

**Why it matters:** Early partnerships will help us:
- Test with real users and get feedback
- Access additional datasets for training
- Understand real-world use cases and requirements
- Build credibility for future funding applications

#### 5. Guidance on Research Ethics & Data Sharing
**What we need:** Advice on:
- Appropriate use of publicly available architectural survey data
- Best practices for sharing our trained model and dataset
- Privacy considerations for images of private residences
- Open-source vs. commercial licensing strategies

**Why it matters:** Want to maximize positive impact while respecting property owners' privacy and ensuring appropriate attribution for data sources.

#### 6. Project Planning & Scope Management
**What would help:**
- Periodic check-ins (monthly?) to:
  - Validate we're staying focused on achievable goals
  - Get feedback on technical decisions before we go too far down a path
  - Help prioritize when we have multiple options
  - Reality-check our timeline and milestones

**Why it matters:** This is our first time building an AI vision model for cultural heritage. Outside perspective will help us avoid common pitfalls and stay on track.

### Longer-Term Support (Months 3-6)

#### 7. Funding Strategy Development
**What we need:**
- Help identifying appropriate grant programs
- Guidance on crafting competitive proposals
- Connections to potential funders interested in AI + preservation
- Advice on building sustainability model (grants vs. commercialization vs. hybrid)

#### 8. Dissemination & Impact
**What would help:**
- Opportunities to present work-in-progress to relevant audiences
- Guidance on publishing in preservation and/or computer science venues
- Help crafting narrative about broader impact of the work
- Connections to media/communications professionals if there's public interest

---

## Summary: Current Status & Momentum

### Where We Are
✅ **Strong foundation**: Enterprise-grade data infrastructure built and tested  
✅ **Rich dataset**: 198 buildings, 717+ images, comprehensive architectural attributes  
✅ **Clear workflow**: Defined path from current state to deployed model  
⚠️ **Critical blocker**: Schema field mapping issue preventing progress to training phase

### What's Next
🔧 **Week 1-2**: Fix data mapping, generate complete validation report  
📊 **Week 3-4**: Curate training dataset, implement train/validation split  
🤖 **Month 2**: Begin prompt engineering and first fine-tuning iteration  
🔄 **Month 3**: Iterative refinement of classification model

### Why This Matters
This project has potential to **transform how architectural surveys are conducted**, making historic preservation more efficient and accessible. By combining computer vision with architectural expertise, we can help communities identify and protect their historic resources before they're lost.

We're at a critical juncture where **strategic guidance and connections** will determine whether this becomes a proof-of-concept or a tool with real-world impact. The technical foundation is solid—now we need help navigating the path to practical application.

---

**Prepared by:** Milan Klanjsek  
**Project Repository:** [Arepas](https://github.com/milanklanjsek/workspace/arepas)  
**Contact:** [Your contact information if desired]
