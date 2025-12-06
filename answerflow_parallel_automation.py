"""
Parallel ChatGPT Browser Automation
Processes multiple batches simultaneously using separate browser instances

This module enables parallel processing of AnswerFlow batches using multiple
ChatGPT browser sessions running concurrently.
"""

import sys
import os
from pathlib import Path
import concurrent.futures
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from datetime import datetime
import time

# Add chatgpt_automation to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'chatgpt_automation'))

from answerflow_playwright_automation import automate_chatgpt_response_batch

console = Console()
logger = logging.getLogger(__name__)

def process_single_batch_wrapper(batch_info: tuple, headless: bool = False) -> str:
    """
    Wrapper to process a single batch in its own browser session.
    
    Args:
        batch_info: Tuple of (batch_index, batch_data)
        headless: Run browser in headless mode
    
    Returns:
        Output file path or None if failed
    """
    batch_idx, batch_data = batch_info
    
    try:
        # Log to file only, minimal console output
        logger.info(f"Browser {batch_idx + 1}: Starting session...")
        
        # Process single batch in isolated browser
        result = automate_chatgpt_response_batch([batch_data], headless=headless)
        
        if result and result[0]:
            logger.info(f"Browser {batch_idx + 1}: Completed successfully")
            return result[0]
        else:
            logger.warning(f"Browser {batch_idx + 1}: Failed to process")
            return None
            
    except Exception as e:
        logger.error(f"Parallel batch {batch_idx + 1} failed: {e}", exc_info=True)
        return None

def process_batches_in_parallel(
    batch_list: list, 
    max_parallel: int = 3, 
    headless: bool = False
) -> list:
    """
    Process multiple ChatGPT batches in parallel using separate browser instances.
    
    Args:
        batch_list: List of batch dictionaries to process
        max_parallel: Number of parallel browser sessions (2-4 recommended)
        headless: Run browsers in headless mode (faster, no UI)
    
    Returns:
        List of output file paths (None for failed batches)
    
    Example:
        # Process 10 batches using 3 browsers at once
        results = process_batches_in_parallel(batches, max_parallel=3, headless=True)
    """
    total_batches = len(batch_list)
    
    console.print(f"\n[cyan]Starting parallel processing: {total_batches} batches, {max_parallel} browsers at a time[/cyan]")
    
    if max_parallel > 4:
        console.print("[yellow]⚠ Warning: More than 4 parallel browsers may strain your system[/yellow]")
    
    # Log detailed info to file
    logger.info(f"Parallel processing started: {total_batches} batches, {max_parallel} concurrent browsers")
    
    all_results = [None] * total_batches  # Preserve order
    completed = 0
    
    # Process in chunks
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    ) as progress:
        
        overall_task = progress.add_task(
            f"[cyan]Processing {total_batches} batches...", 
            total=total_batches
        )
        
        # Process batches in chunks of max_parallel
        for chunk_start in range(0, total_batches, max_parallel):
            chunk_end = min(chunk_start + max_parallel, total_batches)
            chunk_size = chunk_end - chunk_start
            
            # Log to file, minimal console output
            logger.info(f"Processing chunk {chunk_start // max_parallel + 1}: Browsers {chunk_start + 1}-{chunk_end}")
            
            # Prepare batch info tuples for this chunk
            chunk_batches = [
                (idx, batch_list[idx]) 
                for idx in range(chunk_start, chunk_end)
            ]
            
            # Process chunk in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_parallel) as executor:
                # Submit all batches in this chunk
                future_to_idx = {
                    executor.submit(process_single_batch_wrapper, batch_info, headless): batch_info[0]
                    for batch_info in chunk_batches
                }
                
                # Wait for completion
                for future in concurrent.futures.as_completed(future_to_idx):
                    batch_idx = future_to_idx[future]
                    try:
                        result = future.result()
                        all_results[batch_idx] = result
                        completed += 1
                        
                        progress.update(overall_task, completed=completed)
                        
                    except Exception as e:
                        logger.error(f"Batch {batch_idx + 1} executor error: {e}", exc_info=True)
            
            # Brief pause between chunks to avoid overwhelming the system
            if chunk_end < total_batches:
                logger.info("Preparing next chunk...")
                time.sleep(2)
    
    # Summary
    successful = sum(1 for r in all_results if r is not None)
    failed = total_batches - successful
    
    console.print(f"\n[green]✓ Parallel processing complete: {successful}/{total_batches} batches successful[/green]")
    if failed > 0:
        console.print(f"[yellow]⚠ {failed} batch(es) failed[/yellow]")
    
    logger.info(f"Parallel processing summary: {successful} successful, {failed} failed")
    
    return all_results

# For testing
if __name__ == "__main__":
    console.print("[yellow]This is a module - import it in answerflow_preprocessor.py[/yellow]")
