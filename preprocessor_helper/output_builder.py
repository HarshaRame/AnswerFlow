"""
Output Builder
Constructs the final JSON output with grouped questions and prompts.
"""

import json
import pandas as pd
from typing import Dict, Any
from datetime import datetime


class OutputBuilder:
    """Builds the final JSON output structure."""
    
    def __init__(self):
        """Initialize output builder."""
        self.prompt_structure = self._create_prompt_structure()
    
    def _create_prompt_structure(self) -> Dict[str, Any]:
        """
        Create the structured prompt section.
        
        Returns:
            Dictionary with prompt structure
        """
        return {
            'task_description': 'Provide most accurate and short yet complete answers to customer questions posted on JCPenney website on product pages using all the input data.',
            'ai_processing_rules': [
                'DO NOT ask any follow-up questions or request clarifications. Process without any user prompts with only the data provided. Start processing automatically and immediately.',
                'First try to generate answers using input data provided. Later, only if required, refer to data available on JCPenney website and later use your best judgment to form an answer.'
            ],
            'data_structure': {
                'overview': 'The data is structured as a 1D array with separate columns and values arrays. Each row represents one unique product with all its questions nested as a sub-array.',
                'column_data_format': 'Each row in column_data contains: [product_id, product_name, brand_name, product_attributes, warranties, questions]',
                'question_format': 'Each question is an array: [question_id, question_text, answer]. The answer field is initially empty and needs to be populated by AI.'
            },
            'processing_instructions': {
                'step_1': 'Read product data: product_id, product_name, brand_name, product_attributes, warranties',
                'step_2': 'For each product, process all questions in the questions array',
                'step_3': 'QUESTION CATEGORY: Each question has a question_category field (index 2). Read it first to understand what topic the question is about. This will guide your answer.',
                'step_4': 'BAZAARVOICE PRE-ANSWERED QUESTIONS: For each question, check index 3 (answer field). If this field is already filled (non-empty), it means this question was matched with a previously answered question on BazaarVoice OR has a default answer for specific question types. SKIP this question - do NOT modify or regenerate the answer. Keep the existing answer as-is.',
                'step_5': 'NEW QUESTIONS ONLY: For questions with EMPTY answer field (index 3 = ""), check index 6 (special_handling). If true AND answer is blank, this is a credit card/shipping/returns question - leave the answer blank (do NOT generate an answer). If false or answer has text, this is a NEW question that needs an answer.',
                'step_6': 'GENERATE ANSWER: Generate a comprehensive answer using product_attributes and warranties. Ensure your answer directly addresses the question_category topics.',
                'step_7': 'ANSWER CATEGORY ASSIGNMENT: After generating an answer, determine what category/categories your answer addresses. Use the same category list: Size/Fit/Shape, Color, How to use/Instructions, Care Information, Manufacturer/Country of origin, Material/Feature, Shipping/Return/Replacement Related Queries, Availability/Inventory, Measurements/Capacity/Volume, Pricing & Promotions, Includes/Pieces info required, Weight, Other. Your answer can have multiple categories (comma-separated).',
                'step_8': 'CATEGORY CROSS-VERIFICATION: CRITICAL - Compare your answer_category with the question_category (index 2). They should match or overlap significantly. For example: If question_category is "Size/Fit/Shape" but your answer_category is "Color", that is WRONG - you answered the wrong question. If question_category is "Color, Material/Feature" and your answer_category is "Material/Feature", that is acceptable but ensure you also address Color if mentioned in the question. If categories do not match, REVISE your answer to properly address the question_category topics.',
                'step_9': 'REFERENCE ANSWERS: If index 4 is true but index 3 is empty (low similarity match), you may reference the BazaarVoice answer from index 5 for context, but generate a fresh answer tailored to the specific new question.',
                'step_10': 'OUTPUT: Include ALL questions in your output. For pre-answered questions, copy the answer from index 3. For new questions, populate index 3 with your generated answer. For credit card/shipping/returns questions (index 6 true, blank answer), leave answer blank. Always include both question_category (from index 2) and your assigned answer_category in the final output.'
            },
            'answer_guidelines': {
                'PRIMARY_RULE': 'MANDATORY: Before answering ANY question, you MUST first examine these three sections in order: (1) product_name - to understand what the product is, (2) product_attributes - to extract all available specifications, features, materials, measurements, and details, (3) warranties - to check for protection plans or coverage information. Use this information directly to answer every question. Extract information from product_name, brand_name, product_attributes, and warranties to formulate answers. Only if absolutely no relevant information exists in the provided data should you acknowledge the limitation - but NEVER use vague fallback responses.',
                'CATEGORY_VALIDATION_RULE': 'CRITICAL: Each question has a question_category that tells you what the question is about (e.g., "Color", "Size/Fit/Shape", "Material/Feature"). Your answer MUST address this category. After writing your answer, assign an answer_category based on what your answer actually discusses. Then COMPARE: Does your answer_category match or overlap with the question_category? If a question asks about "Color" but your answer discusses "Material/Feature" only, that is WRONG. If a question is categorized as "Color, Material/Feature" and your answer covers both, that is CORRECT. If categories don\'t match, you MUST revise your answer to properly address the question.',
                'DATA_EXAMINATION_REQUIREMENT': 'CRITICAL: For EVERY question, you MUST explicitly look at the product_name field, then thoroughly examine the product_attributes dictionary (which contains all the product specifications, features, materials, dimensions, care instructions, etc.), and check the warranties array before formulating your answer. This is NON-NEGOTIABLE. The product_attributes field contains all the detailed information you need - you MUST read it and extract relevant data.',
                'special_question_handling': {
                    'size_chart_questions': 'Questions about size charts or size guides will have a pre-filled default answer: "Refer to the Size Chart/Size Guide provided for more information". Copy this answer as-is.',
                    'credit_card_shipping_returns': 'Questions about credit cards, shipping, or returns will have index 6 (special_handling) = true and blank answer. For these questions, leave the answer BLANK - do NOT generate an answer. These questions are handled separately outside of this AI processing.'
                },
                'critical_prohibitions': {
                    'NEVER_leave_blank': 'STRICTLY FORBIDDEN: You MUST NEVER leave any answer field blank or empty. Every single question must receive an answer.',
                    'NEVER_reuse_answers': 'STRICTLY FORBIDDEN: You MUST NEVER use the same answer for different questions. Each question deserves a unique, specific answer tailored to that exact question.',
                    'NEVER_copy_paste': 'STRICTLY FORBIDDEN: You MUST NEVER copy-paste generic responses across multiple questions. Read each question individually and craft a unique response.',
                    'NEVER_skip_questions': 'STRICTLY FORBIDDEN: You MUST answer ALL questions. No skipping, no exceptions.',
                    'NEVER_use_placeholders': 'STRICTLY FORBIDDEN: You MUST NEVER use placeholder text like "Answer here", "TBD", "N/A", or leave empty strings.',
                    'NEVER_mention_unavailable_info': 'ABSOLUTELY FORBIDDEN - CRITICAL CUSTOMER EXPERIENCE RULE: You MUST NEVER say that information is "not available", "not provided", "not specified", "not mentioned", "not included", or "not in the description". NEVER say "the description does not mention", "unable to find this information", "we don\'t have this information", or "details are not available". These phrases make it appear that a third party is answering and creates a poor customer experience. Instead: (1) Use available product data to answer what you CAN, (2) For sizing questions without specific data, direct to Size Guide/Size Chart, (3) For other questions, provide helpful guidance based on product type and available information, (4) Use your best judgment to give helpful context even if exact details aren\'t available. EXAMPLE - WRONG: "This information is not available in the product description." RIGHT: "For specific measurements, please refer to the Size Guide on the product page."',
                    'NEVER_say_no_answer': 'ABSOLUTELY FORBIDDEN: You MUST NEVER use generic cop-out responses like "Sorry, I don\'t have an answer for this question" or "I cannot answer this question" or any variation of "I don\'t have information". You have ALL the product data you need in the product_attributes field. READ IT and USE IT to answer questions. This is NOT optional - you MUST attempt to answer using the provided data.',
                    'NEVER_be_lazy': 'ZERO TOLERANCE FOR LAZY ANSWERS: Giving generic "sorry" responses is completely unacceptable and shows you did not even attempt to read the product_attributes data. You are REQUIRED to analyze the product_attributes dictionary for EVERY question and formulate a real answer using the available information.',
                    'LEAVE_BLANK_IF_NO_INFO': 'CRITICAL RULE - BLANK ANSWERS: If you genuinely cannot find ANY relevant information in product_attributes, product_name, brand_name, or warranties to answer a specific question, you MUST leave the answer field completely BLANK (empty string ""). DO NOT write "I don\'t have information", "Information not available", "Unable to answer", or ANY message about missing information. Simply return an empty string "" for that answer field. The customer will never see a message about missing information - they will either get a real answer or no answer at all. EXAMPLES - WRONG: "I cannot find this information in the product details." WRONG: "This information is not provided." WRONG: "Sorry, I don\'t have details about this." RIGHT: "" (completely blank/empty). This maintains professional customer experience by not drawing attention to missing data.',
                    'NEVER_use_fallback_responses': 'STRICTLY PROHIBITED: You MUST NEVER use fallback responses like "For further details, refer to the product page" or "Please check the product page" or "Visit the product listing for more information". These are lazy cop-outs. You have the product data - USE IT to answer directly.',
                    'NEVER_use_vague_responses': 'ABSOLUTELY FORBIDDEN: You MUST NEVER use vague responses that mention missing information. Instead of saying what\'s NOT available, focus on what IS available or provide helpful guidance. WRONG: "Information is not provided", "This information is not available", "Details not specified". RIGHT: Extract relevant details from available attributes or provide specific guidance (e.g., "Please refer to the Size Guide for measurements" for sizing questions). Be specific and helpful, never mention unavailable information.'
                },
                'mandatory_requirements': {
                    'link_to_attributes': 'CRITICAL: Every question must be answered by directly extracting and using information from the product_attributes, product_name, brand_name, or warranties data. Explicitly link each answer to specific product features available in the data.',
                    'read_each_question': 'YOU MUST read EACH question individually and carefully before answering.',
                    'provide_unique_answers': 'YOU MUST provide a UNIQUE, SPECIFIC answer tailored to each exact question.',
                    'use_attributes_differently': 'YOU MUST use the product attributes to craft DIFFERENT answers for DIFFERENT questions about the same product.',
                    'answer_every_question': 'YOU MUST answer EVERY SINGLE question - no exceptions, no blanks.',
                    'actually_read_product_data': 'CRITICAL: You MUST actually READ the product_attributes dictionary for each product before answering ANY question. The data is RIGHT THERE in the JSON. Use it. Analyze it. Extract relevant information and formulate proper answers.',
                    'always_provide_answer': 'MANDATORY: You must ALWAYS provide a substantive answer using the product_name, brand_name, product_attributes, and warranties data. Use your best judgment to address the customer\'s question based on all available information.'
                },
                'tone': 'Write as a friendly, knowledgeable customer care agent',
                'style': 'Be conversational and helpful, not robotic',
                'length_requirement': 'CRITICAL LENGTH RESTRICTIONS: (1) EVERY answer MUST be a SINGLE sentence only - NO multiple sentences allowed, (2) Maximum length is 300 characters including punctuation and spaces, (3) Be concise and direct - get to the point immediately, (4) If information requires more detail, provide the most important point in one sentence. EXAMPLES - WRONG: "This item is made from 100% polyester. It is durable and easy to care for. You can machine wash it." (3 sentences, too long). RIGHT: "This item is made from 100% polyester and is machine washable." (1 sentence, concise).',
                'sentence_requirement': 'CRITICAL: ALL answers MUST be complete, grammatically correct SINGLE sentences. NEVER quote or copy raw attribute values. NEVER use the format "Attribute: Value" or "Care instructions: X, Y, Z". NEVER dump comma-separated raw data like "100% Polyester, 10 Inches - Front, 19 1/2 In". You MUST transform ALL data into proper conversational sentences with subjects, verbs, and complete thoughts.',
                'strict_prohibition': 'ABSOLUTELY FORBIDDEN: Do NOT echo back raw attribute names and values. Do NOT copy-paste attribute data as-is. Do NOT list measurements or specifications without context. Transform ALL data into natural conversational sentences. Every answer must read like a human customer service agent wrote it, not like you copied from a database.',
                'raw_data_dump_prohibition': 'STRICTLY FORBIDDEN - NO RAW DATA DUMPS: You are absolutely prohibited from providing raw attribute values or comma-separated lists of data. Examples of FORBIDDEN answers: "100% Polyester, 10 Inches - Front, 19 1/2 In", "Material: Cotton", "Size: Large", "Dimensions: 5x7". Instead, you MUST write: "This item is made from 100% polyester material", "The front measures 10 inches and the back is 19.5 inches long", "This is available in a large size". ALWAYS convert data into complete sentences.',
                'invalid_examples': [
                    'WRONG: "Available sizes: 5 Cup" - This is NOT a valid answer',
                    'WRONG: "Care instructions: Machine Wash, Tumble Dry" - This is NOT a valid answer',
                    'WRONG: "100% Polyester, 10 Inches - Front, 19 1/2 In" - This is RAW DATA, NOT a sentence',
                    'WRONG: "This item is made from 100% polyester. It is very durable. You can machine wash it." - MULTIPLE SENTENCES (only 1 allowed)',
                    'WRONG: "This beautiful ring is expertly crafted from premium 14k gold over sterling silver, making it both elegant and affordable for everyday wear." - TOO LONG (over 300 characters)',
                    'CORRECT: "This coffee maker is available in a 5-cup size." (Single sentence, concise)',
                    'CORRECT: "Yes, this item is machine washable and can be tumble dried." (Single sentence, under 300 chars)',
                    'CORRECT: "The attachments are dishwasher safe for easy cleanup." (Single sentence, direct)',
                    'CORRECT: "This is machine washable and should be dried flat." (Single sentence, concise)',
                    'CORRECT: "This ring is crafted from 14k gold over silver." (Single sentence, 49 characters)',
                    'CORRECT: "This item is made from 100% polyester." (Single sentence, direct)',
                    'CORRECT: "The front measures 10 inches and the back is 19.5 inches long." (Single sentence, measurements combined)'
                ],
                'natural_answer_variation': 'CRITICAL - VARY YOUR ANSWER STRUCTURE: Do NOT use the same sentence pattern for every answer. Use natural variations to sound more conversational and less robotic. Examples for the SAME information should be varied: (1) "This comforter is not offered separately; it is only available as a 24-piece complete bedding set." (2) "This product is sold only as a 24-piece set, and the comforter is not listed for individual purchase." (3) "The comforter is not available on its own; it comes as part of the 24-piece set." (4) "This comforter cannot be purchased separately; it is part of the 24-piece bedding set." - ALL are correct variations expressing the same fact. Apply this variation principle to ALL answers.',
                'variation_examples': {
                    'negative_availability': [
                        'GOOD: "This item is not offered separately; it is only available as a complete set."',
                        'GOOD: "This product is sold only as a complete set, and the item is not listed for individual purchase."',
                        'GOOD: "The item is not available on its own; it comes as part of the complete set."',
                        'GOOD: "This item cannot be purchased separately; it is part of the complete set."'
                    ],
                    'positive_availability': [
                        'GOOD: "This is available in blue."',
                        'GOOD: "Yes, this comes in blue."',
                        'GOOD: "This is offered in blue."',
                        'GOOD: "This item is available in blue."'
                    ],
                    'measurements': [
                        'GOOD: "The inseam measures 32 inches."',
                        'GOOD: "This has an inseam of 32 inches."',
                        'GOOD: "The inseam is 32 inches."',
                        'GOOD: "This measures 32 inches for the inseam."'
                    ],
                    'material': [
                        'GOOD: "This is made from 100% cotton."',
                        'GOOD: "This item is crafted from 100% cotton."',
                        'GOOD: "The material is 100% cotton."',
                        'GOOD: "This features 100% cotton construction."'
                    ],
                    'care': [
                        'GOOD: "This is machine washable."',
                        'GOOD: "Yes, this is machine washable."',
                        'GOOD: "This item is machine washable."',
                        'GOOD: "You can machine wash this item."'
                    ]
                },
                'care_instructions_specific': 'SPECIAL ATTENTION FOR CARE QUESTIONS: When asked about washing, drying, cleaning, or care - NEVER quote "Care instructions: X". Instead, directly answer the question in sentence form. Examples: "Yes, this is machine washable" or "The attachments are dishwasher safe" or "This should be spot cleaned only".',
                'size_questions_mandatory_rule': 'MANDATORY RULE FOR SIZING/FIT QUESTIONS: For questions about personal sizing, fit, or "what size should I order" - you MUST direct customers to check the Size Guide and/or Size Chart. However, if asked about product measurements or dimensions (e.g., pillow size, tablecloth dimensions, inseam length), answer using product_attributes data. Examples: "For detailed sizing information, please refer to the Size Guide and Size Chart available on the product page." or "To find your perfect fit, please consult the Size Guide and Size Chart on the product page."',
                'size_question_examples': [
                    'Question: "What size should I order?" → Answer: "For accurate sizing information, please refer to the Size Guide and Size Chart available on the product page to find your perfect fit."',
                    'Question: "Does this run true to size?" → Answer: "To determine the best size for you, please check the Size Guide and Size Chart on the product page for detailed measurements."',
                    'Question: "Will this fit me if I\'m 5\'10\"?" → Answer: "Please refer to the Size Guide and Size Chart on the product page to find the size that best matches your measurements."',
                    'Question: "what is the actual size of these socks?" → Answer: "Please refer to the Size Chart & Size Guide information on the product page for detailed sizing."',
                    'Question: "is this size 7/8 it just says small/large" → Answer: "Please refer to the Size Chart & Size Guide information on the product page for specific sizing details."',
                    'Question: "What are the measurements of this pillow?" → Answer: "This pillow measures 13.7 inches wide by 16 inches high." (Use product_attributes data)',
                    'Question: "What is the inseam?" → Answer: "This pant is available with a 31-inch inseam." (Use product_attributes data)'
                ],
                'attribute_usage': 'MANDATORY ATTRIBUTE EXTRACTION: For every question, you MUST actively search the product_attributes dictionary for relevant information. Extract specific details and transform them into natural, conversational sentences. Do NOT say "information is not provided" without first thoroughly examining all available attributes. Use the data directly - no vague responses, no fallback answers, no cop-outs.',
                'how_to_answer': 'CRITICAL TRANSFORMATION RULE: You MUST convert all product_attributes data into complete, natural language sentences. NEVER copy raw values. Examples of REQUIRED transformations: (1) If product_attributes has "Fiber Content": "100% Polyester" and customer asks about material → Answer: "This item is made from 100% polyester for easy care and durability." NOT "100% Polyester" or "Fiber Content: 100% Polyester". (2) If attributes show "Length - Front": "10 Inches", "Length - Back": "19 1/2 In" and customer asks about measurements → Answer: "The front measures 10 inches, while the back is 19.5 inches long." NOT "10 Inches - Front, 19 1/2 In". (3) If product_attributes contains "Metal": "14k Gold Over Silver" → Answer: "This item is made of 14k gold over silver" NOT "Metal: 14k Gold Over Silver". (4) For care questions with "Care instructions": "Machine Wash, Tumble Dry" → Answer: "Yes, this item is machine washable and can be tumble dried" NOT "Care instructions: Machine Wash, Tumble Dry". EVERY answer must be a grammatically complete sentence with proper structure.',
                'answer_relevance_check': 'MANDATORY ANSWER VALIDATION: Before finalizing each answer, verify that your response DIRECTLY addresses the specific question asked.',
                'generic_answer_examples': [
                    'ABSOLUTELY FORBIDDEN: "This product features quality design and craftsmanship." - This is a meaningless generic answer',
                    'ABSOLUTELY FORBIDDEN: "This product features Memory Foam." - This does not answer most questions',
                    'ABSOLUTELY FORBIDDEN: "This is a great product." - This is not helpful',
                    'ABSOLUTELY FORBIDDEN: "This item is well-made." - This is too vague'
                ],
                'category_validation_examples': [
                    'WRONG: Question category = "Color" | Answer discusses only size → Answer category = "Size/Fit/Shape" | MISMATCH - Answer must discuss color',
                    'WRONG: Question category = "Material/Feature" | Answer discusses only price → Answer category = "Pricing & Promotions" | MISMATCH - Answer must discuss material or features',
                    'CORRECT: Question category = "Color" | Answer: "This item is available in navy blue" → Answer category = "Color" | MATCH',
                    'CORRECT: Question category = "Color, Material/Feature" | Answer: "This shirt is available in red and is made from 100% cotton" → Answer category = "Color, Material/Feature" | MATCH',
                    'CORRECT: Question category = "Size/Fit/Shape" | Answer: "For accurate sizing information, please refer to the Size Guide" → Answer category = "Size/Fit/Shape" | MATCH',
                    'ACCEPTABLE: Question category = "Material/Feature, Care Information" | Answer discusses only material → Answer category = "Material/Feature" | PARTIAL MATCH - Better to address both if possible',
                    'VALIDATION PROCESS: (1) Read question_category, (2) Generate answer, (3) Assign answer_category based on what you discussed, (4) Compare - do they match or overlap?, (5) If no match, revise answer to address the correct category'
                ],
                'answer_variation_instruction': 'MANDATORY - USE VARIED SENTENCE STRUCTURES: When answering multiple questions with similar information, you MUST vary the sentence structure. Do NOT repeat the same pattern like "This item is..." for every answer. Mix up your structures using different word orders, contractions vs full forms, active vs passive voice, etc. Example: If answering 5 questions about availability, use different patterns: (1) "This is not available separately" (2) "The item cannot be purchased on its own" (3) "This product is sold only as a complete set" (4) "Individual purchase is not offered for this item" (5) "This comes only as part of the full set". This makes answers sound natural and conversational instead of robotic.',
                'length': 'Keep answers concise but complete (2-4 sentences typically)'
            },
            'output_format': {
                'type': 'JSON file',
                'filename': 'Processed_AI_Answers.json',
                'structure': {
                    'column_headers': ['product_id', 'product_name', 'brand_name', 'question_id', 'question_text', 'question_category', 'answer', 'answer_category', 'bv_previously_answered'],
                    'data': 'Array of arrays where each inner array represents one question with values in the same order as column_headers'
                },
                'category_list': 'Available categories: Size/Fit/Shape, Color, How to use/Instructions, Care Information, Manufacturer/Country of origin, Material/Feature, Shipping/Return/Replacement Related Queries, Availability/Inventory, Measurements/Capacity/Volume, Pricing & Promotions, Includes/Pieces info required, Weight, Other. Both question_category and answer_category can contain multiple categories separated by commas (e.g., "Color, Material/Feature").',
                'rules': [
                    'Use the EXACT structure: {"column_headers": [...], "data": [...]}',
                    'column_headers must be: ["product_id", "product_name", "brand_name", "question_id", "question_text", "question_category", "answer", "answer_category", "bv_previously_answered"]',
                    'Each item in data array = ONE question as an array of values matching the column_headers order',
                    'If a product has 3 questions, create 3 separate arrays in the data array',
                    'question_category comes from the input data (index 2 of question array)',
                    'answer_category is assigned by you based on what your answer addresses',
                    'CRITICAL: answer_category MUST match or overlap with question_category. If they don\'t match, revise your answer.',
                    'Include bv_previously_answered (true/false) to track which questions were pre-answered',
                    'Ensure proper JSON escaping for special characters (quotes, newlines, etc.)',
                    'All values should be strings in the data arrays except bv_previously_answered which should be boolean'
                ],
                'delivery': 'CRITICAL: Create a downloadable JSON file and provide a download link. The download link MUST include the exact filename "Processed_AI_Answers.json" in the link text (e.g., "Download Processed_AI_Answers.json" or "Processed_AI_Answers.json"). Do NOT use generic text like "Download the JSON file" - always include the actual filename in the link text.',
                'example': '{\n  "column_headers": ["product_id", "product_name", "brand_name", "question_id", "question_text", "question_category", "answer", "answer_category", "bv_previously_answered"],\n  "data": [\n    ["pp5004930352", "14K Gold Ring", "FINE JEWELRY", "7952315", "What is the metal type?", "Material/Feature", "This ring is crafted from 14k gold over silver.", "Material/Feature", false],\n    ["pp5004930352", "14K Gold Ring", "FINE JEWELRY", "7952316", "Is this hypoallergenic?", "Material/Feature", "This ring contains silver, which may cause reactions in some individuals with metal sensitivities.", "Material/Feature", true],\n    ["pp5004930352", "14K Gold Ring", "FINE JEWELRY", "7952317", "What color is this?", "Color", "This ring features a beautiful gold color from the 14k gold plating.", "Color", false]\n  ]\n}'
            },
            'quality_standards': {
                'accurate': 'Base answers only on provided product data',
                'natural': 'Sound human, not like you\'re reading a database',
                'helpful': 'Address the customer\'s actual concern',
                'professional': 'Maintain courteous, respectful tone',
                'concise': 'Don\'t over-explain, but be thorough enough',
                'unique': 'CRITICAL: Each answer must be specifically crafted for its question - NO copy-pasting or reusing answers across different questions',
                'complete': 'CRITICAL: ZERO blank answers allowed - every single question must receive a unique, non-empty response'
            },
            'final_validation_checklist': {
                'before_submission': 'Before submitting your answers, verify:',
                'check_1': 'NO blank or empty answers exist (except for credit card/shipping/returns questions with special_handling=true)',
                'check_2': 'NO duplicate/identical answers for different questions',
                'check_3': 'EVERY question has been processed (answered or left blank per special handling rules)',
                'check_4': 'Each answer is unique and specifically addresses its question',
                'check_5': 'All answers are complete sentences (not raw data dumps)',
                'check_6': 'CATEGORY VALIDATION: Every answer_category matches or overlaps with its question_category',
                'check_7': 'For questions with pre-filled answers, you copied them exactly without modification',
                'check_8': 'Output includes both question_category and answer_category columns',
                'check_9': 'CRITICAL - NO UNAVAILABLE INFO MENTIONS OR LEAVE BLANK: Scan all your answers and ensure NONE contain phrases like "information is not available", "not provided", "not specified", "not mentioned", "description does not include", "unable to find", "we don\'t have", "I don\'t have information", "cannot answer", or any variation mentioning missing data. If you find any such phrase, you have TWO options: (1) REWRITE that answer to focus on what IS available or provide helpful guidance (like directing to Size Guide), OR (2) Leave that answer field completely BLANK (empty string "") with NO explanation. NEVER explain why you cannot answer - just leave it blank.',
                'check_10': 'CRITICAL - LENGTH VALIDATION: Verify EVERY answer is (1) a SINGLE sentence only (one period/exclamation/question mark at the end), (2) maximum 300 characters in length. If any answer violates these rules, REWRITE it to be shorter and use only one sentence.'
            },
            'unavailable_info_examples': {
                'purpose': 'These examples show how to handle questions when exact information might not be in product_attributes - LEAVE BLANK if truly no info available',
                'wrong_approach': [
                    'WRONG: "The warranty information is not available in the product description."',
                    'WRONG: "This information is not provided."',
                    'WRONG: "Unfortunately, the product description does not specify the dimensions."',
                    'WRONG: "We don\'t have information about the material composition."',
                    'WRONG: "The exact weight is not mentioned in the product details."',
                    'WRONG: "Sorry, this detail is not available."',
                    'WRONG: "I cannot answer this question."',
                    'WRONG: "Unable to find this information."'
                ],
                'correct_approach': [
                    'RIGHT: "This product comes with the manufacturer\'s standard warranty. For specific warranty details, please contact customer service." (when warranty data is in the JSON)',
                    'RIGHT: "For detailed sizing information, please refer to the Size Guide and Size Chart available on the product page." (for size questions)',
                    'RIGHT: "This [product type] is designed for [general use based on product name and type]." (use context)',
                    'RIGHT: "Based on the product specifications, this item is made from [extract from available attributes]." (use what IS available)',
                    'RIGHT: "For specific care instructions, please check the product label." (for care questions without data)',
                    'RIGHT: "This [product type] typically features [standard features for this product type]." (use product knowledge)',
                    'RIGHT: "" (completely BLANK/empty string - if absolutely NO relevant information exists and no helpful guidance can be provided)'
                ],
                'golden_rule': 'NEVER mention what\'s missing - either answer with available data, provide helpful guidance, OR leave answer completely BLANK (empty string "") with NO explanation about why'
            }
        }
    
    def group_questions_by_product(self, df_enriched: pd.DataFrame) -> list:
        """
        Convert data to simple array format.
        Groups all questions for the same product together.
        
        Args:
            df_enriched: Enriched DataFrame with questions and product attributes
            
        Returns:
            List of product arrays (one row per product with nested questions)
        """
        # Group by product to collect all questions per product
        product_groups = {}
        
        for _, row in df_enriched.iterrows():
            product_id = row['Clean_Product_ID'] if 'Clean_Product_ID' in row and pd.notna(row['Clean_Product_ID']) else str(row['Product ID'])
            
            # Initialize product if not seen before
            if product_id not in product_groups:
                # Parse product_attributes from JSON string
                try:
                    product_attrs = json.loads(row['product_attributes']) if pd.notna(row['product_attributes']) else {}
                except (json.JSONDecodeError, TypeError):
                    product_attrs = {}
                
                product_groups[product_id] = {
                    'product_name': product_attrs.get('name', ''),
                    'brand_name': product_attrs.get('brand', ''),
                    'product_attributes': product_attrs.get('product_attributes', {}),
                    'warranties': product_attrs.get('warranties', []),
                    'questions': []
                }
            
            # Get BazaarVoice check results if available
            bv_previously_answered = row.get('bv_previously_answered', False)
            bv_rephrased_answer = row.get('bv_rephrased_answer', '') if bv_previously_answered else ''
            bv_existing_answer = row.get('bv_existing_answer', '') if bv_previously_answered else ''
            bv_similarity_score = row.get('bv_similarity_score', 0.0)
            
            # Get question category
            question_category = row.get('question_category', 'Other')
            
            # Get special handling info
            special_handling = row.get('special_handling', False)
            default_answer = row.get('default_answer', None)
            
            # Use rephrased answer if available, otherwise use existing answer
            final_bv_answer = bv_rephrased_answer if bv_rephrased_answer else bv_existing_answer
            
            # Add question to this product's questions array
            # Format: [question_id, question_text, question_category, answer_placeholder, bv_previously_answered, bv_answer, special_handling]
            question_id = str(row['Question ID']) if pd.notna(row['Question ID']) else ''
            question_title = str(row['Question title']) if pd.notna(row['Question title']) else ''
            
            # Determine answer placeholder
            if special_handling and default_answer is not None:
                # Use default answer for special questions (e.g., size chart)
                answer_placeholder = default_answer
            elif bv_previously_answered and final_bv_answer:
                # Use the rephrased BV answer directly for all validated matches
                # This includes:
                # 1. High-similarity BazaarVoice matches (score >= 0.75)
                # 2. Answers generated directly from product attributes (score = 1.0)
                # All of these have been validated by the AnswerRephraser
                answer_placeholder = final_bv_answer
            else:
                # Leave empty for AI to fill
                answer_placeholder = ''
            
            product_groups[product_id]['questions'].append([
                question_id, 
                question_title,
                question_category,  # Added question category
                answer_placeholder,  # Pre-filled if special/BV matched with high score, empty otherwise
                bv_previously_answered,
                final_bv_answer,  # For reference even if not pre-filled
                special_handling  # Flag to indicate if this question needs special handling
            ])
        
        # Convert grouped data to values array
        values = []
        for product_id, product_data in product_groups.items():
            row_values = [
                product_id,
                product_data['product_name'],
                product_data['brand_name'],
                product_data['product_attributes'],
                product_data['warranties'],
                product_data['questions']
            ]
            values.append(row_values)
        
        return values
    
    def build_output(self, df_enriched: pd.DataFrame) -> Dict[str, Any]:
        """
        Build the complete output JSON structure.
        
        Args:
            df_enriched: Enriched DataFrame
            
        Returns:
            Complete output data structure
        """
        column_data = self.group_questions_by_product(df_enriched)
        
        output_data = {
            'project': 'eCommerce Product Page Questions and Answers AI POC',
            'instructions_for_ai': 'CRITICAL FIRST STEP: Before doing ANYTHING else, you MUST read and fully understand the "prompt" section at the end of this JSON file. The "prompt" section contains comprehensive guidelines, rules, examples, and quality standards that are MANDATORY for this task. DO NOT proceed with processing until you have reviewed the entire "prompt" section. STRICTLY and INDEFINITELY adhere to ALL instructions in the "prompt" section throughout the entire processing. EFFICIENCY OPTIMIZATION: Many questions have already been answered and rephrased from BazaarVoice data OR have default answers for specific question types. For each question, check index 3 (answer field). If it contains text, the answer is already complete - copy it as-is to your output without modification. This saves you processing time. ONLY generate new answers for questions where index 3 is empty. After understanding the prompt section, process the customer questions data from column_data. CRITICAL DATA EXAMINATION: For NEW questions only (where index 3 is empty), you MUST first look at the product_name field, then thoroughly examine the product_attributes dictionary (which contains all specifications, features, materials, dimensions, care instructions, etc.), and check the warranties array before answering. This is NON-NEGOTIABLE - you must actively extract information from these fields to formulate answers. QUESTION CATEGORY VALIDATION: Each question has a question_category field (index 2). You MUST cross-verify that your answer matches the question category. For example, if the question category is "Size/Fit/Shape" but your answer discusses color, that is WRONG. Ensure your answer addresses the specific category/categories the question falls under. Transform the data into JSON format with the structure: {"column_headers": ["product_id", "product_name", "brand_name", "question_id", "question_text", "question_category", "answer", "answer_category", "bv_previously_answered"], "data": [[...], [...], ...]} where each inner array in "data" represents one question with values in the order specified in column_headers. The "prompt" section is your complete instruction manual - follow it exactly. CRITICAL OUTPUT REQUIREMENTS: (1) For pre-answered questions (index 3 non-empty), copy the answer exactly as provided, (2) For new questions (index 3 empty), generate a unique answer using product data, (3) NEVER leave any answer blank or empty UNLESS index 6 (special_handling) is true AND the default answer is blank (for credit card/shipping/returns questions), (4) NEVER use the same answer for different questions - each answer must be specifically crafted for its question, (5) Answer EVERY SINGLE question that does not have a blank default answer, (6) For each answer you generate, assign an answer_category based on what your answer addresses (use the same category list as question categories), (7) VALIDATE that your answer_category matches or overlaps with the question_category - if they don\'t match, revise your answer. CRITICAL PYTHON CODE EXECUTION REQUIREMENT: You MUST use Python code execution to write the final output to a JSON file. Use json.dumps() to serialize the output data and write it to a file named "Processed_AI_Answers.json". After creating the file, provide a download link with the exact text "Download Processed_AI_Answers.json" or "Processed_AI_Answers.json". Do NOT just display the JSON as text - you MUST create a downloadable file using Python code. Example code: import json; output_data = {...your output...}; with open("Processed_AI_Answers.json", "w") as f: json.dump(output_data, f, indent=2)',
            'column_definitions': {
                'product_id': 'Unique key to identify JCPenney product pages.',
                'product_name': 'Title of the product as displayed on JCPenney website.',
                'brand_name': 'Brand/manufacturer name of the product (e.g., Nike, STAFFORD, A.N.A).',
                'product_attributes': 'Key-value dictionary containing product-specific features and specifications. (e.g., Material, Toe Type Care instructions, Measurements, Fiber Content). This contains BULLETED ATTRIBUTES aggregated from ALL lot IDs - unique values are combined with commas.',
                'warranties': 'List of available warranty/protection plan options for the product. Each warranty has name (title), price (cost in dollars), and description (coverage details). May be empty if no warranties are offered.',
                'questions': 'List of questions for this product. Each question is an array with 7 elements: [question_id, question_text, question_category, answer, bv_previously_answered, bv_reference_answer, special_handling]. The question structure is: Index 0 = question_id (string), Index 1 = question_text (string), Index 2 = question_category (string - comma-separated list of categories like "Color", "Material/Feature", or "Size/Fit/Shape, Color"), Index 3 = answer (string - may be PRE-FILLED with default answer or rephrased BazaarVoice answer for high-confidence matches, or EMPTY for new questions requiring AI generation), Index 4 = bv_previously_answered (boolean, true if matched with BazaarVoice question), Index 5 = bv_reference_answer (string, reference answer from BazaarVoice if available), Index 6 = special_handling (boolean, true for size chart/guide or credit card/shipping/returns questions). PROCESSING RULE: If index 3 is non-empty, the answer is already complete - use it as-is. If index 3 is empty and index 6 is false, generate a new answer using product data. If index 3 is empty and index 6 is true, this is a credit card/shipping/returns question - leave answer blank. CATEGORY VALIDATION RULE: After generating an answer, verify it matches the question_category (index 2) - if the question is about "Color" but your answer discusses "Size", that\'s incorrect.'
            },
            'columns_and_sequence': [
                'product_id',
                'product_name',
                'brand_name',
                'product_attributes',
                'warranties',
                'questions'
            ],
            'column_data': column_data,
            'prompt': self.prompt_structure
        }
        
        return output_data
    
    def save_to_file(self, output_data: Dict[str, Any], output_path: str = None) -> str:
        """
        Save output data to JSON file.
        
        Args:
            output_data: Complete output structure
            output_path: Optional output file path
            
        Returns:
            Path to saved file
        """
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"answerflow_enriched_{timestamp}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        # Calculate and print detailed statistics
        unique_products = len(output_data['column_data'])
        total_questions = 0
        pre_answered = 0
        new_questions = 0
        high_confidence_answers = 0  # Score = 1.0
        medium_confidence_answers = 0  # Score >= 0.75
        special_handling_count = 0
        
        for row in output_data['column_data']:
            questions = row[5]  # questions array
            for question in questions:
                total_questions += 1
                answer = question[3]  # answer field (index 3)
                bv_answered = question[4]  # bv_previously_answered (index 4)
                special_handling = question[6]  # special_handling (index 6)
                
                # Check if answer is pre-filled
                if answer:  # Non-empty answer
                    pre_answered += 1
                    
                    # Track special handling
                    if special_handling:
                        special_handling_count += 1
                    
                    # Try to determine confidence level from the answer source
                    # High confidence = generated from attributes or exact match
                    # Medium confidence = BazaarVoice similarity match
                    if bv_answered:
                        # This is a validated pre-answer (could be from attributes or BV)
                        # Assume high confidence for now (preprocessor validates all answers)
                        high_confidence_answers += 1
                else:
                    new_questions += 1
        
        print(f"  ✓ Saved {unique_products} unique products")
        print(f"  ✓ Total questions: {total_questions}")
        print(f"  ✓ Pre-answered (VALIDATED - will skip ChatGPT): {pre_answered}")
        print(f"    • High-confidence answers (attributes/exact matches): {high_confidence_answers}")
        print(f"    • Special handling (size chart, shipping/returns): {special_handling_count}")
        print(f"  ✓ New questions (need ChatGPT processing): {new_questions}")
        print(f"  ✓ ChatGPT efficiency: {(pre_answered/total_questions*100):.1f}% questions skip ChatGPT")
        print(f"  ✓ Cost savings: ~{pre_answered} fewer API calls needed")
        print(f"  ✓ Format: 1D array with nested questions per product")
        print(f"  ✓ File ready for ChatGPT automation pipeline")
        
        return output_path
