"""
CSV Handler
Manages CSV file reading, cleaning, and validation.
"""

import re
import pandas as pd
from typing import Dict
from .text_cleaner import TextCleaner


class CSVHandler:
    """Handles CSV file operations and validation."""
    
    def __init__(self):
        """Initialize CSV handler."""
        self.text_cleaner = TextCleaner()
        self.ppid_pattern = re.compile(r"\b(pp[pr]?\d{7,})\b", re.I)
        self.stats = {
            'utf_cleaning_applied': 0
        }
    
    def read_csv(self, filepath: str) -> pd.DataFrame:
        """
        Read CSV file with encoding handling.
        
        Args:
            filepath: Path to the CSV file
            
        Returns:
            DataFrame with CSV data
        """
        try:
            return pd.read_csv(filepath, encoding='utf-8', low_memory=False)
        except UnicodeDecodeError:
            try:
                return pd.read_csv(filepath, encoding='latin-1', low_memory=False)
            except Exception:
                return pd.read_csv(filepath, encoding='cp1252', low_memory=False)
    
    def validate_columns(self, df: pd.DataFrame, required_columns: Dict[str, str]) -> None:
        """
        Validate that required columns exist in DataFrame.
        
        Args:
            df: DataFrame to validate
            required_columns: Dictionary of required column mappings
            
        Raises:
            ValueError: If required columns are missing
        """
        missing_cols = [col_name for col_name in required_columns.values() if col_name not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
    
    def filter_columns(self, df: pd.DataFrame, columns_to_retain: list) -> pd.DataFrame:
        """
        Filter DataFrame to retain only specified columns.
        
        Args:
            df: Input DataFrame
            columns_to_retain: List of column names to keep
            
        Returns:
            Filtered DataFrame
        """
        available_columns = [col for col in columns_to_retain if col in df.columns]
        
        if len(available_columns) != len(columns_to_retain):
            missing_cols = set(columns_to_retain) - set(available_columns)
            print(f"  ⚠ Warning: Some columns not found: {missing_cols}")
        
        return df[available_columns].copy()
    
    def clean_text_columns(self, df: pd.DataFrame, text_columns: list) -> pd.DataFrame:
        """
        Clean UTF-8 characters in specified text columns.
        
        Args:
            df: DataFrame to clean
            text_columns: List of column names to clean
            
        Returns:
            DataFrame with cleaned text columns
        """
        for col in text_columns:
            if col in df.columns:
                original_nulls = df[col].isnull().sum()
                df[col] = df[col].apply(self.text_cleaner.clean_text)
                
                cleaned_count = len(df) - original_nulls
                self.stats['utf_cleaning_applied'] += cleaned_count
                print(f"  Cleaned UTF-8 characters in {cleaned_count} '{col}' entries")
        
        return df
    
    def extract_product_id(self, product_id: str) -> str:
        """
        Extract and clean product ID using regex pattern.
        
        Args:
            product_id: Raw product ID from CSV
            
        Returns:
            Clean product ID or empty string if invalid
        """
        if not product_id or pd.isna(product_id):
            return ""
        
        match = self.ppid_pattern.search(str(product_id))
        return match.group(1).lower() if match else ""
    
    def filter_approved_questions(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Filter DataFrame to only approved questions.
        
        Args:
            df: Input DataFrame
            
        Returns:
            Filtered DataFrame with only approved questions
        """
        if 'Question moderation status' in df.columns:
            approved_mask = df['Question moderation status'].str.upper() == 'APPROVED'
            approved_count = approved_mask.sum()
            total_before = len(df)
            df = df[approved_mask].copy()
            print(f"  ✓ Filtered to APPROVED questions: {approved_count} out of {total_before}")
        else:
            print(f"  ⚠ Warning: 'Question moderation status' column not found, processing all questions")
        
        return df
