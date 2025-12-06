"""
JSON Processor
Handles JSON data extraction, cleaning, and flattening.
"""

import re
import json
import html
from typing import Dict, Any
from .text_cleaner import TextCleaner


class JSONProcessor:
    """Processes and transforms JSON data from API responses."""
    
    def __init__(self):
        """Initialize JSON processor."""
        self.text_cleaner = TextCleaner()
    
    def strip_html_tags(self, text: str) -> str:
        """
        Remove HTML tags and unescape HTML entities.
        
        Args:
            text: Input text with potential HTML
            
        Returns:
            Clean text without HTML
        """
        if not text:
            return ""
        text = html.unescape(text)
        text = re.sub(r"<.*?>", " ", text)
        return " ".join(text.split()).strip()
    
    def extract_product_attributes(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract required fields from API JSON response.
        
        Args:
            api_data: Raw API response data
            
        Returns:
            Dictionary with product attributes
        """
        if not api_data:
            return {}
        
        # Clean JSON first
        clean_data = self.text_cleaner.clean_json_recursive(api_data)
        product_attributes = {}
        
        try:
            # Extract name
            if 'name' in clean_data:
                product_attributes['name'] = clean_data['name']
            
            # Extract brand name
            brand_obj = clean_data.get("brand", {})
            if isinstance(brand_obj, dict) and 'name' in brand_obj:
                product_attributes['brand'] = brand_obj['name']
            
            # Extract bulleted attributes from ALL lots and combine unique values
            lots = clean_data.get("lots", [])
            if lots:
                # Dictionary to collect all unique values for each attribute key
                combined_attributes = {}
                
                # Loop through all lots to collect bulleted attributes
                for lot in lots:
                    bulleted_attrs = lot.get("bulletedAttributes", [])
                    if bulleted_attrs:
                        for attr in bulleted_attrs:
                            if isinstance(attr, dict) and 'description' in attr:
                                desc = attr['description']
                                if ':' in desc:
                                    key, value = desc.split(':', 1)
                                    key = key.strip()
                                    value = value.strip()
                                    
                                    # Initialize key if not exists
                                    if key not in combined_attributes:
                                        combined_attributes[key] = []
                                    
                                    # Add unique values only
                                    if value not in combined_attributes[key]:
                                        combined_attributes[key].append(value)
                
                # Convert lists to comma-separated strings
                if combined_attributes:
                    attributes_dict = {}
                    for key, values in combined_attributes.items():
                        attributes_dict[key] = ', '.join(values) if len(values) > 1 else values[0]
                    product_attributes['product_attributes'] = attributes_dict
                
                # Check for warranties from first lot and remove itemId
                if len(lots) > 0:
                    warranties = lots[0].get("warranties", [])
                    if warranties:
                        cleaned_warranties = []
                        for warranty in warranties:
                            if isinstance(warranty, dict):
                                cleaned_warranty = {k: v for k, v in warranty.items() if k != 'itemId'}
                                if cleaned_warranty:
                                    cleaned_warranties.append(cleaned_warranty)
                        if cleaned_warranties:
                            product_attributes['warranties'] = cleaned_warranties
        
        except Exception as e:
            print(f"  Warning: Error extracting product attributes: {e}")
        
        return product_attributes
    
    def flatten_api_data(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten API data to product_attributes JSON string.
        
        Args:
            api_data: Raw API response
            
        Returns:
            Dictionary with product_attributes as JSON string
        """
        product_attrs = self.extract_product_attributes(api_data)
        return {
            'product_attributes': json.dumps(product_attrs, ensure_ascii=False) if product_attrs else '{}'
        }
    
    def process_all_products(self, product_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Process all product data from API responses.
        
        Args:
            product_data: Dictionary mapping product_id to raw API data
            
        Returns:
            Dictionary mapping product_id to flattened data
        """
        processed_data = {}
        
        for product_id, api_data in product_data.items():
            if api_data:
                processed_data[product_id] = self.flatten_api_data(api_data)
            else:
                processed_data[product_id] = {'product_attributes': '{}'}
        
        return processed_data
