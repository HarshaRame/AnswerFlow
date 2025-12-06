"""
Answer Rephraser
Rephrases BazaarVoice answers with intelligent cleaning and category validation.
Uses NLP to ensure answers match question categories.
Generates answers from product attributes and previously answered questions.
"""

import random
import re
from typing import List, Optional, Tuple, Dict, Any
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class AnswerRephraser:
    """Rephrase existing answers to provide natural variety with intelligent validation.
    Also generates answers from product attributes and previously answered questions."""
    
    # Conversational artifacts to remove (user-generated content patterns)
    CONVERSATIONAL_PATTERNS = [
        r'^(my apologies|sorry|i apologize)[^\n.!?]*[.!?]\s*',
        r'^(i think|i believe|in my opinion|personally)[^\n.!?]*[.!?]\s*',
        r'^(i read the chart wrong|i measured|i have this|i cannot find)[^\n.!?]*[.!?]\s*',
        r'^(hopefully|maybe|perhaps)\s+someone[^\n.!?]*[.!?]\s*',
        r'hopefully someone[^\n.!?]*[.!?]',
        r'i cannot find[^\n.!?]*[.!?]',
        r'upon receipt[^\n.!?]*,?\s*',
        r'and i measured[^\n.!?]*,?\s*',
        r'according to my[^\n.!?]*,?\s*'
    ]
    
    # Salutation patterns to remove (greetings and thank you messages)
    SALUTATION_PATTERNS = [
        r'^(hi|hello|hey|dear|greetings)[\s,]+[^\n.!?]*[.!?]\s*',
        r'^(hi|hello|hey)\s+there[^\n.!?]*[.!?]\s*',
        r'^(thank you|thanks)[\s,]+for\s+(your\s+)?(question|asking|contacting|reaching\s+out)[^\n.!?]*[.!?]\s*',
        r'^(thank you|thanks)[\s,]+for\s+your\s+interest[^\n.!?]*[.!?]\s*',
        r'^(we\s+)?appreciate\s+your\s+(question|interest|inquiry)[^\n.!?]*[.!?]\s*',
        r'(hi|hello|hey|dear)\s+\w+\s*,?\s*(thank you|thanks)[^\n.!?]*[.!?]\s*',
        r'^hi\s+\w+,?\s*',  # Remove "Hi name," at start
        r'^hello\s+\w+,?\s*',  # Remove "Hello name," at start
        r'^thank\s+you\s+for\s+(asking|your\s+question|contacting)[^\n.!?]*[.!?]\s*',
    ]
    
    # Patterns indicating unavailable information (answers to reject)
    UNAVAILABLE_INFO_PATTERNS = [
        r'information (is )?not (available|provided|specified|included|listed)',
        r'(this |the )?information (is )?not in the (product )?description',
        r'not (mentioned|specified|provided|available|listed) in the (product )?(description|details|information)',
        r'(product )?description (does not|doesn\'t) (mention|specify|include|provide)',
        r'not found in the (product )?(description|details|listing)',
        r'unable to (find|locate|determine) (this |the )?information',
        r'(i |we )?do(n\'t| not) have (this |that |the )?information',
        r'details (are )?not (available|provided|specified)',
        r'no information (is )?(available|provided) (about|regarding|for)',
        r'sorry.*(information|details).*(not|unavailable)',
        r'unfortunately.*(information|details).*(not|unavailable)'
    ]
    
    # Sentence starters for variety
    STARTERS = [
        "",  # No starter
        "Based on the product information, ",
        "According to the product details, ",
    ]
    
    # Category-specific keywords to validate answers
    CATEGORY_KEYWORDS = {
        'Weight': ['gram', 'grams', 'ounce', 'oz', 'pound', 'lb', 'kg', 'kilogram', 'weigh', 'weight'],
        'Size/Fit/Shape': ['size', 'fit', 'fits', 'small', 'medium', 'large', 'petite', 'inseam', 'chest', 'waist'],
        'Measurements/Capacity/Volume': ['inch', 'inches', 'cm', 'mm', 'length', 'width', 'height', 'dimension', 'measure'],
        'Color': ['color', 'colour', 'black', 'white', 'red', 'blue', 'green', 'shade', 'tone'],
        'Material/Feature': ['material', 'fabric', 'cotton', 'polyester', 'metal', 'plastic', 'feature', 'closure', 'hook', 'loop', 'zipper', 'button'],
        'Care Information': ['wash', 'dry', 'clean', 'care', 'dishwasher', 'machine', 'hand wash'],
        'Pricing & Promotions': ['price', 'cost', 'dollar', '$', 'sale', 'discount'],
    }
    
    # Natural answer variation templates
    ANSWER_VARIATIONS = {
        'negative_statement': [
            "This {item} isn't offered separately; it's only available as a {full_description}.",
            "This product is sold only as a {full_description}, and the {item} isn't listed for individual purchase.",
            "The {item} isn't available on its own; it comes as part of the {full_description}.",
            "This {item} can't be purchased separately; it's part of the {full_description}."
        ],
        'positive_statement': [
            "This {item} is available in {value}.",
            "Yes, this comes in {value}.",
            "This is offered in {value}.",
            "This item is available in {value}."
        ],
        'measurement': [
            "The {attribute} measures {value}.",
            "This has a {attribute} of {value}.",
            "The {attribute} is {value}.",
            "This measures {value} for the {attribute}."
        ],
        'material': [
            "This is made from {value}.",
            "This item is crafted from {value}.",
            "The material is {value}.",
            "This features {value} construction."
        ],
        'care': [
            "This is {value}.",
            "Yes, this is {value}.",
            "This item is {value}.",
            "You can {value} this item."
        ]
    }
    
    def __init__(self):
        """Initialize the rephraser."""
        import random
        self.random = random
    
    def clean_conversational_answer(self, answer: str) -> str:
        """
        Remove conversational artifacts and user-specific content from BazaarVoice answers.
        
        Args:
            answer: Original answer text
            
        Returns:
            Cleaned answer text
        """
        if not answer or not answer.strip():
            return answer
        
        cleaned = answer.strip()
        
        # Remove salutation patterns first
        for pattern in self.SALUTATION_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Remove conversational patterns
        for pattern in self.CONVERSATIONAL_PATTERNS:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        # Clean up any remaining salutation fragments
        cleaned = re.sub(r'^\s*[,.\s]+', '', cleaned)
        
        # Remove multiple sentences if they contain conversational elements
        sentences = re.split(r'[.!?]\s+', cleaned)
        factual_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Skip sentences that are clearly conversational/personal
            skip_patterns = [
                r'\bi\b.*\b(measured|have|cannot|read)\b',
                r'\bhopefully\b',
                r'\bsomeone\b.*\bcan\b',
                r'\bmy\b.*\b(opinion|experience|pants)\b',
                r'^(hi|hello|hey|dear|thank|thanks)\b',  # Catch any remaining greetings
                r'\bthank you\b.*\b(question|asking|contacting)\b'
            ]
            
            skip = False
            for pattern in skip_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    skip = True
                    break
            
            # Also skip sentences mentioning unavailable information
            if not skip:
                for pattern in self.UNAVAILABLE_INFO_PATTERNS:
                    if re.search(pattern, sentence, re.IGNORECASE):
                        skip = True
                        logger.warning(f"Rejecting sentence mentioning unavailable info: {sentence[:50]}...")
                        break
            
            if not skip:
                factual_sentences.append(sentence)
        
        # Prioritize sentences with factual keywords (measurements, materials, features)
        factual_keywords = [
            r'\b\d+\s*(inch|cm|mm|ounce|oz|gram|pound|lb|kg)\b',  # Measurements with numbers
            r'\b(made of|made from|constructed|material|fabric|cotton|polyester|metal|plastic|steel|aluminum)\b',
            r'\b(feature|includes|has|contains|equipped with|comes with)\b',
            r'\b(wash|washable|dry clean|machine wash|hand wash|care)\b',
            r'\b(yes|no),?\s+\w+',  # Direct yes/no answers
            r'\b(size|fits|available in|dimensions|capacity|weight)\b'
        ]
        
        prioritized_sentences = []
        regular_sentences = []
        
        for sentence in factual_sentences:
            has_factual_keyword = False
            for pattern in factual_keywords:
                if re.search(pattern, sentence, re.IGNORECASE):
                    has_factual_keyword = True
                    break
            
            if has_factual_keyword:
                prioritized_sentences.append(sentence)
            else:
                regular_sentences.append(sentence)
        
        # Use prioritized sentences first, fallback to regular ones
        final_sentences = prioritized_sentences + regular_sentences
        
        # Rejoin factual sentences
        if final_sentences:
            cleaned = '. '.join(final_sentences)
            if not cleaned.endswith('.'):
                cleaned += '.'
        
        # Clean up whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def validate_answer_matches_category(self, answer: str, question_category: str) -> Tuple[bool, str]:
        """
        Validate that the answer actually addresses the question category.
        Also rejects answers mentioning that information is not available.
        
        Args:
            answer: The answer text
            question_category: Comma-separated categories (e.g., "Weight", "Size/Fit/Shape, Color")
            
        Returns:
            Tuple of (is_valid, reason)
        """
        if not answer or not question_category:
            return True, "No validation needed"
        
        answer_lower = answer.lower()
        
        # First, check if answer mentions information is not available
        for pattern in self.UNAVAILABLE_INFO_PATTERNS:
            if re.search(pattern, answer_lower):
                return False, "Answer mentions information is not available (rejected for customer experience)"
        
        categories = [cat.strip() for cat in question_category.split(',')]
        
        # Check if answer contains keywords related to at least one question category
        for category in categories:
            if category in self.CATEGORY_KEYWORDS:
                keywords = self.CATEGORY_KEYWORDS[category]
                if any(keyword in answer_lower for keyword in keywords):
                    return True, f"Answer addresses {category}"
        
        # Special case: If question is about Weight but answer mentions dimensions
        if 'Weight' in categories:
            dimension_keywords = ['inch', 'cm', 'mm', 'length', 'width', 'height', 'dimension']
            if any(kw in answer_lower for kw in dimension_keywords) and not any(kw in answer_lower for kw in self.CATEGORY_KEYWORDS.get('Weight', [])):
                return False, "Answer provides dimensions instead of weight"
        
        # Special case: If question is about Size/Fit but answer doesn't mention sizing
        if 'Size/Fit/Shape' in categories:
            size_keywords = self.CATEGORY_KEYWORDS['Size/Fit/Shape']
            if not any(kw in answer_lower for kw in size_keywords):
                # Check if it's talking about something else entirely
                if any(kw in answer_lower for kw in ['color', 'material', 'price']):
                    return False, "Answer discusses wrong attribute"
        
        # If we can't validate, allow it (benefit of doubt)
        return True, "Cannot validate, allowing"
    
    def extract_factual_info(self, answer: str, question: str) -> Optional[str]:
        """
        Extract only factual information relevant to the question.
        
        Args:
            answer: Original answer
            question: The question being asked
            
        Returns:
            Extracted factual answer or None if can't extract
        """
        # Look for measurement patterns
        measurement_pattern = r'\b\d+\.?\d*\s*(inch|inches|cm|mm|meter|oz|gram|grams|pound|lb|kg)\b'
        measurements = re.findall(measurement_pattern, answer, re.IGNORECASE)
        
        if measurements:
            # If question asks about specific measurement, extract it
            question_lower = question.lower()
            
            if 'inseam' in question_lower:
                inseam_match = re.search(r'inseam\s+(is\s+|measures?\s+)?(\d+\.?\d*\s*inch)', answer, re.IGNORECASE)
                if inseam_match:
                    value = inseam_match.group(2)
                    return f"The inseam measures {value}es."
            
            if 'weight' in question_lower or 'gram' in question_lower:
                weight_match = re.search(r'(\d+\.?\d*\s*(gram|grams|oz|ounce|pound|lb|kg))', answer, re.IGNORECASE)
                if weight_match:
                    value = weight_match.group(1)
                    return f"This item weighs {value}."
        
        return None
    
    def generate_answer_from_attributes(self, question: str, product_attributes: dict, 
                                       question_category: str = "") -> Optional[str]:
        """
        Generate an answer directly from product attributes when appropriate.
        Returns None (blank) if information cannot be found - NEVER mention that information is missing.
        
        Args:
            question: The question being asked
            product_attributes: Dictionary of product attributes
            question_category: The category of the question
            
        Returns:
            Generated answer or None (blank) if can't generate - will never mention missing information
        """
        if not product_attributes or not question:
            return None
        
        question_lower = question.lower()
        
        # Weight questions
        if 'weight' in question_category or 'gram' in question_lower or 'weigh' in question_lower:
            weight_keys = ['Weight', 'weight', 'Item Weight', 'Product Weight', 'Chain Weight']
            for key in weight_keys:
                if key in product_attributes:
                    weight_value = product_attributes[key]
                    # Extract numeric value if needed
                    weight_match = re.search(r'(\d+\.?\d*)\s*(gram|grams|g|oz|lb)', str(weight_value), re.IGNORECASE)
                    if weight_match:
                        number = weight_match.group(1)
                        unit = weight_match.group(2).lower()
                        if unit == 'g':
                            unit = 'grams'
                        return f"This item weighs {number} {unit}."
                    return f"This item weighs {weight_value}."
        
        # Inseam questions
        if 'inseam' in question_lower:
            inseam_keys = ['Inseam', 'inseam', 'Leg Length']
            for key in inseam_keys:
                if key in product_attributes:
                    inseam_value = product_attributes[key]
                    # Extract numeric value
                    inseam_match = re.search(r'(\d+\.?\d*)\s*(inch|in|")', str(inseam_value), re.IGNORECASE)
                    if inseam_match:
                        number = inseam_match.group(1)
                        return f"The inseam measures {number} inches."
                    return f"The inseam is {inseam_value}."
        
        # Material/closure questions
        if 'closure' in question_lower or 'fastening' in question_lower:
            closure_keys = ['Closure', 'closure', 'Fastening', 'Closure Type']
            for key in closure_keys:
                if key in product_attributes:
                    closure_value = product_attributes[key]
                    return f"This item features a {closure_value.lower()} closure."
        
        # Color questions
        if 'Color' in question_category and 'color' in question_lower:
            color_keys = ['Color', 'color', 'Colour', 'Primary Color']
            for key in color_keys:
                if key in product_attributes:
                    color_value = product_attributes[key]
                    return f"This item is available in {color_value}."
        
        # Material questions
        if 'Material' in question_category or 'material' in question_lower or 'made of' in question_lower:
            material_keys = ['Material', 'material', 'Fabric', 'Fiber Content', 'Composition']
            for key in material_keys:
                if key in product_attributes:
                    material_value = product_attributes[key]
                    # Use varied answer structure
                    template = self.random.choice(self.ANSWER_VARIATIONS['material'])
                    answer = template.format(value=material_value.lower())
                    return answer
        
        return None
    
    def create_natural_answer(self, answer_type: str, **kwargs) -> Optional[str]:
        """
        Create a natural-sounding answer with varied sentence structures.
        
        Args:
            answer_type: Type of answer (negative_statement, positive_statement, measurement, etc.)
            **kwargs: Template variables (item, value, attribute, full_description, etc.)
            
        Returns:
            Formatted natural answer or None
        """
        if answer_type not in self.ANSWER_VARIATIONS:
            return None
        
        templates = self.ANSWER_VARIATIONS[answer_type]
        template = self.random.choice(templates)
        
        try:
            answer = template.format(**kwargs)
            return answer
        except KeyError:
            return None
        
        return None
    
    def calculate_question_similarity(self, question1: str, question2: str) -> float:
        """
        Calculate similarity between two questions using sequence matching.
        
        Args:
            question1: First question
            question2: Second question
            
        Returns:
            Similarity score between 0 and 1
        """
        if not question1 or not question2:
            return 0.0
        
        # Normalize questions
        q1_clean = re.sub(r'[^\w\s]', '', question1.lower())
        q2_clean = re.sub(r'[^\w\s]', '', question2.lower())
        
        # Use SequenceMatcher for similarity
        similarity = SequenceMatcher(None, q1_clean, q2_clean).ratio()
        
        # Boost similarity if they share important keywords
        q1_words = set(q1_clean.split())
        q2_words = set(q2_clean.split())
        common_words = q1_words & q2_words
        
        # Important keywords that indicate similar questions
        important_keywords = {'weight', 'size', 'color', 'material', 'inseam', 'length', 
                            'width', 'height', 'wash', 'care', 'fit', 'closure'}
        
        important_common = common_words & important_keywords
        if important_common:
            # Boost similarity by 10% for each important common word
            similarity += len(important_common) * 0.1
            similarity = min(similarity, 1.0)
        
        return similarity
    
    def generate_answer_from_previously_answered(self, 
                                                 question: str, 
                                                 previously_answered: List[Dict[str, Any]],
                                                 question_category: str = "",
                                                 similarity_threshold: float = 0.75) -> Optional[str]:
        """
        Generate an answer by finding similar previously answered questions for the same product.
        Returns None (blank) if no match found - NEVER mention that information is missing.
        
        Args:
            question: The new question to answer
            previously_answered: List of dicts with 'question' and 'answer' keys
            question_category: The category of the new question
            similarity_threshold: Minimum similarity score to use an answer (default 0.75)
            
        Returns:
            Generated answer or None (blank) if no good match found - will never mention missing information
        """
        if not previously_answered or not question:
            return None
        
        best_match = None
        best_score = 0.0
        
        # Find the most similar previously answered question
        for prev_qa in previously_answered:
            prev_question = prev_qa.get('question', '')
            prev_answer = prev_qa.get('answer', '')
            
            if not prev_question or not prev_answer:
                continue
            
            # Calculate similarity
            similarity = self.calculate_question_similarity(question, prev_question)
            
            if similarity > best_score:
                best_score = similarity
                best_match = {
                    'question': prev_question,
                    'answer': prev_answer,
                    'similarity': similarity
                }
        
        # If we found a good match, use it
        if best_match and best_score >= similarity_threshold:
            logger.info(f"Found similar previously answered question (score: {best_score:.2f})")
            
            # Clean and validate the answer
            cleaned_answer = self.clean_conversational_answer(best_match['answer'])
            
            if not cleaned_answer or len(cleaned_answer.strip()) < 10:
                return None
            
            # Validate against category
            if question_category:
                is_valid, reason = self.validate_answer_matches_category(cleaned_answer, question_category)
                if not is_valid:
                    logger.warning(f"Previously answered question validation failed: {reason}")
                    return None
            
            # Extract factual info if it's a measurement question
            factual = self.extract_factual_info(cleaned_answer, question)
            if factual:
                return factual
            
            return cleaned_answer
        
        return None
    
    def generate_comprehensive_answer(self,
                                     question: str,
                                     product_attributes: Dict[str, Any] = None,
                                     previously_answered: List[Dict[str, Any]] = None,
                                     question_category: str = "") -> Tuple[Optional[str], str]:
        """
        Comprehensive answer generation using all available sources.
        Tries multiple methods in order of confidence:
        1. Direct product attributes
        2. Previously answered questions
        Returns (None, source) if no answer found - NEVER mentions missing information.
        
        Args:
            question: The question to answer
            product_attributes: Product attribute dictionary
            previously_answered: List of previously answered questions for this product
            question_category: Category of the question
            
        Returns:
            Tuple of (answer, source) where answer is None (blank) if not found, source indicates attempt method
        """
        if not question:
            return None, "no_question"
        
        # Try 1: Generate from product attributes (highest confidence)
        if product_attributes:
            attr_answer = self.generate_answer_from_attributes(
                question=question,
                product_attributes=product_attributes,
                question_category=question_category
            )
            if attr_answer:
                is_valid, _ = self.validate_answer_matches_category(attr_answer, question_category)
                if is_valid:
                    logger.info(f"Generated answer from product attributes")
                    return attr_answer, "product_attributes"
        
        # Try 2: Generate from previously answered questions (high confidence)
        if previously_answered:
            prev_answer = self.generate_answer_from_previously_answered(
                question=question,
                previously_answered=previously_answered,
                question_category=question_category,
                similarity_threshold=0.75
            )
            if prev_answer:
                logger.info(f"Generated answer from previously answered questions")
                return prev_answer, "previously_answered"
        
        # No answer could be generated
        return None, "no_match"
    
    def rephrase_answer(self, original_answer: str, similarity_score: float = 1.0) -> str:
        """
        Rephrase an answer with intelligent cleaning.
        
        Args:
            original_answer: The original answer text
            similarity_score: How similar the questions were (0-1)
            
        Returns:
            Rephrased answer text
        """
        if not original_answer or not original_answer.strip():
            return original_answer
        
        # First, clean conversational artifacts
        cleaned = self.clean_conversational_answer(original_answer)
        
        if not cleaned or len(cleaned.strip()) < 10:
            # Answer was mostly conversational fluff, return empty
            return ""
        
        # Ensure it starts with a capital letter
        if cleaned and cleaned[0].islower():
            cleaned = cleaned[0].upper() + cleaned[1:]
        
        # For very high similarity, keep mostly same
        if similarity_score > 0.95:
            return cleaned
        
        # For moderate similarity, optionally add a starter
        if random.random() < 0.3:
            starter = random.choice(self.STARTERS)
            if starter:
                # Remove existing similar starters
                cleaned = re.sub(r'^(based on|according to)[^,]*,\s*', '', cleaned, flags=re.IGNORECASE)
                cleaned = starter + cleaned[0].lower() + cleaned[1:]
        
        return cleaned
    
    def rephrase_with_context(self, 
                              original_answer: str, 
                              new_question: str,
                              original_question: str,
                              similarity_score: float,
                              question_category: str = "") -> Tuple[str, bool]:
        """
        Rephrase answer considering the new question context with validation.
        
        Args:
            original_answer: The original answer text
            new_question: The new question being asked
            original_question: The original question that was answered
            similarity_score: Similarity score between questions
            question_category: The category of the new question
            
        Returns:
            Tuple of (rephrased_answer, is_valid)
        """
        # First, try to extract factual information specific to the question
        factual = self.extract_factual_info(original_answer, new_question)
        if factual:
            # Validate it matches the category
            is_valid, reason = self.validate_answer_matches_category(factual, question_category)
            if is_valid:
                logger.info(f"Extracted factual answer: {factual[:50]}...")
                return factual, True
        
        # Otherwise, do standard rephrasing
        rephrased = self.rephrase_answer(original_answer, similarity_score)
        
        if not rephrased or len(rephrased.strip()) < 10:
            # Answer became too short after cleaning
            logger.warning("Answer too short after cleaning, marking as invalid")
            return "", False
        
        # Validate the rephrased answer matches the question category
        if question_category:
            is_valid, reason = self.validate_answer_matches_category(rephrased, question_category)
            if not is_valid:
                logger.warning(f"Answer validation failed: {reason}")
                return "", False
        
        return rephrased, True


def rephrase_bazaarvoice_answer(answer: str, similarity_score: float = 1.0) -> str:
    """
    Convenience function to rephrase a BazaarVoice answer.
    
    Args:
        answer: Original answer text
        similarity_score: Similarity score of matched question
        
    Returns:
        Rephrased answer
    """
    rephraser = AnswerRephraser()
    return rephraser.rephrase_answer(answer, similarity_score)

