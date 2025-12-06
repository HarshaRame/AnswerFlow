"""
JSON to XLSX Converter for AnswerFlow
Project: AUTO-1434 - ChatGPT Automation for Customer Questions

This script converts the downloaded JSON output from ChatGPT to XLSX format.
Reads the JSON file with structure: {"column_headers": [...], "data": [[...]]}
and converts it to an Excel file.
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime
import logging
from typing import Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_json_to_xlsx(json_file_path: str, output_dir: Optional[str] = None) -> Optional[str]:
    """
    Convert ChatGPT JSON output to XLSX format.
    
    Args:
        json_file_path: Path to the downloaded JSON file
        output_dir: Optional output directory (defaults to same directory as JSON file)
        
    Returns:
        Path to the created XLSX file, or None if failed
        
    Expected JSON structure:
        {
            "column_headers": ["product_id", "product_name", "brand_name", "question_id", "question_text", "answer"],
            "data": [
                ["pp5004930352", "14K Gold Ring", "FINE JEWELRY", "7952315", "What is the metal type?", "This ring is crafted from 14k gold over silver."],
                ...
            ]
        }
    """
    try:
        logger.info("="*60)
        logger.info("JSON TO XLSX CONVERSION")
        logger.info("="*60)
        logger.info(f"Input JSON: {json_file_path}")
        
        # Validate input file exists
        json_path = Path(json_file_path)
        if not json_path.exists():
            logger.error(f"JSON file not found: {json_file_path}")
            return None
        
        # Read JSON file
        logger.info("Reading JSON file...")
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate JSON structure
        if not isinstance(data, dict):
            logger.error("JSON must be a dictionary")
            return None
        
        if 'column_headers' not in data or 'data' not in data:
            logger.error("JSON must contain 'column_headers' and 'data' keys")
            return None
        
        column_headers = data['column_headers']
        rows = data['data']
        
        logger.info(f"Found {len(column_headers)} columns: {column_headers}")
        logger.info(f"Found {len(rows)} data rows")
        
        # Create DataFrame
        logger.info("Creating DataFrame...")
        df = pd.DataFrame(rows, columns=column_headers)
        
        # Create category summary if question_category column exists
        category_summary_df = None
        if 'question_category' in df.columns:
            logger.info("Generating category summary...")
            category_counts = df['question_category'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Number of Questions']
            category_summary_df = category_counts
            logger.info(f"Found {len(category_summary_df)} unique category combinations")
        
        # Determine output directory
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = json_path.parent
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"Answerflow_AI_Output_{timestamp}.xlsx"
        output_file = output_path / output_filename
        
        # Write to Excel with multiple sheets
        logger.info(f"Writing to Excel: {output_file}")
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Write main data sheet
            df.to_excel(writer, sheet_name='Questions and Answers', index=False)
            
            # Auto-adjust column widths for main sheet
            worksheet = writer.sheets['Questions and Answers']
            for idx, col in enumerate(df.columns, 1):
                # Calculate max width based on column name and data
                max_length = len(str(col))
                for value in df[col].astype(str):
                    # Limit check to first 1000 chars to avoid performance issues
                    value_length = len(str(value)[:1000])
                    if value_length > max_length:
                        max_length = value_length
                
                # Set reasonable limits: min 10, max 100 characters
                adjusted_width = min(max(max_length + 2, 10), 100)
                column_letter = chr(64 + idx)  # A, B, C, etc.
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info("✓ Auto-adjusted column widths for readability")
            
            # Write category summary sheet if available
            if category_summary_df is not None:
                category_summary_df.to_excel(writer, sheet_name='Category Summary', index=False)
                
                # Auto-adjust column widths for summary sheet
                summary_worksheet = writer.sheets['Category Summary']
                for idx, col in enumerate(category_summary_df.columns, 1):
                    max_length = len(str(col))
                    for value in category_summary_df[col].astype(str):
                        if len(str(value)) > max_length:
                            max_length = len(str(value))
                    adjusted_width = min(max(max_length + 2, 10), 50)
                    column_letter = chr(64 + idx)
                    summary_worksheet.column_dimensions[column_letter].width = adjusted_width
                
                logger.info(f"Added 'Category Summary' sheet with {len(category_summary_df)} rows")
        
        # Verify file was created
        if output_file.exists():
            file_size = output_file.stat().st_size
            logger.info(f"✓ XLSX file created successfully!")
            logger.info(f"  File: {output_file}")
            logger.info(f"  Size: {file_size:,} bytes")
            logger.info(f"  Rows: {len(df)}")
            logger.info(f"  Columns: {len(df.columns)}")
            logger.info("="*60)
            return str(output_file)
        else:
            logger.error("Failed to create XLSX file")
            return None
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
        return None
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def consolidate_and_convert_json_to_xlsx(json_file_paths: List[str], output_dir: Optional[str] = None, pre_answered_json_path: Optional[str] = None) -> Optional[str]:
    """
    Consolidate multiple JSON files from batches and convert to a single XLSX file.
    Also merges pre-answered questions from the repository if provided.
    
    Args:
        json_file_paths: List of paths to ChatGPT output JSON files to consolidate
        output_dir: Optional output directory (defaults to same directory as first JSON file)
        pre_answered_json_path: Optional path to pre-answered questions repository JSON
        
    Returns:
        Path to the created consolidated XLSX file, or None if failed
        
    Expected JSON structure for each file:
        {
            "column_headers": ["product_id", "product_name", "brand_name", "question_id", "question_text", "answer"],
            "data": [
                ["pp5004930352", "14K Gold Ring", "FINE JEWELRY", "7952315", "What is the metal type?", "Answer here"],
                ...
            ]
        }
    """
    try:
        logger.info("="*60)
        logger.info("CONSOLIDATING MULTIPLE JSON FILES TO XLSX")
        logger.info("="*60)
        logger.info(f"Total ChatGPT JSON files to consolidate: {len(json_file_paths)}")
        if pre_answered_json_path:
            logger.info(f"Pre-answered repository: {Path(pre_answered_json_path).name}")
        
        # Filter out None values and validate files exist
        valid_files = [f for f in json_file_paths if f and Path(f).exists()]
        
        if not valid_files and not pre_answered_json_path:
            logger.error("No valid JSON files to consolidate")
            return None
        
        logger.info(f"Valid ChatGPT files: {len(valid_files)}")
        for idx, file_path in enumerate(valid_files, 1):
            logger.info(f"  {idx}. {Path(file_path).name}")
        
        # Read all JSON files and consolidate data
        all_data_rows = []
        column_headers = None
        
        # STEP 1: Read pre-answered questions repository FIRST
        pre_answered_count = 0
        if pre_answered_json_path and Path(pre_answered_json_path).exists():
            logger.info(f"\nReading pre-answered repository: {Path(pre_answered_json_path).name}")
            
            try:
                with open(pre_answered_json_path, 'r', encoding='utf-8') as f:
                    pre_answered_data = json.load(f)
                
                if isinstance(pre_answered_data, dict) and 'column_headers' in pre_answered_data and 'data' in pre_answered_data:
                    # Set column headers from repository
                    column_headers = pre_answered_data['column_headers']
                    logger.info(f"Column headers: {column_headers}")
                    
                    # Add pre-answered rows
                    pre_answered_rows = pre_answered_data['data']
                    all_data_rows.extend(pre_answered_rows)
                    pre_answered_count = len(pre_answered_rows)
                    logger.info(f"  ✓ Added {pre_answered_count} pre-answered rows")
                else:
                    logger.warning("Pre-answered JSON has invalid structure, skipping")
            except Exception as e:
                logger.warning(f"Could not read pre-answered repository: {e}")
        
        # STEP 2: Read ChatGPT output files
        chatgpt_count = 0
        for idx, json_file_path in enumerate(valid_files, 1):
            logger.info(f"\nReading ChatGPT batch {idx}/{len(valid_files)}: {Path(json_file_path).name}")
            
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate JSON structure
            if not isinstance(data, dict):
                logger.warning(f"Skipping {Path(json_file_path).name}: Not a dictionary")
                continue
            
            if 'column_headers' not in data or 'data' not in data:
                logger.warning(f"Skipping {Path(json_file_path).name}: Missing required keys")
                continue
            
            # Set column headers from first file if not set by pre-answered
            if column_headers is None:
                column_headers = data['column_headers']
                logger.info(f"Column headers: {column_headers}")
            else:
                # Verify headers match
                if data['column_headers'] != column_headers:
                    logger.warning(f"Column headers mismatch in {Path(json_file_path).name}, using first file's headers")
            
            # Append data rows
            batch_rows = data['data']
            all_data_rows.extend(batch_rows)
            chatgpt_count += len(batch_rows)
            logger.info(f"  Added {len(batch_rows)} rows (Running total: {len(all_data_rows)})")
        
        if not column_headers or not all_data_rows:
            logger.error("No data to consolidate")
            return None
        
        logger.info(f"\n" + "="*60)
        logger.info(f"CONSOLIDATION SUMMARY:")
        logger.info(f"  Pre-answered questions: {pre_answered_count}")
        logger.info(f"  ChatGPT generated answers: {chatgpt_count}")
        logger.info(f"  TOTAL ROWS: {len(all_data_rows)}")
        logger.info(f"  Source files: {len(valid_files)} ChatGPT batches + repository")
        logger.info("="*60)
        
        # Create consolidated DataFrame
        logger.info("Creating consolidated DataFrame...")
        df = pd.DataFrame(all_data_rows, columns=column_headers)
        
        # Create category summary if question_category column exists
        category_summary_df = None
        if 'question_category' in df.columns:
            logger.info("Generating category summary...")
            category_counts = df['question_category'].value_counts().reset_index()
            category_counts.columns = ['Category', 'Number of Questions']
            category_summary_df = category_counts
            logger.info(f"Found {len(category_summary_df)} unique category combinations")
        
        # Determine output directory
        if output_dir:
            output_path = Path(output_dir)
        else:
            output_path = Path(valid_files[0]).parent
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"Answerflow_AI_Output_Consolidated_{timestamp}.xlsx"
        output_file = output_path / output_filename
        
        # Write to Excel with multiple sheets
        logger.info(f"Writing consolidated data to Excel: {output_file}")
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Write main data sheet
            df.to_excel(writer, sheet_name='Questions and Answers', index=False)
            
            # Auto-adjust column widths for main sheet
            worksheet = writer.sheets['Questions and Answers']
            for idx, col in enumerate(df.columns, 1):
                # Calculate max width based on column name and data
                max_length = len(str(col))
                for value in df[col].astype(str):
                    # Limit check to first 1000 chars to avoid performance issues
                    value_length = len(str(value)[:1000])
                    if value_length > max_length:
                        max_length = value_length
                
                # Set reasonable limits: min 10, max 100 characters
                adjusted_width = min(max(max_length + 2, 10), 100)
                column_letter = chr(64 + idx)  # A, B, C, etc.
                worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info("✓ Auto-adjusted column widths for readability")
            
            # Write category summary sheet if available
            if category_summary_df is not None:
                category_summary_df.to_excel(writer, sheet_name='Category Summary', index=False)
                
                # Auto-adjust column widths for summary sheet
                summary_worksheet = writer.sheets['Category Summary']
                for idx, col in enumerate(category_summary_df.columns, 1):
                    max_length = len(str(col))
                    for value in category_summary_df[col].astype(str):
                        if len(str(value)) > max_length:
                            max_length = len(str(value))
                    adjusted_width = min(max(max_length + 2, 10), 50)
                    column_letter = chr(64 + idx)
                    summary_worksheet.column_dimensions[column_letter].width = adjusted_width
                
                logger.info(f"Added 'Category Summary' sheet with {len(category_summary_df)} rows")
        
        # Verify file was created
        if output_file.exists():
            file_size = output_file.stat().st_size
            logger.info(f"✓ CONSOLIDATED XLSX file created successfully!")
            logger.info(f"  File: {output_file}")
            logger.info(f"  Size: {file_size:,} bytes")
            logger.info(f"  Rows: {len(df)}")
            logger.info(f"  Columns: {len(df.columns)}")
            logger.info(f"  Source batches: {len(valid_files)}")
            logger.info("="*60)
            return str(output_file)
        else:
            logger.error("Failed to create consolidated XLSX file")
            return None
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format: {e}")
        return None
    except Exception as e:
        logger.error(f"Consolidation failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def main():
    """Main function for standalone execution."""
    import sys
    
    if len(sys.argv) < 2:
        print("\nUsage: python json_to_xlsx_converter.py <json_file_path> [output_directory]")
        print("\nExample:")
        print("  python json_to_xlsx_converter.py downloads/output_20251127_143022.json")
        print("  python json_to_xlsx_converter.py downloads/output_20251127_143022.json ./output")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = convert_json_to_xlsx(json_file, output_dir)
    
    if result:
        print(f"\n✓ SUCCESS: XLSX file created at {result}")
        sys.exit(0)
    else:
        print("\n✗ FAILED: Could not convert JSON to XLSX")
        sys.exit(1)


if __name__ == "__main__":
    main()

