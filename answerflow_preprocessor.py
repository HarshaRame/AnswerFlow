"""
AnswerFlow Preprocessor Script (Enhanced)
Project: AUTO-1434 - Leveraging AI to Answer Customer Questions

Enhanced version with Rich terminal output, proper logging, and clean UX.
"""

import os
import sys
import time
import json
import logging
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Confirm
from rich import box

# Import helper modules
from preprocessor_helper import (
    TextCleaner,
    CSVHandler,
    APIFetcher,
    JSONProcessor,
    OutputBuilder,
    QuestionCategorizer
)
from preprocessor_helper.bazaarvoice_checker import BazaarVoiceChecker
from preprocessor_helper.answer_rephraser import AnswerRephraser
from answerflow_parallel_automation import process_batches_in_parallel

# Initialize Rich console
console = Console()

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Remove old log files
try:
    import glob
    old_logs = glob.glob(os.path.join(log_dir, 'answerflow_*.log'))
    for old_log in old_logs:
        try:
            os.remove(old_log)
        except:
            pass
except:
    pass

log_file = os.path.join(log_dir, f'answerflow_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# Configure logging to ONLY write to file, suppress terminal output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)

# Suppress all logging to console
logging.getLogger().handlers = [logging.FileHandler(log_file, encoding='utf-8')]
logger = logging.getLogger(__name__)

# Suppress verbose logging
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)


