# Core Evaluation Scripts

This directory contains the core evaluation scripts for the investment memo generator.

## Files

### evaluation_metrics.py
Main evaluation metrics framework with comprehensive evaluation capabilities.

**Key Classes:**
- `MemoEvaluator` - Main evaluation class
- `SectionMetrics` - Individual section metrics
- `MemoEvaluationMetrics` - Complete memo evaluation container

**Features:**
- Section completeness analysis
- Readability scoring (Flesch-Kincaid)
- Cost and time tracking
- Traditional VC comparison
- Quality scoring system
- System performance metrics

### integrate_evaluation.py
Integration script for evaluation during memo generation with real-time tracking.

**Key Classes:**
- `MemoGenerationTracker` - Real-time tracking class

**Features:**
- Real-time section timing
- Token usage tracking
- Academic summary generation
- Detailed metrics export

## Usage

These scripts are automatically integrated into the main memo generation pipeline.
No manual intervention required.
