"""
BazaarVoice Question Checker
Checks if questions have already been answered on the BazaarVoice platform.
"""

import requests
import json
import gzip
from typing import Dict, List, Optional, Tuple
import logging
from urllib.parse import quote
import re
from difflib import SequenceMatcher

# Try to import brotli for Brotli decompression
try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False
    print("Warning: brotli not available. Brotli-compressed responses will fail.")

# Try to import advanced NLP libraries, fall back to basic matching
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("Warning: sklearn not available. Using basic similarity matching.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BazaarVoiceChecker:
    """Check BazaarVoice API for previously answered questions."""
    
    BASE_URL = "https://apps.bazaarvoice.com/bfd/v1/clients/JCPenney/api-products/cv2/resources/data/questions.json"
    
    HEADERS = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "bv-bfd-token": "1573,main_site,en_US",
        "cache-control": "no-cache",
        "origin": "https://www.jcpenney.com",
        "pragma": "no-cache",
        "referer": "https://www.jcpenney.com/",
        "sec-ch-ua": '"Chromium";v="142", "Microsoft Edge";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
    }
    
    def __init__(self, timeout: int = 30):
        """
        Initialize the BazaarVoice checker.
        
        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        # Create a session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def _decompress_response(self, response: requests.Response) -> str:
        """
        Manually decompress response content if needed.
        
        Args:
            response: The response object
            
        Returns:
            Decompressed text content
        """
        content = response.content
        
        # Check if content looks like gzip (magic number: 0x1f 0x8b)
        if len(content) >= 2 and content[0] == 0x1f and content[1] == 0x8b:
            try:
                logger.debug("Detected gzip compression, decompressing manually")
                decompressed = gzip.decompress(content)
                return decompressed.decode('utf-8')
            except Exception as e:
                logger.error(f"Failed to decompress gzip content: {e}")
                raise
        
        # Try to decode as regular text
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            # Last resort: try latin-1
            return content.decode('latin-1')
    
    def get_answered_questions(self, product_id: str, limit: int = 100) -> Optional[Dict]:
        """
        Fetch answered questions for a product from BazaarVoice API.
        
        Args:
            product_id: JCPenney product ID (e.g., 'pp5001840012')
            limit: Maximum number of questions to retrieve
            
        Returns:
            Dictionary containing the API response, or None if request fails
        """
        try:
            url = f"{self.BASE_URL}?filter=productid%3Aeq%3A{product_id}&filter=contentlocale%3Aeq%3Aen_US%2Cen_GB&filter_questions=contentlocale%3Aeq%3Aen_US%2Cen_GB&filter_answers=contentlocale%3Aeq%3Aen_US%2Cen_GB&filteredstats=questions&include=authors%2Cproducts%2Canswers&limit={limit}&offset=0&sort=submissiontime%3Adesc&apiversion=5.5&displaycode=1573-en_us"
            
            logger.debug(f"Fetching BazaarVoice questions for product: {product_id}")
            
            # Make the request with stream=True to prevent automatic decompression
            response = self.session.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()
            
            # Get the raw content
            response.raw.decode_content = False
            content = response.raw.read()
            print(content)
            

            # Handle decompression based on Content-Encoding
            encoding = response.headers.get('Content-Encoding', '').lower()
            try:
                if encoding == 'gzip' or (len(content) >= 2 and content[0] == 0x1f and content[1] == 0x8b):
                    logger.debug("Detected gzip compression, decompressing...")
                    text_content = gzip.decompress(content).decode('utf-8')
                elif encoding == 'br':
                    if HAS_BROTLI:
                        logger.debug("Detected Brotli compression, decompressing...")
                        text_content = brotli.decompress(content).decode('utf-8')
                    else:
                        logger.error("Brotli compression detected but brotli package is not installed.")
                        return None
                else:
                    text_content = content.decode('utf-8')
                # Parse JSON
                data = json.loads(text_content)
            except (gzip.BadGzipFile, UnicodeDecodeError, json.JSONDecodeError, brotli.error) as e:
                logger.error(f"Failed to process response for {product_id}: {e}")
                logger.error(f"Response status: {response.status_code}")
                logger.error(f"Response headers: {dict(response.headers)}")
                logger.error(f"Content type: {response.headers.get('Content-Type')}")
                logger.error(f"Content encoding: {response.headers.get('Content-Encoding')}")
                logger.error(f"Raw content (first 200 bytes): {content[:200]}")
                return None
            
            # Check for API errors
            if data.get("response", {}).get("HasErrors", False):
                errors = data.get("response", {}).get("Errors", [])
                logger.error(f"BazaarVoice API returned errors: {errors}")
                return None
            
            total_results = data.get("response", {}).get("TotalResults", 0)
            logger.info(f"Found {total_results} questions for product {product_id}")
            return data
            
        except requests.RequestException as e:
            logger.error(f"HTTP error fetching BazaarVoice data for {product_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching BazaarVoice data for {product_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def extract_answered_questions(self, api_response: Dict) -> List[Dict]:
        """
        Extract questions with answers from the API response.
        
        Args:
            api_response: The raw API response dictionary
            
        Returns:
            List of dictionaries containing question and answer information
        """
        answered_questions = []
        
        try:
            results = api_response.get("response", {}).get("Results", [])
            includes = api_response.get("response", {}).get("Includes", {})
            answers_dict = includes.get("Answers", {})
            
            for question in results:
                # Only include questions that have answers
                answer_ids = question.get("AnswerIds", [])
                if answer_ids:
                    question_summary = question.get("QuestionSummary", "")
                    question_id = question.get("Id", "")
                    
                    # Get answer texts
                    answer_texts = []
                    for answer_id in answer_ids:
                        answer = answers_dict.get(answer_id, {})
                        answer_text = answer.get("AnswerText", "")
                        if answer_text:
                            answer_texts.append(answer_text)
                    
                    if answer_texts:
                        answered_questions.append({
                            "bv_question_id": question_id,
                            "question_text": question_summary,
                            "answers": answer_texts,
                            "answer_count": len(answer_texts)
                        })
            
            logger.info(f"Extracted {len(answered_questions)} answered questions")
            
        except Exception as e:
            logger.error(f"Error extracting answered questions: {e}")
        
        return answered_questions
    
    def normalize_question(self, question: str) -> str:
        """
        Normalize question text for comparison.
        
        Args:
            question: Question text
            
        Returns:
            Normalized question text
        """
        # Convert to lowercase
        q = question.lower().strip()
        
        # Remove punctuation except question marks
        q = re.sub(r'[^\w\s?]', '', q)
        
        # Remove extra whitespace
        q = ' '.join(q.split())
        
        return q
    
    def calculate_similarity_score(self, new_question: str, existing_question: str) -> float:
        """
        Calculate similarity score between two questions using advanced NLP or basic matching.
        
        Args:
            new_question: The new question text
            existing_question: The existing question text from BazaarVoice
            
        Returns:
            Similarity score between 0 and 1 (1 = identical)
        """
        # Normalize questions
        new_q = self.normalize_question(new_question)
        existing_q = self.normalize_question(existing_question)
        
        # Exact match
        if new_q == existing_q:
            return 1.0
        
        # Use sklearn if available
        if HAS_SKLEARN:
            try:
                vectorizer = TfidfVectorizer()
                tfidf_matrix = vectorizer.fit_transform([new_q, existing_q])
                similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                return float(similarity)
            except:
                pass  # Fall through to basic matching
        
        # Fall back to SequenceMatcher (built-in Python)
        return SequenceMatcher(None, new_q, existing_q).ratio()
    
    def check_question_similarity(self, new_question: str, existing_question: str, threshold: float = 0.75) -> bool:
        """
        Check if two questions are similar above a certain threshold.
        
        Args:
            new_question: The new question text
            existing_question: The existing question text from BazaarVoice
            threshold: Similarity threshold (0-1), default 0.75
            
        Returns:
            True if questions are similar above threshold, False otherwise
        """
        similarity = self.calculate_similarity_score(new_question, existing_question)
        logger.debug(f"Similarity score: {similarity:.2f} for '{new_question}' vs '{existing_question}'")
        return similarity >= threshold
    
    def find_matching_questions(self, 
                                new_question: str, 
                                answered_questions: List[Dict],
                                threshold: float = 0.75) -> Optional[Dict]:
        """
        Find if a new question matches any previously answered questions.
        
        Args:
            new_question: The new question text to check
            answered_questions: List of previously answered questions
            threshold: Similarity threshold (default 0.75)
            
        Returns:
            Dictionary with matching question, answer, and similarity score, or None if no match
        """
        best_match = None
        best_score = 0.0
        
        for answered_q in answered_questions:
            existing_question = answered_q.get("question_text", "")
            
            similarity = self.calculate_similarity_score(new_question, existing_question)
            
            if similarity >= threshold and similarity > best_score:
                best_score = similarity
                best_match = answered_q.copy()
                best_match['similarity_score'] = similarity
        
        if best_match:
            logger.info(f"Found matching question (score: {best_score:.2f}): '{new_question}' matches '{best_match.get('question_text', '')}'")
        
        return best_match
    
    def close(self):
        """Close the session."""
        if hasattr(self, 'session'):
            self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close session."""
        self.close()


