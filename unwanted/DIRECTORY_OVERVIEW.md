# Route Optimization Directory - Complete File Overview

**Total Files: 125**
**Last Updated: September 29, 2025**

## 📁 **DIRECTORY STRUCTURE**

---

## 🏗️ **CORE/** - Main Optimization Engine (9 files)

### **Main Components:**
- **`database.py`** - Database connection handler with SQL Server integration
- **`route_optimizer.py`** - Basic route optimization with TSP algorithms
- **`enhanced_route_optimizer.py`** - Advanced optimization with prospect integration
- **`scalable_route_optimizer.py`** - Performance-optimized version for large datasets

### **Pipeline Runners:**
- **`run_specific_agents.py`** - Process predefined specific agents (SK-SAT4, SK-SAT5, PVM-PRE01)
- **`run_csv_agents.py`** - Process agents from CSV file input
- **`run_enhanced_pipeline.py`** - Enhanced pipeline with advanced features
- **`run_production_pipeline.py`** - Production-ready pipeline runner

### **Documentation:**
- **`README.md`** - Core module documentation

---

## 🚀 **FULL_PIPELINE/** - Complete Enterprise Pipeline (5 files)

### **Main Pipeline:**
- **`run_all_agents.py`** - Process ALL agents in database with advanced features
- **`run_pipeline.py`** - User-friendly interactive pipeline runner

### **Supporting Components:**
- **`batch_processor.py`** - Batch processing utilities and monitoring
- **`config.py`** - Configuration settings and presets
- **`README.md`** - Full pipeline documentation

---

## 🛠️ **UTILS/** - Utilities & Specialized Tools (32 files)

### **Prospect Route Creators (599 prospects):**
- **`create_prospect_route_balanced.py`** ⭐ - K-means clustering, max 60 per cluster
- **`create_prospect_route_dbscan_tsp.py`** - DBSCAN clustering for multi-day routes
- **`create_prospect_route_effective.py`** - Simple effective clustering approach
- **`create_prospect_route_from_distributor.py`** - Distributor-based prospect routing
- **`create_prospect_route_simple.py`** - Basic prospect route creation
- **`create_prospect_route_fixed.py`** - Fixed routing approach
- **`create_prospect_route.py`** - General prospect route creator

### **Scenario Analysis:**
- **`find_distributor_scenarios.py`** ⭐ - Find agents by 5 scenarios for specific distributor
- **`clustered_scenario_report.py`** - Generate clustered scenario reports
- **`export_clustered_csv.py`** ⭐ - Export scenario data to CSV
- **`simple_clustered_format.py`** - Display scenarios in clustered format
- **`analyze_agent_scenarios.py`** - Analyze agent performance scenarios
- **`analyze_scenario3_details.py`** - Detailed analysis of scenario 3 agents
- **`analyze_scenario5_details.py`** - Detailed analysis of scenario 5 agents

### **Agent Finders & Examples:**
- **`comprehensive_agent_finder.py`** - Find agents matching various criteria
- **`find_scenario_agents.py`** - Find agents for specific scenarios
- **`find_specific_scenarios.py`** - Locate specific scenario examples
- **`simple_agent_examples.py`** - Simple agent example generation
- **`quick_scenario_examples.py`** - Quick scenario demonstration
- **`quick_specific_scenarios.py`** - Quick specific scenario lookup
- **`final_scenario_examples.py`** - Final verified scenario examples

### **Pipeline Runners:**
- **`run_agent_pipeline.py`** ⭐ - Alternative agent pipeline runner
- **`run_agents_with_prospects.py`** - Run agents with prospect integration
- **`test_specific_agents.py`** - Test specific agent processing

### **Database & System:**
- **`check_database_table.py`** - Database table verification
- **`check_results.py`** - Verify processing results
- **`test_database_connection.py`** - Test database connectivity
- **`verify_insertions.py`** - Verify data insertions
- **`create_indexes.py`** - Create database indexes for performance
- **`create_table.py`** - Database table creation utilities

### **Data Management:**
- **`clear_agent_914.py`** - Clear data for agent 914
- **`clear_agent_914_quick.py`** - Quick clear for agent 914
- **`analyze_routedata.py`** - Analyze route data patterns

### **Organization & Packaging:**
- **`organize_files.py`** - Organize project files
- **`finish_organization.py`** - Complete file organization
- **`create_package.py`** - Create deployment packages
- **`main.py`** - Main utility entry point

### **Documentation:**
- **`README.md`** - Utils module documentation

---

## 🧪 **TESTS/** - Testing & Validation (25 files)

### **Agent Testing:**
- **`test_single_agent.py`** - Test individual agent processing
- **`test_specific_agents.py`** - Test specific agent combinations
- **`basic_agent_check.py`** - Basic agent validation
- **`simple_agent_analysis.py`** - Simple agent performance analysis
- **`get_specific_agents.py`** - Get specific agents for testing

### **Scenario Analysis:**
- **`analyze_agent_scenarios.py`** - Comprehensive scenario analysis
- **`detailed_scenario_report.py`** - Detailed scenario reporting

### **Database & Barangay Testing:**
- **`check_barangay_codes.py`** - Validate barangay codes
- **`check_barangay_code_issue.py`** - Debug barangay code issues
- **`debug_barangay_matching.py`** - Debug barangay matching logic
- **`find_valid_barangay_codes.py`** - Find valid barangay codes
- **`quick_barangay_check.py`** - Quick barangay validation
- **`test_barangay_code_fix.py`** - Test barangay code fixes

### **Prospect Testing:**
- **`debug_prospects.py`** - Debug prospect processing
- **`check_prospect_barangays.py`** - Validate prospect barangays
- **`test_with_prospects.py`** - Test with prospect integration
- **`test_fallback_prospects.py`** - Test prospect fallback logic
- **`test_final_prospect_demo.py`** - Final prospect demonstration

