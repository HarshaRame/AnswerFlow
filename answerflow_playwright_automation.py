"""
AnswerFlow Playwright Automation
Project: AUTO-1434 - ChatGPT Automation for Customer Questions

This script automates the ChatGPT interaction process using the modular chatgpt_automation library.
Simplified wrapper that uses the clean chatgpt_automation module with proper UTF-8 encoding.

Can be imported and called from answerflow_preprocessor.py or run standalone.
"""

import os
import sys
from pathlib import Path
from typing import Optional
import logging

# Import the chatgpt_automation module
sys.path.insert(0, str(Path(__file__).parent.parent / "chatgpt_automation"))
from chatgpt_automation import automate_chatgpt, automate_chatgpt_batch

# Import the JSON to XLSX converter
from json_to_xlsx_converter import convert_json_to_xlsx, consolidate_and_convert_json_to_xlsx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
# SSO and ChatGPT Configuration
SSO_EMAIL = "Harsha.Kr@jcp.catalystbrands.com"
SSO_PASSWORD = "HariSrivathsa.0001"

# Project Configuration
PROJECT_NAME = "BazaarVoice Reply Test"

# Expected output filename (ChatGPT will generate this)
# Updated to JSON format - ChatGPT will create Processed_AI_Answers.json
EXPECTED_OUTPUT_FILENAME = "Processed_AI_Answers.json"


def automate_chatgpt_response(prompt: str, csv_file_path: str, headless: bool = False) -> Optional[str]:
    """
    Main function to automate ChatGPT interaction.
    Can be imported and called from other scripts.
    
    Args:
        prompt: Text prompt to send to ChatGPT
        csv_file_path: Path to JSON/CSV file to upload
        headless: Whether to run browser in headless mode (default: False for visibility)
        
    Returns:
        Path to downloaded output file, or None if failed
        
    Example:
        from answerflow_playwright_automation import automate_chatgpt_response
        
        prompt = "Process this data and return JSON..."
        json_file = "input_data.json"
        output_file = automate_chatgpt_response(prompt, json_file)
        
        if output_file:
            print(f"Success! Output saved to: {output_file}")
        else:
            print("Automation failed")
    """
    logger.info("="*60)
    logger.info("ANSWERFLOW CHATGPT AUTOMATION")
    logger.info("="*60)
    logger.info(f"Prompt length: {len(prompt)} characters")
    logger.info(f"File: {csv_file_path}")
    logger.info(f"Headless mode: {headless}")
    logger.info("="*60)
    
    # Set up project-specific download directory
    project_dir = Path(__file__).parent
    downloads_dir = project_dir / "downloads"
    downloads_dir.mkdir(exist_ok=True)
    logger.info(f"Download directory: {downloads_dir}")
    
    # Use the chatgpt_automation module
    output_file = automate_chatgpt(
        email=SSO_EMAIL,
        password=SSO_PASSWORD,
        prompt=prompt,
        file_path=csv_file_path,
        project_name=PROJECT_NAME,
        expected_output_filename=EXPECTED_OUTPUT_FILENAME,
        headless=headless,
        use_sso=True,
        download_dir=str(downloads_dir)
    )
    
    logger.info("="*60)
    if output_file:
        logger.info("SUCCESS: AUTOMATION COMPLETED")
        logger.info(f"Output JSON: {output_file}")
        
        # Convert JSON to XLSX
        logger.info("")
        logger.info("Converting JSON to XLSX format...")
        xlsx_file = convert_json_to_xlsx(output_file, str(downloads_dir))
        
        if xlsx_file:
            logger.info(f"✓ XLSX file created: {xlsx_file}")
        else:
            logger.warning("⚠ JSON to XLSX conversion failed, but JSON file is available")
    else:
        logger.info("FAILED: AUTOMATION DID NOT COMPLETE")
    logger.info("="*60)
    
    return output_file