def get_previously_answered_questions(product_id: str) -> Tuple[bool, Optional[List[Dict]]]:
    """
    Convenience function to get previously answered questions for a product.
    
    Args:
        product_id: JCPenney product ID
        
    Returns:
        Tuple of (success: bool, answered_questions: List[Dict] or None)
    """
    try:
        with BazaarVoiceChecker() as checker:
            api_response = checker.get_answered_questions(product_id)
            
            if api_response:
                answered_questions = checker.extract_answered_questions(api_response)
                return True, answered_questions
            else:
                return False, None
                
    except Exception as e:
        logger.error(f"Error in get_previously_answered_questions: {e}")
        return False, None


# Example usage
if __name__ == "__main__":
    # Test the checker
    product_id = "ppr5008506228"
    
    print(f"\n{'='*60}")
    print(f"Testing BazaarVoice Checker for product: {product_id}")
    print(f"{'='*60}\n")
    
    success, answered_questions = get_previously_answered_questions(product_id)
    
    if success and answered_questions:
        print(f"✓ Found {len(answered_questions)} answered questions\n")
        
        # Display first 3 questions as examples
        for i, q in enumerate(answered_questions[:3], 1):
            print(f"Question {i}:")
            print(f"  Text: {q['question_text']}")
            print(f"  Answers: {q['answer_count']}")
            print(f"  First answer: {q['answers'][0][:100]}...")
            print()
        
        # Test question matching
        test_question = "What are the dimensions?"
        print(f"\nTesting question matching for: '{test_question}'")
        
        with BazaarVoiceChecker() as checker:
            match = checker.find_matching_questions(test_question, answered_questions, threshold=0.7)
            
            if match:
                print(f"✓ Found match (similarity: {match['similarity_score']:.2f})")
                print(f"  Matched question: {match['question_text']}")
                print(f"  Answer: {match['answers'][0][:150]}...")
            else:
                print("✗ No matching question found")
    else:
        print("✗ Failed to retrieve questions")