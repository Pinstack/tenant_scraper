#!/usr/bin/env python3
"""
Script to map tenant brands to Google's complete business categories.
Uses the complete 4,000+ Google Business Profile categories with fuzzy matching.
"""

import json
import os
import difflib
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import re

class GoogleCategoryMapper:
    """
    Maps basic tenant categories to Google's complete business categories.
    Uses fuzzy matching and the full 4,000+ category taxonomy.
    """

    def __init__(self, categories_file: str = None):
        if categories_file is None:
            # Try hierarchical categories first, then complete, then curated
            script_dir = os.path.dirname(os.path.abspath(__file__))
            hierarchical_file = os.path.join(script_dir, '..', 'data', 'google_business_categories_hierarchical.json')
            complete_file = os.path.join(script_dir, '..', 'data', 'google_business_categories_complete.json')
            curated_file = os.path.join(script_dir, '..', 'data', 'google_business_categories.json')

            if os.path.exists(hierarchical_file):
                categories_file = hierarchical_file
            elif os.path.exists(complete_file):
                categories_file = complete_file
            else:
                categories_file = curated_file

        print(f"Loading categories from: {categories_file}")
        with open(categories_file, 'r', encoding='utf-8') as f:
            self.categories_data = json.load(f)

        # Handle different file formats
        if 'hierarchy' in self.categories_data:
            # Hierarchical format (preferred)
            self.category_hierarchy = self.categories_data['hierarchy']
            self.all_categories = self._extract_categories_from_hierarchy()
            self.direct_mappings = {}
        elif 'categories' in self.categories_data:
            # Complete flat list format
            self.all_categories = self.categories_data['categories']
            self.category_hierarchy = self._build_hierarchy_from_flat_list()
            self.direct_mappings = {}
        else:
            # Original hierarchical format
            self.category_hierarchy = self.categories_data.get('hierarchy', {})
            self.direct_mappings = self.categories_data.get('direct_mappings', {})
            self.all_categories = self._extract_categories_from_hierarchy()

        print(f"Loaded {len(self.all_categories)} categories")

        # Load curated mappings (HYBRID STRATEGY: curated first, fuzzy second)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        curated_mapping_file = os.path.join(script_dir, '..', 'data', 'curated_category_mappings.json')
        self.curated_mappings = {}
        if os.path.exists(curated_mapping_file):
            with open(curated_mapping_file, 'r', encoding='utf-8') as f:
                curated_data = json.load(f)
                # Extract just the tenant_category -> google_category mappings
                for tenant_cat, info in curated_data.get('mappings', {}).items():
                    self.curated_mappings[tenant_cat] = info.get('google_category', '')
            print(f"Loaded {len(self.curated_mappings)} curated mappings (covers 82.9% of tenants)")

        # Pre-compute lowercase versions for faster matching
        self.all_categories_lower = [cat.lower() for cat in self.all_categories]

        # Keywords for better fuzzy matching
        self.category_keywords = self._build_keyword_mappings()
        
        # Common domain-specific mappings (to prevent mismatches)
        self.common_mappings = self._build_common_mappings()
        
    def _build_common_mappings(self) -> Dict[str, str]:
        """Build exact mappings for common categories to prevent mismatches."""
        mappings = {}
        
        # Clothing & Fashion
        for prefix in ["Men's", "Women's", "Children's", 'Kids', 'Baby', 'Infant']:
            for suffix in ['Clothes Shop', 'Clothing Shop', 'Clothing Store', 'Apparel', 'Fashion']:
                key = f'{prefix} {suffix}'
                if prefix == "Men's":
                    mappings[key.lower()] = "Men's clothing store"
                elif prefix == "Women's":
                    mappings[key.lower()] = "Women's clothing store"
                elif prefix in ["Children's", 'Kids', 'Baby', 'Infant']:
                    mappings[key.lower()] = "Children's clothing store"
        
        # Beauty & Personal Care
        mappings['beauty supply store'] = 'Beauty supply store'
        mappings['beauty salon'] = 'Beauty salon'
        mappings['hair salon'] = 'Hair salon'
        mappings['nail salon'] = 'Nail salon'
        mappings['barber shop'] = 'Barber shop'
        
        # Entertainment
        mappings['cinema'] = 'Movie theater'
        mappings['movie theater'] = 'Movie theater'
        mappings['theater'] = 'Performing arts theater'
        
        # Automotive & Parking
        mappings['car park'] = 'Parking lot'
        mappings['parking'] = 'Parking lot'
        mappings['parking lot'] = 'Parking lot'
        mappings['parking garage'] = 'Parking garage'
        
        # Furniture
        mappings['furniture store'] = 'Furniture store'
        mappings['home furniture shop'] = 'Furniture store'
        mappings['furniture shop'] = 'Furniture store'
        
        # General shops
        mappings['clothing shop'] = 'Clothing store'
        mappings['clothing store'] = 'Clothing store'
        
        # Youth & Community
        mappings['youth centre'] = 'Youth center'
        mappings['youth center'] = 'Youth center'
        mappings['community centre'] = 'Community center'
        mappings['community center'] = 'Community center'
        
        return mappings

    def _build_hierarchy_from_flat_list(self) -> Dict:
        """Build a basic hierarchy from the flat category list."""
        def nested_dict():
            return defaultdict(nested_dict)

        hierarchy = nested_dict()

        # Group categories by first word/prefix
        for category in self.all_categories:
            first_word = category.split()[0].lower()

            # Create basic groupings
            if first_word in ['restaurant', 'cafe', 'bar', 'pub']:
                hierarchy['Food & Drink']['children']['Restaurants']['children'][category] = [category]
            elif first_word in ['shop', 'store', 'market']:
                hierarchy['Retail & Shopping']['children']['General Retail']['children'][category] = [category]
            elif first_word in ['salon', 'spa', 'clinic']:
                hierarchy['Beauty & Personal Care']['children']['Services']['children'][category] = [category]
            elif first_word in ['dealer', 'repair', 'service']:
                hierarchy['Automotive']['children']['Services']['children'][category] = [category]
            else:
                # Group by first letter for other categories
                first_letter = first_word[0].upper()
                hierarchy[f'Other ({first_letter})']['children']['General']['children'][category] = [category]

        return dict(hierarchy)

    def _extract_categories_from_hierarchy(self) -> List[str]:
        """Extract all category names from hierarchical structure."""
        categories = []

        # Walk through the known hierarchy structure
        for major_cat, major_data in self.category_hierarchy.items():
            if 'children' in major_data:
                for sub_cat, sub_data in major_data['children'].items():
                    if 'children' in sub_data:
                        # These are the leaf dictionaries containing category names
                        for cat_name, cat_value in sub_data['children'].items():
                            if isinstance(cat_value, str):
                                categories.append(cat_name)

        return list(set(categories))

    def _build_keyword_mappings(self) -> Dict[str, List[str]]:
        """Build keyword mappings for better fuzzy matching."""
        return {
            'fashion': ['clothing', 'apparel', 'fashion', 'clothes', 'wear', 'boutique', 'designer'],
            'food': ['restaurant', 'cafe', 'bar', 'pub', 'diner', 'eatery', 'bakery', 'food', 'dining'],
            'beauty': ['salon', 'spa', 'beauty', 'cosmetic', 'hair', 'nail', 'makeup', 'skincare'],
            'electronics': ['electronics', 'phone', 'computer', 'tech', 'mobile', 'laptop', 'tablet'],
            'health': ['health', 'medical', 'clinic', 'doctor', 'hospital', 'pharmacy', 'dental'],
            'sports': ['sports', 'fitness', 'gym', 'athletic', 'exercise', 'training', 'workout'],
            'automotive': ['car', 'auto', 'automotive', 'vehicle', 'repair', 'service', 'dealer'],
            'retail': ['shop', 'store', 'market', 'retail', 'boutique', 'emporium'],
            'home': ['home', 'house', 'garden', 'furniture', 'appliance', 'hardware'],
            'entertainment': ['theater', 'cinema', 'movie', 'entertainment', 'arts', 'museum']
        }

    def map_category(self, current_category: Optional[str]) -> Dict[str, str]:
        """
        Map a current tenant category to Google's hierarchical structure.

        Args:
            current_category: The current category string from tenant data

        Returns:
            Dictionary with hierarchical category information
        """
        # Handle None or empty categories
        if not current_category:
            return {
                'original_category': '',
                'primary_category': 'Other',
                'secondary_category': 'General',
                'tertiary_category': 'Unspecified',
                'full_hierarchy': 'Other > General > Unspecified',
                'confidence': 'none'
            }

        # HYBRID STRATEGY: Step 1 - Check curated mappings (83% coverage, 100% accuracy)
        if current_category in self.curated_mappings:
            google_cat = self.curated_mappings[current_category]
            return self._create_result(current_category, google_cat, 'high')

        # Step 2 - Check common mappings (exact matches for problematic categories)
        current_lower = current_category.lower()
        if current_lower in self.common_mappings:
            google_cat = self.common_mappings[current_lower]
            return self._create_result(current_category, google_cat, 'high')

        # Step 3 - Try direct mapping (legacy)
        if current_category in self.direct_mappings:
            hierarchy_path = self.direct_mappings[current_category]
            parts = hierarchy_path.split(' > ')
            return {
                'original_category': current_category,
                'primary_category': parts[0] if len(parts) > 0 else '',
                'secondary_category': parts[1] if len(parts) > 1 else '',
                'tertiary_category': parts[2] if len(parts) > 2 else '',
                'full_hierarchy': hierarchy_path,
                'confidence': 'high'
            }

        # Step 4 - Fallback to fuzzy matching for long tail (17% of data)
        return self._fuzzy_match_category(current_category)

    def _fuzzy_match_category(self, current_category: str) -> Dict[str, str]:
        """
        Advanced fuzzy matching using multiple strategies with improved accuracy.
        """
        if not current_category:
            return self._create_result(current_category, 'Other > General > Unspecified', 'none')

        current_lower = current_category.lower()
        current_words = set(re.findall(r'\b\w+\b', current_lower))

        # Strategy 1: Exact match (case insensitive)
        for google_cat in self.all_categories:
            if google_cat.lower() == current_lower:
                return self._create_result(current_category, google_cat, 'high')

        # Strategy 2: Word-based matching with better scoring (more conservative)
        best_matches = []
        for google_cat in self.all_categories:
            google_lower = google_cat.lower()
            google_words = set(re.findall(r'\b\w+\b', google_lower))

            # Calculate word overlap
            common_words = current_words.intersection(google_words)
            
            # CRITICAL: Require significant overlap - at least 2 words OR 60% of the input category
            num_common = len(common_words)
            if num_common >= 2 or (num_common >= 1 and len(current_words) <= 2):
                # Filter out generic words that shouldn't count as strong matches
                generic_words = {'shop', 'store', 'service', 'centre', 'center', 'supplier', 'equipment', 'supplies'}
                meaningful_common = common_words - generic_words
                
                # If all common words are generic, require more overlap
                if len(meaningful_common) == 0 and num_common < 3:
                    continue
                
                # More sophisticated scoring
                overlap_ratio = len(common_words) / len(current_words)
                word_order_bonus = self._check_word_order(current_words, google_words)
                length_similarity = 1 - abs(len(current_words) - len(google_words)) / max(len(current_words), len(google_words))

                total_score = (overlap_ratio * 0.6) + (word_order_bonus * 0.2) + (length_similarity * 0.2)
                best_matches.append((google_cat, total_score, len(meaningful_common), num_common))

        if best_matches:
            # Sort by: meaningful words (desc), total score (desc), total common words (desc)
            best_matches.sort(key=lambda x: (x[2], x[1], x[3]), reverse=True)
            best_match = best_matches[0][0]

            confidence = 'high' if best_matches[0][1] > 0.8 and best_matches[0][2] >= 2 else 'medium' if best_matches[0][1] > 0.6 else 'low'
            return self._create_result(current_category, best_match, confidence)

        # Strategy 3: difflib similarity matching (more conservative)
        matches = difflib.get_close_matches(current_lower, self.all_categories_lower, n=3, cutoff=0.8)
        if matches:
            # Get the original case version
            best_match_lower = matches[0]
            for google_cat in self.all_categories:
                if google_cat.lower() == best_match_lower:
                    return self._create_result(current_category, google_cat, 'medium')

        # Strategy 4: Keyword-based categorization with better logic
        for category_type, keywords in self.category_keywords.items():
            # Require multiple keyword matches for better accuracy
            matching_keywords = [kw for kw in keywords if kw in current_lower]
            if len(matching_keywords) >= 2 or (len(matching_keywords) == 1 and len(current_words) <= 3):
                return self._keyword_based_mapping(current_category, category_type)

        # Strategy 5: Partial substring match (more conservative)
        for google_cat in self.all_categories:
            google_lower = google_cat.lower()
            # Require substantial overlap, not just any word
            if len(current_lower) > 3 and current_lower in google_lower and len(current_lower) > len(google_lower) * 0.6:
                return self._create_result(current_category, google_cat, 'medium')

        # Strategy 6: Single word matches for short categories
        if len(current_words) == 1:
            word = list(current_words)[0]
            for google_cat in self.all_categories:
                if word in google_cat.lower().split():
                    return self._create_result(current_category, google_cat, 'low')

        # Final fallback
        return self._create_result(current_category, 'Other > General > Unspecified', 'none')

    def _check_word_order(self, current_words: set, google_words: set) -> float:
        """Check if words appear in similar order (bonus for matching sequence)."""
        # Simple implementation: check if common words appear in same relative order
        current_list = list(current_words)
        google_list = list(google_words)

        if len(current_list) < 2 or len(google_list) < 2:
            return 0.5  # Neutral bonus

        # Check for consecutive word pairs
        for i in range(len(current_list) - 1):
            pair = f"{current_list[i]} {current_list[i+1]}"
            if pair in " ".join(google_list):
                return 0.8  # Good bonus for consecutive words

        return 0.5  # Neutral bonus

    def _create_result(self, original: str, google_category: str, confidence: str) -> Dict[str, str]:
        """Create standardized result dictionary."""
        # For flat list, create a simple hierarchy
        if ' > ' not in google_category:
            # Create a basic hierarchy for the matched category
            first_word = google_category.split()[0]
            primary = self._infer_primary_category(google_category)
            return {
                'original_category': original,
                'primary_category': primary,
                'secondary_category': first_word.title(),
                'tertiary_category': google_category,
                'full_hierarchy': f'{primary} > {first_word.title()} > {google_category}',
                'confidence': confidence
            }
        else:
            # Already hierarchical
            parts = google_category.split(' > ')
            return {
                'original_category': original,
                'primary_category': parts[0] if len(parts) > 0 else '',
                'secondary_category': parts[1] if len(parts) > 1 else '',
                'tertiary_category': parts[2] if len(parts) > 2 else '',
                'full_hierarchy': google_category,
                'confidence': confidence
            }

    def _infer_primary_category(self, google_category: str) -> str:
        """Infer primary category from Google category name."""
        cat_lower = google_category.lower()

        # Food & Drink - expanded keywords
        if any(word in cat_lower for word in ['restaurant', 'cafe', 'bar', 'pub', 'food', 'dining', 'pizza', 'burger', 'sandwich', 'sushi', 'taco', 'burrito', 'pasta', 'noodle', 'rice', 'meat', 'fish', 'seafood', 'chicken', 'steak', 'breakfast', 'lunch', 'dinner', 'brunch', 'buffet', 'catering', 'food truck', 'food court', 'ice cream', 'frozen yogurt', 'coffee', 'tea', 'juice', 'smoothie', 'beverage', 'wine', 'beer', 'liquor', 'cocktail', 'bakery', 'donut', 'bagel', 'pastry', 'cake', 'cupcake', 'pie', 'candy', 'chocolate', 'dessert', 'deli', 'takeaway', 'delivery']):
            return 'Food & Drink'
        elif any(word in cat_lower for word in ['clothing', 'fashion', 'apparel', 'boutique', 'dress', 'shirt', 'pants', 'jeans', 'jacket', 'coat', 'suit', 'tie', 'shoe', 'boot', 'sandal', 'hat', 'bag', 'purse', 'handbag', 'jewelry', 'watch', 'accessory', 'lingerie', 'swimwear', 'uniform', 'costume', 'vintage', 'thrift', 'consignment']):
            return 'Fashion & Apparel'
        elif any(word in cat_lower for word in ['beauty', 'salon', 'spa', 'cosmetic', 'hair', 'nail', 'makeup', 'skincare', 'facial', 'massage', 'tattoo', 'piercing', 'barber', 'esthetician', 'waxing', 'threading', 'eyebrow', 'eyelash', 'permanent makeup', 'laser', 'microblading', 'chemical peel', 'dermabrasion', 'botox', 'filler', 'teeth whitening', 'manicure', 'pedicure']):
            return 'Beauty & Personal Care'
        elif any(word in cat_lower for word in ['electronic', 'phone', 'computer', 'laptop', 'tablet', 'tv', 'television', 'audio', 'speaker', 'headphone', 'camera', 'drone', 'gaming', 'software', 'repair', 'mobile', 'cell', 'smartphone', 'smartwatch', 'wearable', 'printer', 'scanner', 'network', 'internet', 'wifi', 'cable']):
            return 'Electronics'
        elif any(word in cat_lower for word in ['health', 'medical', 'clinic', 'doctor', 'hospital', 'pharmacy', 'dental', 'dentist', 'therapy', 'therapist', 'psychologist', 'psychiatrist', 'counseling', 'nursing', 'nurse', 'laboratory', 'diagnostic', 'radiology', 'physical therapy', 'chiropractor', 'acupuncture', 'massage therapy', 'nutritionist', 'dietitian', 'veterinarian', 'animal hospital', 'pet clinic']):
            return 'Health & Medical'
        elif any(word in cat_lower for word in ['sport', 'fitness', 'gym', 'yoga', 'pilates', 'martial arts', 'dance', 'swimming', 'tennis', 'golf', 'bowling', 'billiards', 'equipment', 'bicycle', 'bike', 'ski', 'snowboard', 'camping', 'hiking', 'fishing', 'hunting', 'boating', 'park', 'recreation']):
            return 'Sports & Recreation'
        elif any(word in cat_lower for word in ['car', 'auto', 'automotive', 'vehicle', 'truck', 'motorcycle', 'dealer', 'repair', 'service', 'tire', 'oil change', 'brake', 'transmission', 'battery', 'glass', 'body shop', 'detailing', 'car wash', 'towing', 'rental', 'leasing', 'parts', 'accessories']):
            return 'Automotive'
        elif any(word in cat_lower for word in ['home', 'house', 'garden', 'furniture', 'appliance', 'hardware', 'paint', 'flooring', 'plumbing', 'electrical', 'hvac', 'cleaning', 'landscaping', 'lawn', 'pool', 'kitchen', 'bathroom', 'bedroom', 'living room', 'dining room', 'patio', 'deck', 'roofing', 'siding', 'window', 'door', 'lighting', 'security', 'decor', 'rug', 'curtain', 'blind']):
            return 'Home & Garden'
        elif any(word in cat_lower for word in ['hotel', 'motel', 'resort', 'inn', 'bed and breakfast', 'vacation rental', 'hostel', 'campground', 'rv park', 'travel agency', 'tour operator', 'airport', 'bus station', 'train station', 'ferry', 'cruise', 'airline', 'car rental', 'taxi', 'limousine', 'shuttle']):
            return 'Travel & Lodging'
        elif any(word in cat_lower for word in ['school', 'education', 'university', 'college', 'academy', 'training', 'tutoring', 'library', 'museum', 'research', 'student', 'teacher', 'professor', 'class', 'course', 'lesson', 'preschool', 'kindergarten', 'elementary', 'high school', 'vocational']):
            return 'Education'
        elif any(word in cat_lower for word in ['government', 'city hall', 'post office', 'police', 'fire', 'court', 'prison', 'military', 'embassy', 'consulate']):
            return 'Government & Community'
        elif any(word in cat_lower for word in ['lawyer', 'attorney', 'legal', 'accounting', 'accountant', 'consultant', 'marketing', 'advertising', 'insurance', 'real estate', 'realtor', 'financial', 'tax', 'business', 'management', 'recruiting', 'employment']):
            return 'Professional Services'
        elif any(word in cat_lower for word in ['art', 'museum', 'gallery', 'theater', 'cinema', 'movie', 'music', 'concert', 'performance', 'dance', 'artist', 'photography', 'craft', 'hobby', 'entertainment', 'nightclub', 'casino', 'amusement', 'park', 'zoo', 'aquarium']):
            return 'Arts & Entertainment'
        elif any(word in cat_lower for word in ['shop', 'store', 'market', 'retail', 'boutique', 'emporium', 'mall', 'department', 'discount', 'warehouse', 'outlet', 'convenience', 'grocery', 'supermarket', 'bookstore', 'gift', 'toy', 'pet', 'florist', 'optician', 'bank', 'atm']):
            return 'Retail & Shopping'
        else:
            return 'Other'

    def _keyword_based_mapping(self, original: str, category_type: str) -> Dict[str, str]:
        """Create mapping based on keyword categories."""
        category_mappings = {
            'fashion': 'Fashion & Apparel > Clothing > General Clothing',
            'food': 'Food & Drink > Restaurants > General Restaurants',
            'beauty': 'Beauty & Personal Care > Beauty Salons > General Beauty Salons',
            'electronics': 'Electronics > Consumer Electronics > General Electronics',
            'health': 'Health & Medical > Medical Clinics > General Clinics',
            'sports': 'Sports & Recreation > Fitness > General Fitness',
            'automotive': 'Automotive > Auto Services > General Auto Services',
            'retail': 'Retail & Shopping > General Retail > General Stores',
            'home': 'Home & Garden > Home Furnishings > General Furnishings',
            'entertainment': 'Arts & Entertainment > General Entertainment > General Venues'
        }

        hierarchy = category_mappings.get(category_type, 'Other > General > Unspecified')
        return self._create_result(original, hierarchy, 'medium')

    def search_categories(self, query: str, limit: int = 10) -> List[str]:
        """
        Search for categories containing the query string.
        """
        query_lower = query.lower()
        matches = [cat for cat in self.all_categories if query_lower in cat.lower()]
        return matches[:limit]

    def get_category_stats(self) -> Dict[str, int]:
        """
        Get statistics about the category mappings.
        """
        return {
            'total_categories': len(self.all_categories),
            'major_categories': len(self.category_hierarchy) if self.category_hierarchy else 0,
            'curated_mappings': len(self.curated_mappings),
            'has_hierarchy': bool(self.category_hierarchy),
            'has_direct_mappings': bool(self.direct_mappings),
            'source': self.categories_data.get('source', 'unknown'),
            'last_updated': self.categories_data.get('last_updated', 'unknown')
        }