class AnswerFlowPreprocessor:
    """Main preprocessor orchestrator using modular components."""
    
    def __init__(self, max_workers: int = 20, timeout: int = 20):
        """
        Initialize the preprocessor with helper modules.
        
        Args:
            max_workers: Number of concurrent threads for API calls
            timeout: Request timeout in seconds
        """
        self.max_workers = max_workers
        self.timeout = timeout
        
        # Initialize helper modules
        self.text_cleaner = TextCleaner()
        self.csv_handler = CSVHandler()
        self.api_fetcher = APIFetcher(max_workers=max_workers, timeout=timeout)
        self.json_processor = JSONProcessor()
        self.output_builder = OutputBuilder()
        self.question_categorizer = QuestionCategorizer()
        
        # CSV column configuration
        self.csv_columns = {
            'question_id': 'Question ID',
            'question_title': 'Question title',
            'question_details': 'Question details',
            'product_id': 'Product ID'
        }
        
        # Columns to retain in output
        self.columns_to_retain = [
            'Question ID',
            'Question title',
            'Product ID',
            'Question moderation status'
        ]
        
        # Initialize statistics
        self.stats = {
            'total_questions': 0,
            'valid_product_ids': 0,
            'successful_api_calls': 0,
            'failed_api_calls': 0,
            'utf_cleaning_applied': 0
        }
    
    def read_and_clean_csv(self, filepath: str) -> pd.DataFrame:
        """
        Step 1 & 2: Read Input CSV and Clean Non-UTF Characters.
        """
        console.print("\n[cyan]Step 1: Reading and validating CSV file...[/cyan]")
        logger.info(f"Reading CSV file: {filepath}")
        
        try:
            # Read CSV
            df = self.csv_handler.read_csv(filepath)
            logger.info(f"Original CSV shape: {df.shape}")
            
            # Validate required columns
            self.csv_handler.validate_columns(df, self.csv_columns)
            
            # Filter to only keep required columns
            df = self.csv_handler.filter_columns(df, self.columns_to_retain)
            
            # Clean UTF-8 characters in text columns
            df = self.csv_handler.clean_text_columns(df, ['Question title'])
            
            # Filter for APPROVED questions only
            df = self.csv_handler.filter_approved_questions(df)
            
            # Extract and clean product IDs
            df['Clean_Product_ID'] = df['Product ID'].apply(self.csv_handler.extract_product_id)
            
            # Filter out rows without valid product IDs
            valid_mask = df['Clean_Product_ID'].notna() & (df['Clean_Product_ID'] != "")
            df_valid = df[valid_mask].copy()
            
            # Update statistics
            self.stats['total_questions'] = len(df)
            self.stats['valid_product_ids'] = len(df_valid)
            self.stats['utf_cleaning_applied'] = self.csv_handler.stats['utf_cleaning_applied']
            
            console.print(f"[green]✓ Loaded {len(df_valid)} valid questions from {len(df)} total rows[/green]")
            logger.info(f"Cleaned CSV: {len(df_valid)} valid questions, {self.stats['utf_cleaning_applied']} UTF-8 cleanings applied")
            
            return df_valid
            
        except Exception as e:
            logger.error(f"Failed to read CSV: {e}", exc_info=True)
            console.print(f"[red]✗ Error reading CSV: {e}[/red]")
            raise
    
    def fetch_product_data(self, product_ids: list) -> dict:
        """
        Step 3-5: Fetch and process product data from API with progress tracking.
        """
        console.print(f"\n[cyan]Step 2: Fetching product data for {len(product_ids)} products ({self.max_workers} parallel workers)...[/cyan]")
        logger.info(f"Starting API fetch for {len(product_ids)} products with {self.max_workers} workers")
        
        try:
            product_data = {}
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
                transient=False
            ) as progress:
                task = progress.add_task("[cyan]Fetching...", total=len(product_ids))
                
                # Fetch with concurrent futures
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_product = {
                        executor.submit(self.api_fetcher.process_with_retry, pid): pid 
                        for pid in product_ids
                    }
                    
                    success_count = 0
                    for future in concurrent.futures.as_completed(future_to_product):
                        product_id, data, status = future.result()
                        
                        if status == "success":
                            success_count += 1
                            product_data[product_id] = data
                        else:
                            product_data[product_id] = {}
                        
                        progress.update(task, advance=1, description=f"[cyan]Fetching... ({success_count}/{len(product_ids)} success)[/cyan]")
            
            # Update statistics
            self.stats['successful_api_calls'] = self.api_fetcher.stats['successful_calls'] = success_count
            self.stats['failed_api_calls'] = self.api_fetcher.stats['failed_calls'] = len(product_ids) - success_count
            
            # Process JSON data
            processed_data = self.json_processor.process_all_products(product_data)
            
            success_rate = (success_count / len(product_ids) * 100) if product_ids else 0
            console.print(f"[green]✓ Retrieved data for {success_count}/{len(product_ids)} products ({success_rate:.1f}%)[/green]")
            logger.info(f"API fetch complete: {success_count} succeeded, {len(product_ids) - success_count} failed")
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Failed to fetch product data: {e}", exc_info=True)
            console.print(f"[red]✗ Error fetching product data: {e}[/red]")
            raise
    
    def merge_and_enrich_data(self, df_csv: pd.DataFrame, product_data: dict) -> pd.DataFrame:
        """
        Step 6: Data Merging & Enrichment with BazaarVoice check.
        """
        console.print("\n[cyan]Step 3: Enriching questions with product data...[/cyan]")
        logger.info("Starting data merge and enrichment")
        
        try:

            import concurrent.futures

            df_enriched = df_csv.copy()

            # Add product attributes
            df_enriched['product_attributes'] = df_enriched['Clean_Product_ID'].apply(
                lambda pid: product_data.get(pid, {}).get('product_attributes', '{}')
            )

            # Categorize questions and handle special cases
            console.print("\n[cyan]Categorizing questions...[/cyan]")
            logger.info("Starting question categorization")
            
            df_enriched['question_category'] = ''
            df_enriched['special_handling'] = False
            df_enriched['default_answer'] = None
            
            categorized_count = 0
            size_chart_count = 0
            skip_chatgpt_count = 0
            
            for idx, row in df_enriched.iterrows():
                question_text = row['Question title']
                
                # Check for special handling first
                special_check = self.question_categorizer.check_special_question(question_text)
                
                if special_check['is_special']:
                    df_enriched.at[idx, 'special_handling'] = True
                    df_enriched.at[idx, 'default_answer'] = special_check['default_answer']
                    
                    if special_check['type'] == 'size_chart_guide':
                        size_chart_count += 1
                    elif special_check['type'] == 'credit_card_shipping_returns':
                        skip_chatgpt_count += 1
                
                # Categorize the question
                categories = self.question_categorizer.categorize(question_text)
                df_enriched.at[idx, 'question_category'] = categories
                categorized_count += 1
            
            console.print(f"[green]✓ Categorized {categorized_count} questions[/green]")
            console.print(f"[yellow]  • {size_chart_count} size chart/guide questions (default answer)[/yellow]")
            console.print(f"[yellow]  • {skip_chatgpt_count} credit card/shipping/returns questions (skip ChatGPT)[/yellow]")
            logger.info(f"Question categorization complete: {categorized_count} categorized, {size_chart_count} size chart, {skip_chatgpt_count} skip ChatGPT")

            # Check BazaarVoice for previously answered questions
            console.print("\n[cyan]Checking BazaarVoice for previously answered questions...[/cyan]")
            logger.info("Starting BazaarVoice question check")

            df_enriched['bv_previously_answered'] = False
            df_enriched['bv_existing_answer'] = None
            df_enriched['bv_similarity_score'] = 0.0
            df_enriched['bv_rephrased_answer'] = None

            # Initialize rephraser
            rephraser = AnswerRephraser()

            with BazaarVoiceChecker() as bv_checker:
                # Get unique product IDs to minimize API calls
                unique_products = df_enriched['Clean_Product_ID'].unique()
                bv_cache = {}  # Cache BazaarVoice results per product

                matched_count = 0
                checked_count = 0

                def fetch_bazaarvoice(product_id):
                    api_response = bv_checker.get_answered_questions(product_id)
                    if api_response:
                        answered_questions = bv_checker.extract_answered_questions(api_response)
                        return (product_id, answered_questions)
                    else:
                        return (product_id, [])

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console,
                    transient=False
                ) as progress:
                    task = progress.add_task("[cyan]Checking BazaarVoice...", total=len(unique_products))

                    # Multithreaded fetch BazaarVoice data for each unique product
                    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                        future_to_pid = {executor.submit(fetch_bazaarvoice, pid): pid for pid in unique_products}
                        for future in concurrent.futures.as_completed(future_to_pid):
                            pid, answered_questions = future.result()
                            bv_cache[pid] = answered_questions
                            progress.update(task, advance=1)

                # Now try comprehensive answer generation for each question
                # This includes: product attributes + previously answered questions
                comprehensive_generated_count = 0
                
                for idx, row in df_enriched.iterrows():
                    product_id = row['Clean_Product_ID']
                    question_text = row['Question title']
                    question_category = df_enriched.at[idx, 'question_category']
                    
                    # Skip if already has default answer (size chart, etc.)
                    if df_enriched.at[idx, 'default_answer']:
                        continue
                    
                    # Get product attributes
                    product_attributes = df_enriched.at[idx, 'product_attributes']
                    if isinstance(product_attributes, str):
                        try:
                            import json
                            product_attributes = json.loads(product_attributes)
                        except:
                            product_attributes = {}
                    
                    # Get previously answered questions from BazaarVoice for this product
                    bv_answered_questions = bv_cache.get(product_id, [])
                    previously_answered = []
                    for bv_q in bv_answered_questions:
                        if bv_q.get('answers'):
                            previously_answered.append({
                                'question': bv_q.get('question_text', ''),
                                'answer': bv_q['answers'][0]
                            })
                    
                    # Try comprehensive answer generation
                    generated_answer, source = rephraser.generate_comprehensive_answer(
                        question=question_text,
                        product_attributes=product_attributes,
                        previously_answered=previously_answered if previously_answered else None,
                        question_category=question_category
                    )
                    
                    if generated_answer:
                        # Mark as pre-answered with high confidence
                        df_enriched.at[idx, 'bv_previously_answered'] = True
                        df_enriched.at[idx, 'bv_rephrased_answer'] = generated_answer
                        df_enriched.at[idx, 'bv_similarity_score'] = 1.0 if source == "product_attributes" else 0.9
                        df_enriched.at[idx, 'bv_existing_answer'] = f"Generated from {source}"
                        comprehensive_generated_count += 1
                        logger.info(f"Generated answer from {source} for Q{row['Question ID']}: '{question_text}'")
                
                if comprehensive_generated_count > 0:
                    console.print(f"[green]✓ Generated {comprehensive_generated_count} answers from product data and previously answered questions[/green]")
                
                # Now check remaining questions against BazaarVoice data with NLP similarity
                for idx, row in df_enriched.iterrows():
                    # Skip if already answered from comprehensive generation
                    if df_enriched.at[idx, 'bv_previously_answered']:
                        continue
                    
                    product_id = row['Clean_Product_ID']
                    question_text = row['Question title']

                    answered_questions = bv_cache.get(product_id, [])
                    checked_count += 1

                    if answered_questions:
                        # Find best match using enhanced similarity scoring (default threshold 0.75)
                        matching_q = bv_checker.find_matching_questions(question_text, answered_questions, threshold=0.75)

                        if matching_q:
                            original_answer = matching_q['answers'][0] if matching_q['answers'] else None
                            similarity_score = matching_q.get('similarity_score', 1.0)

                            df_enriched.at[idx, 'bv_previously_answered'] = True
                            df_enriched.at[idx, 'bv_existing_answer'] = original_answer
                            df_enriched.at[idx, 'bv_similarity_score'] = similarity_score

                            # Rephrase the answer based on similarity score with validation
                            if original_answer:
                                question_category = df_enriched.at[idx, 'question_category']
                                rephrased, is_valid = rephraser.rephrase_with_context(
                                    original_answer=original_answer,
                                    new_question=question_text,
                                    original_question=matching_q.get('question_text', ''),
                                    similarity_score=similarity_score,
                                    question_category=question_category
                                )
                                
                                if is_valid and rephrased:
                                    df_enriched.at[idx, 'bv_rephrased_answer'] = rephrased
                                    matched_count += 1
                                    logger.info(f"BV match found (score: {similarity_score:.2f}) for Q{row['Question ID']}: '{question_text}'")
                                else:
                                    # Answer didn't pass validation, clear it
                                    df_enriched.at[idx, 'bv_previously_answered'] = False
                                    df_enriched.at[idx, 'bv_existing_answer'] = None
                                    df_enriched.at[idx, 'bv_similarity_score'] = None
                                    logger.warning(f"BV answer validation failed for Q{row['Question ID']}, will send to ChatGPT")
                            else:
                                matched_count += 1
                                logger.info(f"BV match found (score: {similarity_score:.2f}) for Q{row['Question ID']}: '{question_text}'")

            console.print(f"[green]✓ BazaarVoice check complete: {matched_count}/{checked_count} questions previously answered[/green]")
            logger.info(f"BazaarVoice check: {matched_count} matches found out of {checked_count} questions")
            
            console.print(f"[green]✓ Enriched {len(df_enriched)} questions with product attributes and BV data[/green]")
            logger.info(f"Data enrichment complete: {len(df_enriched)} records")
            
            return df_enriched
            
        except Exception as e:
            logger.error(f"Failed to enrich data: {e}", exc_info=True)
            console.print(f"[red]✗ Error enriching data: {e}[/red]")
            raise
    
    def save_enriched_json(self, df_enriched: pd.DataFrame, output_path: str = None) -> str:
        """
        Step 7: Save Enriched JSON with questions grouped by product_id.
        """
        console.print("\n[cyan]Step 4: Building and saving output file...[/cyan]")
        logger.info(f"Saving enriched data to: {output_path}")
        
        try:
            # Build output structure
            output_data = self.output_builder.build_output(df_enriched)
            
            # Save to file
            saved_path = self.output_builder.save_to_file(output_data, output_path)
            
            file_size = os.path.getsize(saved_path)
            console.print(f"[green]✓ Saved to: {os.path.basename(saved_path)} ({file_size:,} bytes)[/green]")
            logger.info(f"Output saved: {saved_path} ({file_size} bytes)")
            
            return saved_path
            
        except Exception as e:
            logger.error(f"Failed to save output: {e}", exc_info=True)
            console.print(f"[red]✗ Error saving output: {e}[/red]")
            raise
    
    def print_processing_summary(self, elapsed_time: float):
        """Print a summary table of the preprocessing pipeline results."""
        table = Table(title="\nProcessing Summary", box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="green", justify="right")
        
        table.add_row("Total Questions", str(self.stats['total_questions']))
        table.add_row("Valid Questions", str(self.stats['valid_product_ids']))
        table.add_row("Unique Products", str(self.stats['successful_api_calls'] + self.stats['failed_api_calls']))
        table.add_row("API Successes", str(self.stats['successful_api_calls']))
        table.add_row("API Failures", str(self.stats['failed_api_calls']), style="yellow" if self.stats['failed_api_calls'] > 0 else "green")
        
        if self.stats['valid_product_ids'] > 0:
            success_rate = (self.stats['successful_api_calls'] / (self.stats['successful_api_calls'] + self.stats['failed_api_calls'])) * 100
            table.add_row("Success Rate", f"{success_rate:.1f}%")
        
        table.add_row("Processing Time", f"{elapsed_time:.1f}s")
        
        console.print(table)
        logger.info(f"Processing complete in {elapsed_time:.1f}s: {self.stats['valid_product_ids']} questions, {self.stats['successful_api_calls']} API successes")
    
    def run_full_pipeline(self, input_csv_path: str, output_json_path: str = None) -> str:
        """
        Run the complete AnswerFlow preprocessing pipeline.
        """
        start_time = time.time()
        
        console.print(Panel.fit(
            "[bold cyan]AnswerFlow Preprocessor[/bold cyan]\n"
            "Preparing customer questions for AI processing",
            border_style="cyan"
        ))
        logger.info("Starting AnswerFlow preprocessing pipeline")
        
        try:
            # Steps 1-2: Read and clean CSV
            df_csv = self.read_and_clean_csv(input_csv_path)
            
            # Get unique product IDs
            unique_product_ids = df_csv['Clean_Product_ID'].unique().tolist()
            
            # Steps 3-5: Fetch and process product data
            product_data = self.fetch_product_data(unique_product_ids)
            
            # Step 6: Merge and enrich data
            df_enriched = self.merge_and_enrich_data(df_csv, product_data)
            
            # Step 7: Save enriched JSON
            output_path = self.save_enriched_json(df_enriched, output_json_path)
            
            # Print summary
            elapsed_time = time.time() - start_time
            self.print_processing_summary(elapsed_time)
            
            console.print("\n[bold green]✓ Preprocessing completed successfully![/bold green]")
            logger.info(f"Pipeline completed successfully in {elapsed_time:.1f}s")
            
            return output_path
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Pipeline failed after {elapsed_time:.1f}s: {e}", exc_info=True)
            console.print(f"\n[bold red]✗ Pipeline failed: {e}[/bold red]")
            console.print(f"[dim]Check log file for details: {log_file}[/dim]")
            raise




