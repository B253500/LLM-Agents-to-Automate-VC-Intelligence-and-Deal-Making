"""
Script to upgrade all GPT models to the best quality for memo generation
Run this to upgrade your models to gpt-4o for maximum quality
"""

import os
import re
from pathlib import Path

def upgrade_model_in_file(file_path: str, old_model: str, new_model: str):
    """Upgrade model in a specific file"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace the model
        new_content = content.replace(f'model="{old_model}"', f'model="{new_model}"')
        new_content = new_content.replace(f"model='{old_model}'", f"model='{new_model}'")
        
        if new_content != content:
            with open(file_path, 'w') as f:
                f.write(new_content)
            print(f"✅ Upgraded {old_model} → {new_model} in {file_path}")
            return True
        else:
            print(f"⚠️  No changes needed in {file_path}")
            return False
    except Exception as e:
        print(f"❌ Error updating {file_path}: {e}")
        return False

def upgrade_all_models():
    """Upgrade all models to gpt-4o for maximum quality"""
    
    # Define upgrades
    upgrades = [
        # Upgrade mini models to full gpt-4o
        ("gpt-4o-mini", "gpt-4o"),
        ("gpt-4.1-mini", "gpt-4o"),
        ("gpt-4.1-nano", "gpt-4o"),
        
        # Upgrade older models to gpt-4o
        ("gpt-3.5-turbo", "gpt-4o"),
        ("gpt-4", "gpt-4o"),  # Only if you want everything to be gpt-4o
    ]
    
    # Files to upgrade
    files_to_upgrade = [
        "chains/market_sizing_chain.py",
        "chains/financial_analysis_chain.py", 
        "chains/technical_dd_chain.py",
        "chains/exit_strategy_chain.py",
        "chains/esg_chain.py",
        "chains/follow_up_chain.py",
        "agents/market_sizing_agent.py",
        "agents/competitive_intel_agent.py",
        "agents/risk_assessment_agent.py",
        "agents/crewai_agents.py",
        "core/llm_utils.py"
    ]
    
    print("🚀 Upgrading all models to gpt-4o for maximum memo quality...")
    print("=" * 60)
    
    total_upgrades = 0
    
    for file_path in files_to_upgrade:
        if os.path.exists(file_path):
            print(f"\n📁 Processing {file_path}:")
            for old_model, new_model in upgrades:
                if upgrade_model_in_file(file_path, old_model, new_model):
                    total_upgrades += 1
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print("\n" + "=" * 60)
    print(f"✅ Upgrade complete! Made {total_upgrades} model upgrades.")
    print("\n🎯 Your memo generation will now use the highest quality models:")
    print("  📊 All critical sections: gpt-4o")
    print("  📈 All analysis sections: gpt-4o") 
    print("  📋 All supporting sections: gpt-4o")
    print("\n💡 This will provide maximum quality but higher costs.")

def show_current_model_distribution():
    """Show current model usage across the codebase"""
    print("📊 Current Model Distribution in Your Codebase:")
    print("=" * 50)
    
    model_counts = {
        "gpt-4o": 0,
        "gpt-4o-mini": 0,
        "gpt-4.1-mini": 0,
        "gpt-4.1-nano": 0,
        "gpt-3.5-turbo": 0,
        "gpt-4": 0
    }
    
    # Count models in key files
    key_files = [
        "chains/memo_synthesis_chain.py",
        "chains/market_sizing_chain.py",
        "chains/financial_analysis_chain.py",
        "chains/technical_dd_chain.py",
        "chains/exit_strategy_chain.py",
        "chains/esg_chain.py",
        "agents/financial_analysis_agent.py",
        "agents/competitive_intel_agent.py",
        "agents/risk_assessment_agent.py"
    ]
    
    for file_path in key_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                for model in model_counts.keys():
                    count = len(re.findall(f'model="{model}"', content))
                    count += len(re.findall(f"model='{model}'", content))
                    model_counts[model] += count
    
    for model, count in model_counts.items():
        if count > 0:
            print(f"  {model}: {count} instances")
    
    print("\n💡 Recommendation: Upgrade all to gpt-4o for maximum quality")

if __name__ == "__main__":
    print("🤖 GPT Model Upgrade Tool for Memo Generation")
    print("=" * 60)
    
    # Show current distribution
    show_current_model_distribution()
    
    # Ask user if they want to upgrade
    response = input("\n❓ Do you want to upgrade all models to gpt-4o? (y/n): ")
    
    if response.lower() in ['y', 'yes']:
        upgrade_all_models()
    else:
        print("⏭️  Skipping upgrade. Your current models will be used.") 