def automate_chatgpt_response_batch(batches: list, headless: bool = True) -> list:
    """
    Process multiple batches in a single browser session (login once).
    
    Args:
        batches: List of dicts with 'prompt' and 'file_path' keys
        headless: Whether to run browser in headless mode
        
    Returns:
        List of output file paths (None for failed batches)
        
    Example:
        batches = [
            {'prompt': '...', 'file_path': 'batch1.json'},
            {'prompt': '...', 'file_path': 'batch2.json'},
        ]
        outputs = automate_chatgpt_response_batch(batches, headless=True)
    """
    logger.info("="*60)
    logger.info("ANSWERFLOW BATCH CHATGPT AUTOMATION")
    logger.info("="*60)
    logger.info(f"Total batches: {len(batches)}")
    logger.info(f"Headless mode: {headless}")
    logger.info("="*60)
    
    # Set up project-specific download directory
    project_dir = Path(__file__).parent
    downloads_dir = project_dir / "downloads"
    downloads_dir.mkdir(exist_ok=True)
    logger.info(f"Download directory: {downloads_dir}")
    
    # Clean up old output JSON files before starting new execution
    logger.info("\nCleaning up old output JSON files...")
    import glob
    old_json_files = glob.glob(str(downloads_dir / "output_*.json"))
    old_processed_files = glob.glob(str(downloads_dir / "Processed_AI_Answers*.json"))
    files_to_remove = old_json_files + old_processed_files
    
    removed_count = 0
    for old_file in files_to_remove:
        try:
            os.remove(old_file)
            removed_count += 1
            logger.info(f"  Removed: {Path(old_file).name}")
        except Exception as e:
            logger.warning(f"  Could not remove {Path(old_file).name}: {e}")
    
    if removed_count > 0:
        logger.info(f"✓ Cleaned up {removed_count} old JSON file(s)")
    else:
        logger.info("✓ No old JSON files to clean up")
    
    # Use the batch automation module
    output_files = automate_chatgpt_batch(
        email=SSO_EMAIL,
        password=SSO_PASSWORD,
        batches=batches,
        expected_output_filename=EXPECTED_OUTPUT_FILENAME,
        headless=headless,
        use_sso=True,
        download_dir=str(downloads_dir)
    )
    
    logger.info("="*60)
    logger.info("BATCH AUTOMATION SUMMARY")
    logger.info(f"Total batches: {len(batches)}")
    logger.info(f"Successful: {len([f for f in output_files if f])}")
    logger.info(f"Failed: {len([f for f in output_files if not f])}")
    logger.info("="*60)
    
    # Note: Consolidation happens in preprocessor after all batches complete
    # This allows parallel processing to work correctly
    
    return output_files


def main():
    """Main function for standalone execution."""
    import json
    
    print("AnswerFlow ChatGPT Automation")
    print("="*60)
    
    # Check command line arguments
    if len(sys.argv) >= 2:
        csv_file = sys.argv[1]
        
        if not os.path.exists(csv_file):
            print(f"ERROR: File not found: {csv_file}")
            sys.exit(1)
    else:
        # Interactive mode
        print("\nUsage: python answerflow_playwright_automation.py <json_file>")
        print("\nExample:")
        print("  python answerflow_playwright_automation.py input.json")
        print("\nThe prompt is automatically extracted from the JSON file.\n")
        
        # Test data - load from default file
        project_dir = Path(__file__).parent
        csv_file = project_dir / "answerflow_input_for_chatgpt.json"
        
        if not os.path.exists(csv_file):
            print(f"\nERROR: JSON file '{csv_file}' not found")
            print("Please provide JSON file path as command line argument")
            sys.exit(1)
    
    # Extract prompt from JSON file (prompt is embedded in the output_builder)
    try:
        with open(str(csv_file), 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # The prompt is in the 'instructions_for_ai' field
        prompt = json_data.get('instructions_for_ai', '')
        
        if not prompt:
            print(f"ERROR: No 'instructions_for_ai' field found in {csv_file}")
            print("The JSON file should be generated by answerflow_preprocessor.py")
            sys.exit(1)
        
        print(f"✓ Extracted prompt from JSON file ({len(prompt)} characters)")
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON file: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read JSON file: {e}")
        sys.exit(1)
    
    # Run automation
    output_file = automate_chatgpt_response(prompt, str(csv_file), headless=False)
    
    if output_file:
        print(f"\n✓ SUCCESS: JSON output saved to '{output_file}'")
        
        # Check if XLSX was also created
        project_dir = Path(__file__).parent
        downloads_dir = project_dir / "downloads"
        xlsx_files = sorted(downloads_dir.glob("Answerflow_AI_Output_*.xlsx"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        if xlsx_files:
            latest_xlsx = xlsx_files[0]
            print(f"✓ SUCCESS: XLSX output saved to '{latest_xlsx}'")
        
        sys.exit(0)
    else:
        print(f"\n✗ FAILED: Automation did not complete successfully")
        sys.exit(1)


if __name__ == "__main__":
    main()