### **Algorithm Testing:**
- **`test_tsp.py`** - Test TSP algorithms
- **`test_tsp_with_coords.py`** - Test TSP with coordinates
- **`test_enhanced_logic.py`** - Test enhanced optimization logic

### **Performance & System:**
- **`test_performance.py`** - Performance testing
- **`test_with_simulated_data.py`** - Test with simulated data
- **`final_verification_test.py`** - Final system verification
- **`final_working_test.py`** - Final working system test

### **Data Management:**
- **`clear_and_rerun.py`** - Clear data and rerun tests
- **`final_cleanup_and_rerun.py`** - Final cleanup and rerun

### **Utility Tests:**
- **`find_agent_with_barangay.py`** - Find agents with barangay data
- **`find_agent_with_coords.py`** - Find agents with coordinates
- **`test_real_agent.py`** - Test with real agent data
- **`quick_custype_test.py`** - Quick customer type testing

### **Documentation:**
- **`README.md`** - Test module documentation

---

## 🗄️ **SQL/** - Database Queries & Scripts (11 files)

### **Scenario Queries:**
- **`distributor_11814_scenarios.sql`** ⭐ - Scenarios for distributor 11814
- **`specific_scenario_queries.sql`** - Specific scenario analysis
- **`scenario_specific_queries.sql`** - Scenario-specific database queries
- **`three_specific_scenarios.sql`** - Three main scenario examples

### **Agent Analysis:**
- **`find_scenario_examples.sql`** - Find scenario examples in database
- **`find_agents_25_to_59.sql`** - Find agents with 25-59 customers
- **`analyze_mix_b10_agent.sql`** - Analyze MIX-B10 agent specifically
- **`check_agents_with_prospects.sql`** - Check agents with prospect data

### **System Queries:**
- **`analysis_queries.sql`** - General analysis queries
- **`single_comprehensive_query.sql`** - Comprehensive system query
- **`create_optimized_indexes.sql`** - Create performance indexes

### **Documentation:**
- **`README.md`** - SQL module documentation

---

## 📊 **VISUALIZATION/** - Web Interface & Visualization (11 files)

### **Main Applications:**
- **`app.py`** ⭐ - Main Streamlit visualization app
- **`route_visualizer.py`** ⭐ - Core route visualization engine
- **`fixed_route_visualizer.py`** - Fixed version of route visualizer
- **`debug_streamlit_app.py`** - Debug version of Streamlit app

### **Testing & Examples:**
- **`simple_test_map.py`** - Simple map testing
- **`test_pvm_pre01_map.py`** - Test PVM-PRE01 agent visualization
- **`pvm_pre01_test.html`** - HTML test output for PVM-PRE01

### **Runners:**
- **`run_app.py`** ⭐ - Python runner for visualization app
- **`run.bat`** - Windows batch runner

### **Configuration:**
- **`requirements.txt`** - Visualization dependencies
- **`README.md`** - Visualization documentation

---

## 📚 **DOCS/** - Documentation & Schemas (4 files)

- **`database_schema.md`** - Database schema documentation
- **`updated_database_schema.md`** - Updated schema information
- **`scenario_agent_examples.md`** - Scenario and agent examples
- **`all_scenarios.md`** - Complete scenario documentation

---

## 📋 **DATA FILES** - Generated Data & Reports (2 files)

- **`distributor_11814_clustered_scenarios_20250929_145849.csv`** ⭐ - Clustered scenario data
- **`distributor_11814_scenarios_20250929_144752.csv`** - Raw scenario data

---

## ⚙️ **ROOT CONFIGURATION FILES** (5 files)

- **`README.md`** ⭐ - Main project documentation
- **`requirements.txt`** - Python dependencies
- **`.env`** - Environment variables (database config)
- **`run_csv_agents_pipeline.py`** ⭐ - Root-level CSV pipeline runner
- **`route_optimization_package.zip`** - Packaged deployment version

---

## 🔧 **SYSTEM FILES** (Hidden/Cache)

- **`.claude/settings.local.json`** - Claude Code settings
- **`__pycache__/`** - Python cache files (8 files)
- **`core/__pycache__/`** - Core module cache (3 files)

---

## 🌟 **KEY FILES FOR IMMEDIATE USE**

### **⭐ Essential Pipeline Runners:**
1. **`core/run_specific_agents.py`** - Run predefined agents
2. **`full_pipeline/run_all_agents.py`** - Process all agents in DB
3. **`utils/create_prospect_route_balanced.py`** - 599 prospects (max 60/cluster)
4. **`run_csv_agents_pipeline.py`** - Process CSV agent list

### **⭐ Visualization:**
1. **`visualization/app.py`** - Main Streamlit app
2. **`visualization/run_app.py`** - App runner

### **⭐ Data Analysis:**
1. **`utils/find_distributor_scenarios.py`** - Find distributor scenarios
2. **`distributor_11814_clustered_scenarios_20250929_145849.csv`** - Ready data

### **⭐ Documentation:**
1. **`README.md`** - Main documentation
2. **`full_pipeline/README.md`** - Pipeline documentation

---

## 🚀 **QUICK START COMMANDS**

```bash
# Run specific scenarios
python core/run_specific_agents.py

# Run 599 prospects (max 60 per cluster)
python utils/create_prospect_route_balanced.py

# Run full pipeline for all agents
python full_pipeline/run_all_agents.py

# Start visualization
cd visualization && streamlit run app.py

# Process CSV agents
python run_csv_agents_pipeline.py
```

---

**This directory contains a complete enterprise-grade route optimization system with 125 files supporting various scenarios, testing, visualization, and production deployment.**