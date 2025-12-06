"""
API Fetcher
Handles API calls to JCPenney Browse API with multithreading.
"""

import time
import requests
import concurrent.futures
from typing import Dict, Any, Tuple, List


class APIFetcher:
    """Manages API calls to fetch product data."""
    
    def __init__(self, max_workers: int = 20, timeout: int = 20):
        """
        Initialize API fetcher.
        
        Args:
            max_workers: Number of concurrent threads
            timeout: Request timeout in seconds
        """
        self.max_workers = max_workers
        self.timeout = timeout
        
        # API Configuration
        self.browse_api_template = "https://browse-api.jcpenney.com/v2/product-aggregator/{ppid}"
        self.headers = {
            "Accept": "application/json",
            "User-Agent": "jcp-browse-extractor/1.0"
        }
        self.default_store = "2982"
        self.default_zip = "29715"
        
        # Statistics
        self.stats = {
            'successful_calls': 0,
            'failed_calls': 0
        }
    
    def fetch_single_product(self, product_id: str, session: requests.Session) -> Tuple[Dict[str, Any], str]:
        """
        Fetch product data from API for a single product.
        
        Args:
            product_id: Clean product ID
            session: Requests session for connection reuse
            
        Returns:
            Tuple of (api_response_dict, status_string)
        """
        url = self.browse_api_template.format(ppid=product_id)
        params = {"store": self.default_store, "geoZip": self.default_zip}
        
        try:
            response = session.get(url, params=params, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            return response.json(), "success"
        except requests.HTTPError as e:
            status_code = e.response.status_code if e.response else "unknown"
            return {}, f"HTTP_{status_code}"
        except Exception as e:
            return {}, f"error_{type(e).__name__}"
    
    def process_with_retry(self, product_id: str, retries: int = 3) -> Tuple[str, Dict[str, Any], str]:
        """
        Process a single product with retry logic.
        
        Args:
            product_id: Clean product ID
            retries: Number of retry attempts
            
        Returns:
            Tuple of (product_id, api_data, status)
        """
        with requests.Session() as session:
            for attempt in range(retries):
                try:
                    api_data, status = self.fetch_single_product(product_id, session)
                    
                    if status == "success":
                        return product_id, api_data, "success"
                    elif status == "HTTP_404":
                        return product_id, {}, "not_found"
                    elif status.startswith("HTTP_429") or status.startswith("HTTP_5"):
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    else:
                        return product_id, {}, status
                        
                except Exception as e:
                    if attempt == retries - 1:
                        return product_id, {}, f"error_{type(e).__name__}"
                    time.sleep(0.2 * (attempt + 1))
        
        return product_id, {}, "max_retries"
    
    def fetch_all_products(self, product_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Fetch data for all products using multithreading.
        
        Args:
            product_ids: List of clean product IDs
            
        Returns:
            Dictionary mapping product_id to api_data
        """
        if not product_ids:
            print("No product IDs to process")
            return {}
        
        print(f"Fetching data for {len(product_ids)} products using {self.max_workers} workers...")
        
        product_data = {}
        success_count = 0
        error_counts = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_product = {
                executor.submit(self.process_with_retry, pid): pid 
                for pid in product_ids
            }
            
            for i, future in enumerate(concurrent.futures.as_completed(future_to_product), 1):
                product_id, data, status = future.result()
                
                if status == "success":
                    success_count += 1
                    product_data[product_id] = data
                else:
                    error_counts[status] = error_counts.get(status, 0) + 1
                    product_data[product_id] = {}
                
                if i % 25 == 0 or i == len(product_ids):
                    print(f"  Progress: {i}/{len(product_ids)} processed, {success_count} successful")
        
        self.stats['successful_calls'] = success_count
        self.stats['failed_calls'] = len(product_ids) - success_count
        
        print(f"  ✓ API processing complete: {success_count} successful, {len(product_ids) - success_count} failed")
        if error_counts:
            print(f"  Error breakdown: {error_counts}")
        
        return product_data
