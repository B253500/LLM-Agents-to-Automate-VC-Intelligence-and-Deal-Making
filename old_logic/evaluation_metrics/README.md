# Evaluation Metrics System

This directory contains the evaluation metrics system for the investment memo generator.

## Directory Structure

### 📁 core/
Core evaluation scripts and frameworks
- `evaluation_metrics.py` - Main evaluation metrics framework
- `integrate_evaluation.py` - Integration script for evaluation during memo generation

### 📁 results/
Evaluation results and outputs organized by type
- `detailed_metrics/` - Detailed JSON evaluation data
- `academic_summaries/` - Academic analysis summaries in Markdown
- `excel_reports/` - Excel evaluation reports
- `performance_analysis/` - Performance analysis files

### 📁 templates/
Templates for evaluation reports
- `academic_summary_template.md` - Template for academic summaries
- `excel_report_template.xlsx` - Template for Excel reports
- `performance_dashboard_template.html` - Template for performance dashboards

### 📁 config/
Configuration files for evaluation parameters
- `evaluation_config.json` - Main evaluation configuration
- `benchmark_standards.json` - Quality and performance benchmarks

### 📁 utils/
Utility functions for evaluation tasks
- `metrics_calculator.py` - Functions for calculating metrics
- `report_generator.py` - Functions for generating reports

## Usage

1. **Run evaluation**: The evaluation system is integrated into main.py
2. **View results**: Check the results/ directory for evaluation outputs
3. **Configure settings**: Modify config/ files to adjust evaluation parameters
4. **Generate reports**: Use utils/ functions for custom report generation

## Metrics Tracked

- **Quality Metrics**: Section completeness, readability, content quality
- **Performance Metrics**: Generation time, token usage, cost analysis
- **Comparison Metrics**: Traditional VC comparison, efficiency analysis
- **System Metrics**: CPU/GPU usage, memory consumption, robustness
