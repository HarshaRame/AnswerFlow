"""
Question Categorizer
Analyzes customer questions and assigns appropriate categories based on keywords and patterns.
A single question can have multiple categories.

Machine Learning Features:
- Learns new keywords from processed questions
- Updates category patterns dynamically
- Saves learned patterns to disk for persistence
"""

import re
import json
import os
from typing import List, Set, Dict, Tuple
from collections import defaultdict
from datetime import datetime


class QuestionCategorizer:
    """Categorizes customer questions into predefined categories with ML learning."""
    
    def __init__(self, learning_enabled: bool = True):
        """
        Initialize the categorizer.
        
        Args:
            learning_enabled: Whether to enable ML learning from processed questions
        """
        self.learning_enabled = learning_enabled
        self.learned_patterns_file = os.path.join(
            os.path.dirname(__file__), 
            'learned_category_patterns.json'
        )
        
        # Load base patterns
        self.CATEGORY_PATTERNS = self._get_base_patterns()
        
        # Load learned patterns if they exist
        if self.learning_enabled:
            self._load_learned_patterns()
        
        # Statistics for learning
        self.learning_stats = {
            'new_keywords_learned': 0,
            'patterns_updated': 0,
            'last_updated': None
        }
    
    def _get_base_patterns(self) -> Dict:
        """Get the base category patterns."""
        return {
            'Size/Fit/Shape': {
                'keywords': [
                    'size', 'fit', 'fits', 'fitting', 'fitted', 'small', 'medium', 'large', 'xl', 'xxl',
                    'petite', 'plus', 'big', 'tall', 'true to size', 'run small', 'run large',
                    'shape', 'shaped', 'tight', 'loose', 'snug', 'roomy', 'slim', 'regular',
                    'sizing', 'what size', 'which size', 'my size', 'right size', 'perfect size'
                ],
                'patterns': [
                    r'\bsize\s+\d+',
                    r'\d+\s*[x×]\s*\d+',
                    r'\d+[\'\"]\s*x\s*\d+[\'\"]+',
                    r'fit\s+(me|you|him|her)',
                    r'(too|very)\s+(small|big|large|tight|loose)',
                    r'what.*size.*order',
                    r'(does|will).*fit',
                    r'true.*size',
                    r'run\s+(small|large|big)'
                ]
            },
            'Color': {
                'keywords': [
                    'color', 'colour', 'shade', 'hue', 'tone', 'tint',
                    'black', 'white', 'red', 'blue', 'green', 'yellow', 'pink', 'purple',
                    'brown', 'gray', 'grey', 'orange', 'navy', 'beige', 'tan', 'cream',
                    'silver', 'gold', 'bronze', 'rose', 'burgundy', 'maroon', 'teal',
                    'turquoise', 'lavender', 'magenta', 'cyan', 'ivory', 'charcoal',
                    'light', 'dark', 'bright', 'pale', 'deep', 'vivid', 'muted'
                ],
                'patterns': [
                    r'what\s+color',
                    r'which\s+color',
                    r'available.*color',
                    r'(is|are)\s+(this|these|it)\s+\w+\s*\??',
                    r'color\s+options',
                    r'(lighter|darker)\s+than'
                ]
            },
            'How to use/Instructions': {
                'keywords': [
                    'how to', 'how do', 'instructions', 'use', 'operate', 'work', 'works',
                    'install', 'installation', 'setup', 'set up', 'assemble', 'assembly',
                    'apply', 'application', 'activate', 'connect', 'attach', 'detach',
                    'remove', 'replace', 'adjust', 'fold', 'unfold', 'open', 'close',
                    'turn on', 'turn off', 'switch', 'operate', 'directions'
                ],
                'patterns': [
                    r'how\s+(to|do\s+(I|you|we))',
                    r'(can|could)\s+(I|you|we)\s+use',
                    r'(is|are)\s+there\s+(any\s+)?instructions',
                    r'step\s+by\s+step',
                    r'what\s+(is|are)\s+the\s+steps',
                    r'(does|do)\s+(this|it)\s+come\s+with\s+instructions'
                ]
            },
            'Care Information': {
                'keywords': [
                    'wash', 'washing', 'washable', 'machine wash', 'hand wash', 'dry clean',
                    'dry', 'drying', 'tumble dry', 'air dry', 'hang dry', 'dryer', 'iron', 'ironing',
                    'care', 'cleaning', 'clean', 'maintain', 'maintenance', 'launder',
                    'bleach', 'detergent', 'fabric softener', 'stain', 'spot clean',
                    'dishwasher', 'dishwasher safe', 'microwave', 'oven safe',
                    'water', 'temperature', 'temp', 'cold water', 'warm water', 'hot water'
                ],
                'patterns': [
                    r'(can|could|should)\s+(I|you|we)\s+wash',
                    r'(is|are)\s+(this|it|these)\s+washable',
                    r'how\s+to\s+(wash|clean|care)',
                    r'care\s+instructions',
                    r'washing\s+instructions',
                    r'(machine|hand)\s+wash',
                    r'dishwasher\s+safe',
                    r'what\s+temp(erature)?',
                    r'(can|should).*dry',
                    r'(is|are).*(dry\s+clean|washable)'
                ]
            },
            'Manufacturer/Country of origin': {
                'keywords': [
                    'manufacturer', 'made in', 'made by', 'country', 'origin', 'where made',
                    'who makes', 'brand', 'company', 'manufacturer warranty',
                    'imported', 'domestic', 'usa', 'china', 'mexico', 'vietnam',
                    'produced', 'manufactured', 'factory'
                ],
                'patterns': [
                    r'(made|manufactured)\s+in',
                    r'(made|manufactured)\s+by',
                    r'where\s+(is|was)\s+(this|it)\s+(made|from)',
                    r'country\s+of\s+origin',
                    r'(who|what)\s+(makes|manufactures)',
                    r'(is|are)\s+(this|it)\s+made\s+in'
                ]
            },
            'Material/Feature': {
                'keywords': [
                    'material', 'fabric', 'made of', 'made from', 'constructed',
                    'cotton', 'polyester', 'wool', 'silk', 'leather', 'suede', 'nylon',
                    'metal', 'plastic', 'wood', 'glass', 'ceramic', 'stainless steel',
                    'aluminum', 'bronze', 'silver', 'gold', 'brass', 'copper',
                    'feature', 'features', 'has', 'include', 'includes', 'included',
                    'come with', 'comes with', 'contain', 'contains', 'equipped',
                    'waterproof', 'water resistant', 'breathable', 'stretch', 'elastic',
                    'pockets', 'zipper', 'buttons', 'velcro', 'snap', 'hook',
                    'lined', 'lining', 'padded', 'padding', 'insulated', 'reversible',
                    'what is', 'whats', 'made out of', 'fiber', 'content'
                ],
                'patterns': [
                    r'(what|which)\s+(is|are)\s+(the\s+)?material',
                    r'made\s+(of|from|out\s+of)',
                    r'(does|do)\s+(this|it|these)\s+have',
                    r'(is|are)\s+(this|it|these)\s+made\s+(of|from)',
                    r'what.*made',
                    r'(is|are).*(cotton|polyester|leather|metal|plastic|wood)',
                    r'(does|do).*feature',
                    r'what.*feature',
                    r'fiber\s+content'
                ]
            },
            'Shipping/Return/Replacement Related Queries': {
                'keywords': [
                    'ship', 'shipping', 'shipped', 'delivery', 'deliver', 'delivered',
                    'arrive', 'arrival', 'when will', 'how long', 'how soon',
                    'return', 'returns', 'returnable', 'return policy', 'send back',
                    'refund', 'exchange', 'replacement', 'replace', 'warranty claim',
                    'tracking', 'track', 'order status', 'expedite', 'rush',
                    'free shipping', 'shipping cost', 'shipping fee', 'carrier',
                    'ups', 'fedex', 'usps', 'postal', 'days to ship'
                ],
                'patterns': [
                    r'(when|how\s+long).*ship',
                    r'(when|how\s+long).*arrive',
                    r'(when|how\s+long).*deliver',
                    r'(can|could|may)\s+(I|we)\s+return',
                    r'return\s+policy',
                    r'(is|are)\s+(this|it)\s+returnable',
                    r'(can|could|may)\s+(I|we)\s+exchange',
                    r'shipping.*cost',
                    r'free\s+shipping',
                    r'how\s+soon'
                ]
            },
            'Availability/Inventory': {
                'keywords': [
                    'available', 'availability', 'in stock', 'out of stock', 'stock',
                    'restock', 'restocking', 'when available', 'back in stock',
                    'discontinued', 'still available', 'still selling', 'still carry',
                    'carry', 'sold out', 'can I buy', 'can I purchase', 'can I order',
                    'available for purchase', 'for sale', 'buy', 'purchase', 'order'
                ],
                'patterns': [
                    r'(is|are)\s+(this|these|it)\s+(still\s+)?available',
                    r'(is|are)\s+(this|these|it)\s+in\s+stock',
                    r'(when|will)\s+(this|it|these)\s+be\s+(back|available)',
                    r'out\s+of\s+stock',
                    r'sold\s+out',
                    r'(can|could|may)\s+(I|we)\s+(buy|purchase|order)',
                    r'(where|how)\s+(can|do|could)\s+(I|we)\s+(buy|purchase|get|find)',
                    r'still\s+(carry|sell|available)'
                ]
            },
            'Measurements/Capacity/Volume': {
                'keywords': [
                    'measurement', 'measurements', 'dimension', 'dimensions', 'measure',
                    'length', 'width', 'height', 'depth', 'diameter', 'radius',
                    'inches', 'feet', 'centimeter', 'meter', 'cm', 'mm', 'ft',
                    'capacity', 'volume', 'hold', 'holds', 'fit', 'fits',
                    'ounce', 'oz', 'cup', 'cups', 'quart', 'gallon', 'liter', 'ml',
                    'pounds', 'lbs', 'kg', 'gram', 'square feet', 'cubic',
                    'how big', 'how large', 'how tall', 'how long', 'how wide', 'how deep',
                    'what size is', 'actual size', 'inseam', 'sleeve', 'chest', 'waist',
                    'shoulder', 'rise', 'leg opening', 'hem'
                ],
                'patterns': [
                    r'(what|whats)\s+(is|are)\s+(the\s+)?(measurement|dimension)',
                    r'how\s+(big|large|tall|long|wide|deep|high)',
                    r'\d+\s*(inch|foot|feet|cm|mm|meter|oz|cup|gallon|liter|lb)',
                    r'(what|whats)\s+(is|are)\s+the\s+(length|width|height|depth|capacity)',
                    r'how\s+many\s+(ounce|cup|gallon|liter)',
                    r'(inseam|sleeve|chest|waist|shoulder|rise)',
                    r'actual\s+size',
                    r'(what|whats)\s+the\s+size'
                ]
            },
            'Pricing & Promotions': {
                'keywords': [
                    'price', 'cost', 'how much', 'expensive', 'cheap', 'affordable',
                    'sale', 'discount', 'promo', 'promotion', 'coupon', 'code',
                    'deal', 'offer', 'clearance', 'markdown', 'reduced',
                    'percent off', '% off', 'save', 'savings', 'special',
                    'free', 'bonus', 'rebate', 'price match', 'best price',
                    'on sale', 'regular price', 'original price', 'msrp'
                ],
                'patterns': [
                    r'(how\s+much|what.*cost|what.*price)',
                    r'(is|are)\s+(this|it|these)\s+on\s+sale',
                    r'(any|have)\s+(discount|coupon|promo|deal)',
                    r'\$\d+',
                    r'percent\s+off',
                    r'\d+%\s+off',
                    r'price\s+match',
                    r'(cheaper|more\s+expensive)\s+than'
                ]
            },
            'Includes/Pieces info required': {
                'keywords': [
                    'include', 'includes', 'included', 'come with', 'comes with',
                    'what comes', 'whats included', 'piece', 'pieces', 'parts',
                    'set', 'contains', 'package', 'packaged', 'in the box',
                    'accessories', 'attachment', 'attachments', 'components',
                    'items', 'contents', 'bundle', 'kit', 'complete set'
                ],
                'patterns': [
                    r'(what|whats)\s+(is\s+)?included',
                    r'(does|do|will)\s+(this|it|these)\s+come\s+with',
                    r'(does|do)\s+(this|it)\s+include',
                    r'how\s+many\s+pieces',
                    r'what.*in\s+the\s+(box|package|set)',
                    r'(is|are)\s+\w+\s+included',
                    r'come.*with.*\w+',
                    r'set\s+of\s+\d+'
                ]
            },
            'Weight': {
                'keywords': [
                    'weight', 'weigh', 'weighs', 'heavy', 'light', 'lightweight',
                    'pounds', 'lbs', 'ounces', 'oz', 'kilogram', 'kg', 'gram', 'grams',
                    'how heavy', 'how light', 'how much does it weigh'
                ],
                'patterns': [
                    r'(what|whats)\s+(is\s+)?(the\s+)?weight',
                    r'how\s+(heavy|light)',
                    r'(how\s+much|what)\s+does\s+(this|it)\s+weigh',
                    r'\d+\s*(pound|lb|kilogram|kg|ounce|oz|gram)',
                    r'(is|are)\s+(this|it)\s+(heavy|light)'
                ]
            },
            'Other': {
                'keywords': [],
                'patterns': []
            }
        }
    
    # Special question patterns for default answers or skip processing
    SPECIAL_PATTERNS = {
        'size_chart_guide': {
            'keywords': ['size chart', 'size guide', 'sizing chart', 'sizing guide', 'measurement chart', 'fit guide'],
            'patterns': [
                r'size\s+(chart|guide)',
                r'sizing\s+(chart|guide)',
                r'(refer|check|see|view|find).*size\s+(chart|guide)',
                r'measurement\s+chart',
                r'fit\s+guide'
            ],
            'default_answer': 'Refer to the Size Chart/Size Guide provided for more information'
        },
        'credit_card_shipping_returns': {
            'keywords': [
                'credit card', 'debit card', 'payment method', 'pay with', 'accept credit',
                'visa', 'mastercard', 'amex', 'discover', 'paypal',
                'ship', 'shipping', 'delivery', 'when will', 'how long to',
                'return', 'returns', 'return policy', 'send back', 'refund', 'exchange'
            ],
            'patterns': [
                r'credit\s+card',
                r'debit\s+card',
                r'payment\s+(method|option)',
                r'(ship|shipping|delivery)',
                r'(when|how\s+long).*arrive',
                r'return\s+policy',
                r'(can|could)\s+.*return'
            ],
            'default_answer': ''  # Leave blank - don't send to ChatGPT
        }
    }
    
    def _load_learned_patterns(self):
        """Load previously learned patterns from disk."""
        if os.path.exists(self.learned_patterns_file):
            try:
                with open(self.learned_patterns_file, 'r', encoding='utf-8') as f:
                    learned_data = json.load(f)
                
                # Merge learned keywords into existing patterns
                for category, data in learned_data.get('patterns', {}).items():
                    if category in self.CATEGORY_PATTERNS:
                        # Add new keywords that aren't already present
                        existing_keywords = set(self.CATEGORY_PATTERNS[category]['keywords'])
                        new_keywords = set(data.get('keywords', []))
                        self.CATEGORY_PATTERNS[category]['keywords'] = list(existing_keywords | new_keywords)
                
                self.learning_stats['last_updated'] = learned_data.get('last_updated')
                print(f"✓ Loaded learned patterns from {os.path.basename(self.learned_patterns_file)}")
            except Exception as e:
                print(f"⚠ Warning: Could not load learned patterns: {e}")
    
    def _save_learned_patterns(self):
        """Save learned patterns to disk."""
        if not self.learning_enabled:
            return
        
        try:
            learned_data = {
                'last_updated': datetime.now().isoformat(),
                'patterns': {},
                'stats': self.learning_stats
            }
            
            # Save only the learned keywords (not base patterns)
            for category, data in self.CATEGORY_PATTERNS.items():
                if category != 'Other':
                    learned_data['patterns'][category] = {
                        'keywords': data['keywords']
                    }
            
            with open(self.learned_patterns_file, 'w', encoding='utf-8') as f:
                json.dump(learned_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Saved learned patterns to {os.path.basename(self.learned_patterns_file)}")
        except Exception as e:
            print(f"⚠ Warning: Could not save learned patterns: {e}")
    
    def learn_from_processed_questions(self, questions_with_categories: List[Tuple[str, str, str]]):
        """
        Learn new patterns from processed questions with assigned categories.
        
        Args:
            questions_with_categories: List of (question_text, question_category, answer_category) tuples
        """
        if not self.learning_enabled:
            return
        
        new_keywords_count = 0
        
        for question_text, question_category, answer_category in questions_with_categories:
            # Only learn if question and answer categories match (validates correct categorization)
            if not question_category or not answer_category:
                continue
            
            question_cats = set(c.strip() for c in question_category.split(','))
            answer_cats = set(c.strip() for c in answer_category.split(','))
            
            # Find matching categories
            matching_cats = question_cats & answer_cats
            
            if matching_cats:
                # Extract potential new keywords from the question
                normalized_text = self._normalize_text(question_text)
                words = normalized_text.split()
                
                # Extract meaningful bi-grams and tri-grams
                for category in matching_cats:
                    if category in self.CATEGORY_PATTERNS:
                        existing_keywords = set(self.CATEGORY_PATTERNS[category]['keywords'])
                        
                        # Look for 2-3 word phrases that might be useful
                        for i in range(len(words) - 1):
                            bigram = f"{words[i]} {words[i+1]}"
                            if len(bigram) > 5 and bigram not in existing_keywords:
                                # Simple heuristic: if this bigram appears to be meaningful
                                if not all(c.isdigit() or c in '.,?!' for c in bigram.replace(' ', '')):
                                    self.CATEGORY_PATTERNS[category]['keywords'].append(bigram)
                                    new_keywords_count += 1
                        
                        # Extract trigger words (question starters, key terms)
                        for word in words:
                            if len(word) > 3 and word not in existing_keywords:
                                if word.isalpha():  # Only alphabetic words
                                    # Check if word is somewhat unique (not too common)
                                    if word not in ['this', 'that', 'what', 'when', 'where', 'which', 'does']:
                                        self.CATEGORY_PATTERNS[category]['keywords'].append(word)
                                        new_keywords_count += 1
        
        if new_keywords_count > 0:
            self.learning_stats['new_keywords_learned'] += new_keywords_count
            self.learning_stats['patterns_updated'] += 1
            self.learning_stats['last_updated'] = datetime.now().isoformat()
            self._save_learned_patterns()
            print(f"🎓 ML Learning: Added {new_keywords_count} new keywords across categories")
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for better matching.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text (lowercase, cleaned)
        """
        if not text:
            return ''
        
        # Convert to lowercase and strip
        text = text.lower().strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _check_keywords(self, text: str, keywords: List[str]) -> Tuple[bool, float]:
        """
        Check if any keywords are present in the text with scoring.
        
        Args:
            text: Normalized text
            keywords: List of keywords to check
            
        Returns:
            Tuple of (match_found, match_score)
        """
        if not keywords:
            return False, 0.0
        
        match_count = 0
        total_score = 0.0
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Create word boundary pattern for more accurate matching
            # For multi-word keywords, use exact phrase matching
            if ' ' in keyword_lower:
                # Multi-word phrase - use exact matching
                if keyword_lower in text:
                    match_count += 1
                    # Multi-word matches get higher score
                    total_score += 2.0
            else:
                # Single word - use word boundary matching to avoid partial matches
                # e.g., "fit" should not match "outfit" or "benefit"
                pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                if re.search(pattern, text):
                    match_count += 1
                    total_score += 1.0
        
        # Calculate normalized score (0.0 to 1.0)
        if match_count > 0:
            # More matches = higher score, but cap at 1.0
            normalized_score = min(total_score / 3.0, 1.0)
            return True, normalized_score
        
        return False, 0.0
    
    def _check_patterns(self, text: str, patterns: List[str]) -> Tuple[bool, float]:
        """
        Check if any regex patterns match the text with scoring.
        
        Args:
            text: Normalized text
            patterns: List of regex patterns
            
        Returns:
            Tuple of (match_found, match_score)
        """
        if not patterns:
            return False, 0.0
        
        match_count = 0
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                match_count += 1
        
        if match_count > 0:
            # Pattern matches get higher score than simple keyword matches
            # because patterns are more specific
            normalized_score = min(match_count * 1.5 / 3.0, 1.0)
            return True, normalized_score
        
        return False, 0.0
    
    def check_special_question(self, question_text: str) -> dict:
        """
        Check if question requires special handling (default answer or skip).
        
        Args:
            question_text: The question text
            
        Returns:
            Dictionary with 'is_special', 'type', and 'default_answer' keys
        """
        normalized_text = self._normalize_text(question_text)
        
        # Check size chart/guide questions
        size_pattern = self.SPECIAL_PATTERNS['size_chart_guide']
        keyword_match, keyword_score = self._check_keywords(normalized_text, size_pattern['keywords'])
        pattern_match, pattern_score = self._check_patterns(normalized_text, size_pattern['patterns'])
        
        # Lower threshold for special questions (0.3) to catch more cases
        if keyword_match or pattern_match:
            total_score = (keyword_score * 0.6) + (pattern_score * 0.4)
            if total_score >= 0.3:
                return {
                    'is_special': True,
                    'type': 'size_chart_guide',
                    'default_answer': size_pattern['default_answer']
                }
        
        # Check credit card/shipping/returns questions
        skip_pattern = self.SPECIAL_PATTERNS['credit_card_shipping_returns']
        keyword_match, keyword_score = self._check_keywords(normalized_text, skip_pattern['keywords'])
        pattern_match, pattern_score = self._check_patterns(normalized_text, skip_pattern['patterns'])
        
        if keyword_match or pattern_match:
            total_score = (keyword_score * 0.6) + (pattern_score * 0.4)
            if total_score >= 0.3:
                return {
                    'is_special': True,
                    'type': 'credit_card_shipping_returns',
                    'default_answer': skip_pattern['default_answer']
                }
        
        return {
            'is_special': False,
            'type': None,
            'default_answer': None
        }
    
    def categorize(self, question_text: str, threshold: float = 0.3) -> str:
        """
        Categorize a question into one or more categories with confidence scoring.
        
        Args:
            question_text: The question text to categorize
            threshold: Minimum confidence score to assign a category (default 0.3)
            
        Returns:
            Comma-separated string of categories (e.g., "Color, Material/Feature")
        """
        if not question_text:
            return 'Other'
        
        normalized_text = self._normalize_text(question_text)
        category_scores: Dict[str, float] = {}
        
        # Check each category and calculate confidence scores
        for category_name, category_data in self.CATEGORY_PATTERNS.items():
            # Skip 'Other' for now - it's a fallback
            if category_name == 'Other':
                continue
            
            # Check keywords with scoring
            keyword_match, keyword_score = self._check_keywords(normalized_text, category_data['keywords'])
            
            # Check patterns with scoring
            pattern_match, pattern_score = self._check_patterns(normalized_text, category_data['patterns'])
            
            # Combine scores (weighted: patterns are worth more than simple keywords)
            total_score = (keyword_score * 0.6) + (pattern_score * 0.4)
            
            # If score meets threshold, add to category scores
            if total_score >= threshold:
                category_scores[category_name] = total_score
        
        # Sort categories by score (highest first) and take those above threshold
        if category_scores:
            sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
            
            # Take categories with score >= threshold
            # But limit to top 3 to avoid over-categorization
            selected_categories = [cat for cat, score in sorted_categories[:3] if score >= threshold]
            
            if selected_categories:
                return ', '.join(selected_categories)
        
        # If no categories found, use 'Other'
        return 'Other'
    
    def categorize_batch(self, questions: List[str]) -> List[str]:
        """
        Categorize a batch of questions.
        
        Args:
            questions: List of question texts
            
        Returns:
            List of category strings
        """
        return [self.categorize(q) for q in questions]
    
    def get_learning_stats(self) -> dict:
        """Get statistics about ML learning."""
        return self.learning_stats.copy()
    
    def get_category_summary(self, categorized_questions: List[str]) -> Dict[str, int]:
        """
        Get a summary count of questions per category combination.
        
        Args:
            categorized_questions: List of category strings (e.g., ["Color", "Size/Fit/Shape, Color"])
            
        Returns:
            Dictionary mapping category combinations to counts
        """
        summary = defaultdict(int)
        for cat in categorized_questions:
            summary[cat] += 1
        
        # Sort by count descending
        return dict(sorted(summary.items(), key=lambda x: x[1], reverse=True))