def create_batches_from_json(json_path: str, batch_size: int = 20, downloads_dir: str = None) -> tuple:
    """
    Split a large preprocessed JSON into smaller batches for ChatGPT processing.
    Separates pre-answered questions from unanswered questions.
    
    CRITICAL CHANGE: Only sends unanswered questions to ChatGPT.
    Pre-answered questions (BazaarVoice matches, default answers, special handling) 
    are saved separately and merged later during consolidation.
    
    Args:
        json_path: Path to the full preprocessed JSON
        batch_size: Maximum number of questions per batch
        downloads_dir: Directory to save pre-answered questions repository
    
    Returns:
        Tuple of (batches list, pre_answered_json_path)
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        full_data = json.load(f)
    
    # Extract base structure
    base_instructions = full_data.get('instructions_for_ai', '')
    column_data = full_data.get('column_data', [])
    
    # Keep all other metadata
    batch_template = {
        'project': full_data.get('project', ''),
        'instructions_for_ai': base_instructions,
        'column_definitions': full_data.get('column_definitions', {}),
        'columns_and_sequence': full_data.get('columns_and_sequence', []),
        'prompt': full_data.get('prompt', {})
    }
    
    batches = []
    current_batch_data = []
    current_question_count = 0
    
    # Repository for pre-answered questions (to be merged later)
    pre_answered_data = []
    
    # Process each product row in column_data
    for product_row in column_data:
        # Structure: [product_id, product_name, brand_name, product_attributes, warranties, questions]
        if len(product_row) < 6:
            continue
        
        product_id = product_row[0]
        product_name = product_row[1]
        brand_name = product_row[2]
        product_attrs = product_row[3]
        warranties = product_row[4]
        questions = product_row[5]
        
        # Separate questions into pre-answered and unanswered
        unanswered_questions = []
        
        for question in questions:
            # Question structure: [question_id, question_text, question_category, answer, 
            #                      bv_previously_answered, bv_reference_answer, special_handling]
            if len(question) < 7:
                continue
            
            question_id = question[0]
            question_text = question[1]
            question_category = question[2]
            answer = question[3]
            bv_previously_answered = question[4]
            bv_reference_answer = question[5]
            special_handling = question[6]
            
            # FILTER LOGIC:
            # Pre-answered: answer is non-empty OR special_handling is true
            # Unanswered: answer is empty AND special_handling is false
            
            if answer or special_handling:
                # This question is already answered or requires special handling
                # Add to pre-answered repository
                pre_answered_data.append({
                    'product_id': product_id,
                    'product_name': product_name,
                    'brand_name': brand_name,
                    'question_id': question_id,
                    'question_text': question_text,
                    'question_category': question_category,
                    'answer': answer if answer else "",  # Empty for special_handling
                    'answer_category': question_category,  # Use question category
                    'bv_previously_answered': bv_previously_answered
                })
            else:
                # This question needs AI-generated answer
                unanswered_questions.append(question)
        
        # Only create batches if there are unanswered questions
        if unanswered_questions:
            # Split unanswered questions for this product if it has many questions
            for i in range(0, len(unanswered_questions), batch_size):
                batch_questions = unanswered_questions[i:i + batch_size]
                
                # Create a product row for this batch
                batch_product_row = [
                    product_id,
                    product_name,
                    brand_name,
                    product_attrs,  # Use original attributes, not summarized
                    warranties,
                    batch_questions
                ]
                
                current_batch_data.append(batch_product_row)
                current_question_count += len(batch_questions)
                
                # If batch is full, save it and start new one
                if current_question_count >= batch_size:
                    batch = batch_template.copy()
                    batch['column_data'] = current_batch_data
                    batches.append(batch)
                    
                    current_batch_data = []
                    current_question_count = 0
    
    # Add remaining products to final batch
    if current_batch_data:
        batch = batch_template.copy()
        batch['column_data'] = current_batch_data
        batches.append(batch)
    
    # Save pre-answered questions to repository JSON
    pre_answered_json_path = None
    if pre_answered_data and downloads_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pre_answered_filename = f"pre_answered_repository_{timestamp}.json"
        pre_answered_json_path = os.path.join(downloads_dir, pre_answered_filename)
        
        # Structure matches ChatGPT output format for easy merging
        pre_answered_output = {
            "column_headers": [
                "product_id", "product_name", "brand_name", "question_id",
                "question_text", "question_category", "answer", "answer_category",
                "bv_previously_answered"
            ],
            "data": [
                [
                    item['product_id'],
                    item['product_name'],
                    item['brand_name'],
                    item['question_id'],
                    item['question_text'],
                    item['question_category'],
                    item['answer'],
                    item['answer_category'],
                    item['bv_previously_answered']
                ]
                for item in pre_answered_data
            ]
        }
        
        with open(pre_answered_json_path, 'w', encoding='utf-8') as f:
            json.dump(pre_answered_output, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✓ Saved {len(pre_answered_data)} pre-answered questions to: {pre_answered_filename}")
    
    return batches, pre_answered_json_path


def run_chatgpt_in_batches(script_dir: str, json_path: str, batch_size: int = 50):
    """
    Process questions in batches through ChatGPT to avoid context overflow.
    Supports both sequential (single browser) and parallel (multiple browsers) modes.
    
    Args:
        script_dir: Script directory path
        json_path: Path to the preprocessed JSON file
        batch_size: Number of questions per batch (default: 50, optimized for speed)
    
    Returns:
        List of output JSON file paths
    """
    from answerflow_playwright_automation import automate_chatgpt_response_batch
    
    console.print(f"\n[cyan]Creating batches with {batch_size} questions each...[/cyan]")
    logger.info(f"Creating batches from {json_path} with batch_size={batch_size}")
    
    # Create downloads directory
    downloads_dir = os.path.join(script_dir, "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    
    # Create batches with optimized size - RETURNS TUPLE NOW
    batches, pre_answered_json_path = create_batches_from_json(json_path, batch_size, downloads_dir)
    
    # Count questions
    unanswered_questions = sum(
        sum(len(product_row[5]) for product_row in batch.get('column_data', []))
        for batch in batches
    )
    
    # Display separation statistics
    if pre_answered_json_path:
        with open(pre_answered_json_path, 'r', encoding='utf-8') as f:
            pre_answered_output = json.load(f)
            pre_answered_count = len(pre_answered_output.get('data', []))
        
        console.print(f"\n[bold cyan]Question Separation:[/bold cyan]")
        console.print(f"[green]  ✓ Pre-answered questions (saved): {pre_answered_count}[/green]")
        console.print(f"[yellow]  → Unanswered questions (to ChatGPT): {unanswered_questions}[/yellow]")
        console.print(f"[cyan]  Total questions: {pre_answered_count + unanswered_questions}[/cyan]")
        console.print(f"\n[dim]Pre-answered repository: {os.path.basename(pre_answered_json_path)}[/dim]")
        logger.info(f"Separated {pre_answered_count} pre-answered and {unanswered_questions} unanswered questions")
    else:
        console.print(f"[cyan]All {unanswered_questions} questions require AI processing[/cyan]")
    
    console.print(f"\n[cyan]Split {unanswered_questions} unanswered questions into {len(batches)} batch(es)[/cyan]")
    logger.info(f"Created {len(batches)} batches containing {unanswered_questions} total unanswered questions")
    
    # Create downloads directory
    downloads_dir = os.path.join(script_dir, "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    
    # Extract prompt structure from first batch and save as separate file
    if batches:
        prompt_structure = batches[0].get('prompt', {})
        prompt_filename = "answerflow_prompt_instructions.json"
        prompt_path = os.path.join(downloads_dir, prompt_filename)
        
        with open(prompt_path, 'w', encoding='utf-8') as f:
            json.dump(prompt_structure, f, ensure_ascii=False, indent=2)
        
        console.print(f"[green]✓ Saved prompt instructions to: {prompt_filename}[/green]")
        logger.info(f"Prompt instructions saved to: {prompt_path}")
    
    # Prepare batch data WITHOUT prompt section
    batch_list = []
    
    for idx, batch_data in enumerate(batches, start=1):
        # Remove prompt section from batch (it's now in separate file)
        if 'prompt' in batch_data:
            del batch_data['prompt']
        
        # Update instructions to reference external prompt file
        batch_data['instructions_for_ai'] = (
            'CRITICAL FIRST STEP: This batch file should be processed along with the "answerflow_prompt_instructions.json" file. '
            'Before processing this data, you MUST read and fully understand the complete instructions in the "answerflow_prompt_instructions.json" file '
            'which contains comprehensive guidelines, rules, examples, and quality standards that are MANDATORY for this task. '
            'The prompt file contains all answer guidelines, prohibited responses, category validation rules, and output format requirements. '
            'DO NOT proceed with processing until you have reviewed the entire prompt file. '
            'After understanding the prompt instructions file, process the customer questions data from the column_data section below using those instructions. '
            '\n\nCRITICAL OUTPUT REQUIREMENT: You MUST use Python code execution to create a downloadable JSON file named "Processed_AI_Answers.json". '
            'Use json.dumps() to serialize the output data and write it to a file. After creating the file, provide a download link with the exact text '
            '"Download Processed_AI_Answers.json" or "Processed_AI_Answers.json". Do NOT just display the JSON as text - you MUST create a downloadable file. '
            'The automation script is waiting for this specific filename to download and process further.'
        )
        
        batch_questions = sum(len(product_row[5]) for product_row in batch_data.get('column_data', []))
        
        # Save batch JSON (without prompt section)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_filename = f"answerflow_batch_{idx}_of_{len(batches)}_{timestamp}.json"
        batch_path = os.path.join(downloads_dir, batch_filename)
        
        with open(batch_path, 'w', encoding='utf-8') as f:
            json.dump(batch_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Batch {idx} saved to: {batch_path}")
        console.print(f"[dim]Batch {idx}/{len(batches)}: {batch_questions} questions -> {batch_filename}[/dim]")
        
        batch_list.append({
            'prompt': batch_data.get('instructions_for_ai', ''),
            'file_path': batch_path,
            'prompt_file': prompt_path  # Include prompt file path for automation
        })
    
    # Determine processing mode based on batch count
    console.print(f"\n[cyan]{'='*60}[/cyan]")
    console.print(f"[bold cyan]Starting ChatGPT Batch Processing[/bold cyan]")
    console.print(f"[cyan]Total batches: {len(batches)}[/cyan]")
    console.print(f"[cyan]{'='*60}[/cyan]")
    
    # Ask user for processing mode if multiple batches
    use_parallel = False
    parallel_count = 1
    use_headless = False  # Default: visible browsers
    
    if len(batches) > 5:
        console.print(f"\n[yellow]You have {len(batches)} batches to process.[/yellow]")
        console.print("[cyan]Processing modes:[/cyan]")
        console.print("  1. Sequential (slower, uses less resources)")
        console.print("  2. Parallel - 2 browsers (2x faster)")
        console.print("  3. Parallel - 3 browsers (3x faster, recommended)")
        console.print("  4. Parallel - 4 browsers (4x faster, needs good PC)")
        
        mode = input("\nSelect mode (1-4) [default: 3]: ").strip() or "3"
        parallel_count = int(mode)
        use_parallel = parallel_count > 1
    
    try:
        logger.info(f"Starting ChatGPT batch automation for {len(batches)} batches")
        
        if use_parallel:
            console.print(f"\n[bold cyan]Parallel mode: {parallel_count} browsers at once[/bold cyan]")
            output_files = process_batches_in_parallel(batch_list, max_parallel=parallel_count, headless=use_headless)
        else:
            console.print(f"\n[cyan]Sequential mode: Login once, process all batches[/cyan]")
            output_files = automate_chatgpt_response_batch(batch_list, headless=use_headless)
        
        # Display results
        for idx, output_file in enumerate(output_files, start=1):
            if output_file:
                console.print(f"[green]✓ Batch {idx}/{len(batches)}: {os.path.basename(output_file)}[/green]")
            else:
                console.print(f"[red]✗ Batch {idx}/{len(batches)}: Failed[/red]")
        
        # Filter out None values
        valid_outputs = [f for f in output_files if f]
        
        logger.info(f"Batch automation completed: {len(valid_outputs)}/{len(batches)} successful")
        
        # CONSOLIDATE ALL JSON FILES AND CONVERT TO XLSX (ONCE AT THE END)
        if valid_outputs:
            console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
            console.print(f"[bold cyan]Consolidating {len(valid_outputs)} JSON file(s) into Master XLSX[/bold cyan]")
            console.print(f"[bold cyan]{'='*60}[/bold cyan]\n")
            
            try:
                from json_to_xlsx_converter import consolidate_and_convert_json_to_xlsx
                
                logger.info(f"Consolidating {len(valid_outputs)} JSON files...")
                console.print(f"[cyan]Step 1: Merging {len(valid_outputs)} JSON files into master JSON...[/cyan]")
                
                # Pass pre-answered JSON path for merging
                consolidated_xlsx = consolidate_and_convert_json_to_xlsx(
                    valid_outputs, 
                    downloads_dir,
                    pre_answered_json_path=pre_answered_json_path
                )
                
                if consolidated_xlsx:
                    console.print(f"\n[bold green]✓ SUCCESS: Master XLSX created![/bold green]")
                    console.print(f"[green]  File: {os.path.basename(consolidated_xlsx)}[/green]")
                    console.print(f"[green]  Location: {downloads_dir}[/green]")
                    logger.info(f"✓ Consolidated XLSX: {consolidated_xlsx}")
                else:
                    console.print(f"[yellow]⚠ Consolidation failed, but individual JSON files are available[/yellow]")
                    logger.warning("Consolidation to XLSX failed")
                    
            except Exception as e:
                console.print(f"[red]✗ Consolidation error: {e}[/red]")
                logger.error(f"Consolidation failed: {e}", exc_info=True)
        else:
            console.print(f"[yellow]⚠ No successful batches to consolidate[/yellow]")
        
        return valid_outputs, pre_answered_json_path
        
    except Exception as e:
        console.print(f"[bold red]✗ Batch automation failed: {e}[/bold red]")
        logger.error(f"Batch automation failed: {e}", exc_info=True)
        valid_outputs = []
        pre_answered_json_path = None
    
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    if len(valid_outputs) == len(batches):
        console.print(f"[bold green]✓ All batches processed successfully![/bold green]")
    elif valid_outputs:
        console.print(f"[yellow]⚠ Partial success: {len(valid_outputs)}/{len(batches)} batches completed[/yellow]")
    else:
        console.print(f"[bold red]✗ All batches failed[/bold red]")
    console.print(f"[green]Successfully processed: {len(valid_outputs)}/{len(batches)} batches[/green]")
    console.print(f"[bold cyan]{'='*60}[/bold cyan]")
    
    return valid_outputs, pre_answered_json_path


def select_csv_file():
    """Open Windows file dialog to select CSV file."""
    root = tk.Tk()
    root.withdraw()
    
    file_path = filedialog.askopenfilename(
        title="Select CSV or Excel file with questions",
        filetypes=[
            ("CSV and Excel files", "*.csv;*.xlsx"),
            ("CSV files", "*.csv"),
            ("Excel files", "*.xlsx"),
            ("All files", "*.*")
        ]
    )
    
    root.destroy()
    return file_path


def main():
    """Main function to run the preprocessor."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Check if input file provided via command line
    if len(sys.argv) >= 2:
        input_file = sys.argv[1]
        if len(sys.argv) > 2:
            output_file = sys.argv[2] if os.path.isabs(sys.argv[2]) else os.path.join(script_dir, sys.argv[2])
        else:
            output_file = os.path.join(script_dir, "answerflow_input_for_chatgpt.json")
        max_workers = int(sys.argv[3]) if len(sys.argv) > 3 else 20
    else:
        # Use file dialog for CSV selection
        console.print("[cyan]Opening file browser...[/cyan]")
        input_file = select_csv_file()
        if not input_file:
            console.print("[yellow]No file selected. Exiting.[/yellow]")
            sys.exit(0)
        
        # Set defaults
        output_file = os.path.join(script_dir, "answerflow_input_for_chatgpt.json")
        max_workers = 20
    
    # Always run ChatGPT automation
    run_chatgpt = True
    
    if not os.path.exists(input_file):
        console.print(f"[red]✗ Error: Input file not found: {input_file}[/red]")
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    console.print(f"[dim]Input: {os.path.basename(input_file)}[/dim]")
    console.print(f"[dim]Log file: {log_file}[/dim]\n")
    
    # Clean up old downloaded files (keep Excel files, remove JSON/batch files)
    downloads_dir = os.path.join(script_dir, 'downloads')
    if os.path.exists(downloads_dir):
        console.print("[cyan]Cleaning up old downloaded files...[/cyan]")
        logger.info("Starting cleanup of old downloaded files")
        
        import glob
        # Remove old JSON outputs
        old_json_files = glob.glob(os.path.join(downloads_dir, "output_*.json"))
        old_processed_files = glob.glob(os.path.join(downloads_dir, "Processed_AI_Answers*.json"))
        # Remove old batch JSON files
        old_batch_files = glob.glob(os.path.join(downloads_dir, "answerflow_batch_*.json"))
        # Remove debug files
        old_debug_html = glob.glob(os.path.join(downloads_dir, "debug_page_*.html"))
        old_debug_screenshots = glob.glob(os.path.join(downloads_dir, "debug_screenshot_*.png"))
        
        files_to_remove = old_json_files + old_processed_files + old_batch_files + old_debug_html + old_debug_screenshots
        
        removed_count = 0
        for old_file in files_to_remove:
            try:
                os.remove(old_file)
                removed_count += 1
                logger.info(f"  Removed: {os.path.basename(old_file)}")
            except Exception as e:
                logger.warning(f"  Could not remove {os.path.basename(old_file)}: {e}")
        
        if removed_count > 0:
            console.print(f"[green]✓ Cleaned up {removed_count} old file(s) (Excel files preserved)[/green]")
            logger.info(f"Cleaned up {removed_count} old files")
        else:
            console.print(f"[dim]✓ No old files to clean up[/dim]")
            logger.info("No old files to clean up")
    
    # Initialize and run preprocessor
    preprocessor = AnswerFlowPreprocessor(max_workers=max_workers)
    
    try:
        output_path = preprocessor.run_full_pipeline(input_file, output_file)
        
        # Run ChatGPT automation if requested
        if run_chatgpt:
            console.print("\n" + "="*60)
            console.print(Panel.fit(
                "[bold cyan]ChatGPT Batch Processing[/bold cyan]\n"
                "Processing questions in batches to ensure optimal AI responses...",
                border_style="cyan"
            ))
            
            # Use default batch size
            batch_size = 20
            console.print(f"[cyan]Batch size: {batch_size} questions per batch[/cyan]")
            
            try:
                # Run batched ChatGPT automation
                output_files = run_chatgpt_in_batches(script_dir, output_path, batch_size=batch_size)
                
                console.print(f"\n[green]Total output files: {len(output_files)}[/green]")
                if not output_files:
                    console.print(f"[dim]Check log for details: {log_file}[/dim]")
                
            except ImportError as e:
                console.print("[red]✗ ChatGPT automation module not found[/red]")
                logger.error(f"Import error: {e}")
            except Exception as e:
                console.print(f"[red]✗ ChatGPT automation failed: {e}[/red]")
                console.print(f"[dim]Check log for details: {log_file}[/dim]")
                logger.error(f"ChatGPT automation failed: {e}", exc_info=True)
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Processing failed: {e}[/bold red]")
        console.print(f"[dim]Check log for details: {log_file}[/dim]")
        logger.error(f"Main pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