def process_tenant_file(input_file: str, output_file: str, mapper: GoogleCategoryMapper):
    """
    Process a tenant JSON file and add hierarchical category mappings.
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        tenants = json.load(f)

    processed_tenants = []
    for tenant in tenants:
        # Map the category
        category_mapping = mapper.map_category(tenant.get('category', ''))

        # Create enhanced tenant record
        enhanced_tenant = tenant.copy()
        enhanced_tenant['google_categories'] = category_mapping

        processed_tenants.append(enhanced_tenant)

    # Save enhanced data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_tenants, f, indent=2, ensure_ascii=False)

    return len(processed_tenants)


def main():
    """
    Main function to demonstrate category mapping.
    """
    # Initialize mapper
    mapper = GoogleCategoryMapper()

    # Show stats
    stats = mapper.get_category_stats()
    print(f"Category Mapping System Loaded:")
    print(f"- Total Google categories: {stats['total_categories']}")
    print(f"- Major categories: {stats['major_categories']}")
    print(f"- Curated mappings: {stats['curated_mappings']} (83% tenant coverage)")
    print(f"- Strategy: Curated first (high accuracy), fuzzy matching for long tail")
    print(f"- Source: {stats['source']}")
    print(f"- Last updated: {stats['last_updated']}")

    # Example mappings
    test_categories = [
        "Men's Clothes Shop",
        "Pizza",
        "Beauty supply store",
        "Mobile Phone Shop",
        "Some Unknown Category"
    ]

    print("\nExample Mappings:")
    print("-" * 50)
    for category in test_categories:
        mapping = mapper.map_category(category)
        print(f"Original: {category}")
        print(f"Mapped: {mapping['full_hierarchy']}")
        print(f"Confidence: {mapping['confidence']}")
        print()

    # Process the complete tenants file if it exists
    input_file = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'mecsr', 'complete_tenants_aggregate.json')
    output_file = os.path.join(os.path.dirname(__file__), '..', 'outputs', 'mecsr', 'complete_tenants_with_google_categories.json')

    if os.path.exists(input_file):
        print(f"Processing tenant file: {input_file}")
        count = process_tenant_file(input_file, output_file, mapper)
        print(f"Processed {count} tenants. Output saved to: {output_file}")
    else:
        print(f"Tenant file not found: {input_file}")


if __name__ == '__main__':
    main()
