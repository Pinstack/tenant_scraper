#!/usr/bin/env python3
"""
Create a hierarchical organization of the complete Google Business Profile categories.
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Set

def load_categories() -> List[str]:
    """Load the complete categories list."""
    file_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'google_business_categories_complete.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['categories']

def create_hierarchical_categories(categories: List[str]) -> Dict:
    """
    Create a comprehensive hierarchical organization of categories.
    """
    def nested_dict():
        return defaultdict(nested_dict)

    hierarchy = nested_dict()

    # Define major category groupings based on keywords
    category_groups = {
        'Food & Drink': {
            'keywords': ['restaurant', 'cafe', 'bar', 'pub', 'diner', 'eatery', 'bakery', 'food', 'dining', 'pizza', 'burger', 'sandwich', 'sushi', 'taco', 'burrito', 'pasta', 'noodle', 'rice', 'meat', 'fish', 'seafood', 'chicken', 'steak', 'breakfast', 'lunch', 'dinner', 'brunch', 'buffet', 'catering', 'food truck', 'food court', 'ice cream', 'frozen yogurt', 'coffee', 'tea', 'juice', 'smoothie', 'beverage', 'wine', 'beer', 'liquor', 'cocktail', 'bartender'],
            'subcategories': {
                'Restaurants': ['restaurant', 'diner', 'eatery'],
                'Fast Food': ['fast food', 'burger', 'pizza', 'taco', 'sandwich', 'chicken', 'fried chicken'],
                'Cafes & Coffee': ['cafe', 'coffee', 'tea', 'bakery', 'donut', 'bagel', 'pastry'],
                'Bars & Nightlife': ['bar', 'pub', 'cocktail', 'beer', 'wine', 'liquor', 'nightclub', 'lounge'],
                'Specialty Foods': ['sushi', 'seafood', 'steak', 'italian', 'chinese', 'japanese', 'mexican', 'thai', 'indian', 'mediterranean', 'french', 'german', 'greek', 'turkish', 'lebanese', 'persian', 'vietnamese', 'korean', 'brazilian', 'peruvian', 'cuban', 'caribbean', 'african', 'middle eastern', 'vegetarian', 'vegan', 'kosher', 'halal', 'organic', 'farm-to-table'],
                'Desserts & Sweets': ['ice cream', 'frozen yogurt', 'bakery', 'cake', 'cupcake', 'pie', 'candy', 'chocolate', 'dessert'],
                'Beverages': ['juice', 'smoothie', 'coffee', 'tea', 'beverage'],
                'Food Services': ['catering', 'food truck', 'food court', 'delivery', 'meal delivery']
            }
        },
        'Fashion & Apparel': {
            'keywords': ['clothing', 'fashion', 'apparel', 'clothes', 'wear', 'boutique', 'designer', 'dress', 'shirt', 'pants', 'jeans', 'jacket', 'coat', 'suit', 'tie', 'shoe', 'boot', 'sandal', 'hat', 'bag', 'purse', 'handbag', 'jewelry', 'watch', 'accessory', 'lingerie', 'swimwear', 'uniform', 'costume', 'vintage', 'thrift', 'consignment'],
            'subcategories': {
                'Clothing Stores': ['clothing', 'clothes', 'apparel', 'boutique', 'designer'],
                "Men's Clothing": ['men', "men's", 'male'],
                "Women's Clothing": ['women', "women's", 'ladies', 'female'],
                "Children's Clothing": ['children', 'kids', 'baby', 'toddler', 'infant'],
                'Shoes': ['shoe', 'boot', 'sandal', 'footwear'],
                'Accessories': ['accessory', 'jewelry', 'watch', 'bag', 'handbag', 'hat', 'scarf', 'belt', 'glove'],
                'Specialty': ['lingerie', 'swimwear', 'uniform', 'costume', 'bridal', 'maternity', 'plus size', 'petite', 'tall']
            }
        },
        'Beauty & Personal Care': {
            'keywords': ['beauty', 'salon', 'spa', 'cosmetic', 'hair', 'nail', 'makeup', 'skincare', 'facial', 'massage', 'tattoo', 'piercing', 'barber', 'esthetician', 'waxing', 'threading', 'eyebrow', 'eyelash', 'permanent makeup', 'laser', 'microblading', 'chemical peel', 'dermabrasion', 'botox', 'filler', 'teeth whitening', 'dental', 'manicure', 'pedicure', 'hair removal'],
            'subcategories': {
                'Beauty Salons': ['salon', 'beauty', 'cosmetic'],
                'Hair Services': ['hair', 'barber', 'stylist'],
                'Nail Services': ['nail', 'manicure', 'pedicure'],
                'Skin Care': ['skincare', 'facial', 'spa', 'massage'],
                'Makeup & Cosmetics': ['makeup', 'cosmetic'],
                'Body Art': ['tattoo', 'piercing'],
                'Specialty Treatments': ['laser', 'microblading', 'chemical peel', 'botox', 'filler']
            }
        },
        'Health & Medical': {
            'keywords': ['health', 'medical', 'clinic', 'doctor', 'hospital', 'pharmacy', 'dental', 'dentist', 'therapy', 'therapist', 'psychologist', 'psychiatrist', 'counseling', 'nursing', 'nurse', 'laboratory', 'diagnostic', 'radiology', 'physical therapy', 'chiropractor', 'acupuncture', 'massage therapy', 'nutritionist', 'dietitian', 'veterinarian', 'animal hospital', 'pet clinic'],
            'subcategories': {
                'Healthcare Facilities': ['hospital', 'clinic', 'medical center'],
                'Doctors & Physicians': ['doctor', 'physician', 'surgeon'],
                'Dental Care': ['dental', 'dentist', 'orthodontist', 'oral surgeon'],
                'Mental Health': ['psychologist', 'psychiatrist', 'counseling', 'therapy'],
                'Specialty Medicine': ['cardiology', 'dermatology', 'oncology', 'pediatrics', 'obstetrics', 'gynecology', 'ophthalmology', 'orthopedics', 'neurology', 'urology'],
                'Therapies': ['physical therapy', 'occupational therapy', 'speech therapy', 'chiropractor', 'acupuncture', 'massage therapy'],
                'Pharmacies & Labs': ['pharmacy', 'laboratory', 'diagnostic'],
                'Animal Care': ['veterinarian', 'animal hospital', 'pet clinic']
            }
        },
        'Electronics & Technology': {
            'keywords': ['electronics', 'phone', 'computer', 'laptop', 'tablet', 'tv', 'television', 'audio', 'speaker', 'headphone', 'camera', 'drone', 'gaming', 'software', 'repair', 'mobile', 'cell', 'smartphone', 'smartwatch', 'wearable', 'printer', 'scanner', 'network', 'internet', 'wifi', 'cable'],
            'subcategories': {
                'Mobile Phones': ['phone', 'mobile', 'cell', 'smartphone'],
                'Computers': ['computer', 'laptop', 'desktop'],
                'Tablets & Wearables': ['tablet', 'smartwatch', 'wearable'],
                'Audio & Video': ['audio', 'speaker', 'headphone', 'tv', 'television', 'camera'],
                'Gaming': ['gaming', 'console', 'video game'],
                'Electronics Stores': ['electronics', 'consumer electronics'],
                'Repair Services': ['repair', 'service']
            }
        },
        'Home & Garden': {
            'keywords': ['home', 'house', 'garden', 'furniture', 'appliance', 'hardware', 'paint', 'flooring', 'plumbing', 'electrical', 'hvac', 'cleaning', 'landscaping', 'lawn', 'pool', 'kitchen', 'bathroom', 'bedroom', 'living room', 'dining room', 'patio', 'deck', 'roofing', 'siding', 'window', 'door', 'lighting', 'security'],
            'subcategories': {
                'Furniture': ['furniture', 'bedroom', 'living room', 'dining room'],
                'Appliances': ['appliance', 'kitchen', 'laundry'],
                'Home Improvement': ['hardware', 'paint', 'flooring', 'plumbing', 'electrical'],
                'Garden & Outdoor': ['garden', 'landscaping', 'lawn', 'pool', 'patio'],
                'Home Services': ['cleaning', 'roofing', 'window', 'door', 'hvac'],
                'Home Decor': ['decor', 'lighting', 'rugs', 'curtains']
            }
        },
        'Automotive': {
            'keywords': ['car', 'auto', 'automotive', 'vehicle', 'truck', 'motorcycle', 'dealer', 'repair', 'service', 'tire', 'oil change', 'brake', 'transmission', 'battery', 'glass', 'body shop', 'detailing', 'car wash', 'towing', 'rental', 'leasing', 'parts', 'accessories'],
            'subcategories': {
                'Car Dealers': ['dealer', 'sales'],
                'Auto Repair': ['repair', 'service', 'mechanic'],
                'Auto Parts': ['parts', 'accessories'],
                'Specialty Services': ['tire', 'oil change', 'brake', 'transmission', 'battery', 'glass', 'detailing'],
                'Body & Paint': ['body shop', 'collision'],
                'Car Wash & Detailing': ['car wash', 'detailing'],
                'Towing & Recovery': ['towing', 'roadside'],
                'Rental & Leasing': ['rental', 'leasing']
            }
        },
        'Sports & Recreation': {
            'keywords': ['sports', 'fitness', 'gym', 'yoga', 'pilates', 'martial arts', 'dance', 'swimming', 'tennis', 'golf', 'bowling', 'billiards', 'equipment', 'bicycle', 'bike', 'ski', 'snowboard', 'camping', 'hiking', 'fishing', 'hunting', 'boating', 'park', 'recreation'],
            'subcategories': {
                'Fitness Centers': ['gym', 'fitness', 'yoga', 'pilates'],
                'Sports Instruction': ['martial arts', 'dance', 'swimming', 'tennis', 'golf'],
                'Sports Equipment': ['equipment', 'bicycle', 'ski', 'snowboard'],
                'Outdoor Activities': ['camping', 'hiking', 'fishing', 'hunting', 'boating'],
                'Venues & Facilities': ['park', 'recreation', 'bowling', 'billiards']
            }
        },
        'Retail & Shopping': {
            'keywords': ['shop', 'store', 'market', 'retail', 'boutique', 'emporium', 'mall', 'department', 'discount', 'warehouse', 'outlet', 'convenience', 'grocery', 'supermarket', 'pharmacy', 'drugstore', 'bookstore', 'gift', 'toy', 'pet', 'florist', 'jewelry', 'optician', 'bank', 'atm'],
            'subcategories': {
                'General Retail': ['shop', 'store', 'retail', 'boutique'],
                'Grocery & Food': ['grocery', 'supermarket', 'market'],
                'Specialty Stores': ['bookstore', 'gift', 'toy', 'pet', 'florist', 'jewelry'],
                'Department & Discount': ['department', 'discount', 'warehouse', 'outlet'],
                'Services': ['bank', 'atm', 'pharmacy', 'optician']
            }
        },
        'Professional Services': {
            'keywords': ['lawyer', 'attorney', 'legal', 'accounting', 'accountant', 'consultant', 'marketing', 'advertising', 'insurance', 'real estate', 'realtor', 'financial', 'tax', 'business', 'management', 'recruiting', 'employment', 'secretary', 'paralegal', 'notary', 'translator', 'printing', 'photography', 'videography'],
            'subcategories': {
                'Legal Services': ['lawyer', 'attorney', 'legal', 'paralegal', 'notary'],
                'Financial Services': ['accounting', 'financial', 'tax', 'insurance'],
                'Business Services': ['consultant', 'business', 'management', 'marketing'],
                'Real Estate': ['real estate', 'realtor'],
                'Professional Services': ['recruiting', 'translator', 'printing', 'photography']
            }
        },
        'Arts & Entertainment': {
            'keywords': ['art', 'museum', 'gallery', 'theater', 'cinema', 'movie', 'music', 'concert', 'performance', 'dance', 'artist', 'photography', 'craft', 'hobby', 'entertainment', 'nightclub', 'casino', 'amusement', 'park', 'zoo', 'aquarium'],
            'subcategories': {
                'Arts & Culture': ['art', 'museum', 'gallery', 'theater'],
                'Entertainment': ['cinema', 'movie', 'music', 'concert', 'performance'],
                'Nightlife': ['nightclub', 'bar', 'casino'],
                'Recreation': ['amusement park', 'zoo', 'aquarium']
            }
        },
        'Education': {
            'keywords': ['school', 'education', 'university', 'college', 'academy', 'training', 'tutoring', 'library', 'museum', 'research', 'student', 'teacher', 'professor', 'class', 'course', 'lesson', 'preschool', 'kindergarten', 'elementary', 'high school', 'vocational'],
            'subcategories': {
                'Schools': ['school', 'academy', 'preschool', 'elementary', 'high school'],
                'Higher Education': ['university', 'college', 'vocational'],
                'Educational Services': ['tutoring', 'training', 'library']
            }
        },
        'Travel & Lodging': {
            'keywords': ['hotel', 'motel', 'resort', 'inn', 'bed and breakfast', 'vacation rental', 'hostel', 'campground', 'rv park', 'travel agency', 'tour operator', 'airport', 'bus station', 'train station', 'ferry', 'cruise', 'airline', 'car rental', 'taxi', 'limousine', 'shuttle'],
            'subcategories': {
                'Hotels & Accommodations': ['hotel', 'motel', 'resort', 'inn', 'bed and breakfast'],
                'Alternative Lodging': ['vacation rental', 'hostel', 'campground', 'rv park'],
                'Travel Services': ['travel agency', 'tour operator', 'car rental'],
                'Transportation': ['airport', 'bus station', 'train station', 'taxi', 'limousine']
            }
        },
        'Government & Community': {
            'keywords': ['government', 'city hall', 'post office', 'police', 'fire', 'library', 'park', 'community center', 'senior center', 'church', 'temple', 'mosque', 'synagogue', 'religious', 'nonprofit', 'charity', 'social service', 'embassy', 'consulate', 'court', 'prison', 'military'],
            'subcategories': {
                'Government': ['government', 'city hall', 'post office', 'police', 'fire', 'court'],
                'Community Services': ['library', 'park', 'community center', 'senior center'],
                'Religious': ['church', 'temple', 'mosque', 'synagogue', 'religious'],
                'Non-Profit': ['nonprofit', 'charity', 'social service']
            }
        }
    }

    # Assign each category to the best matching group
    for category in categories:
        category_lower = category.lower()
        assigned = False

        for major_category, category_info in category_groups.items():
            # Check if any keyword matches
            if any(keyword in category_lower for keyword in category_info['keywords']):
                # Find best subcategory match
                best_subcategory = 'General'
                for subcategory, sub_keywords in category_info['subcategories'].items():
                    if any(sub_keyword in category_lower for sub_keyword in sub_keywords):
                        best_subcategory = subcategory
                        break

                hierarchy[major_category]['children'][best_subcategory]['children'][category] = category
                assigned = True
                break

        if not assigned:
            # Default to "Other" category
            first_word = category.split()[0]
            hierarchy['Other']['children']['General']['children'][category] = category

    return dict(hierarchy)

def save_hierarchical_categories(hierarchy: Dict, output_file: str):
    """Save the hierarchical categories to JSON."""
    output_data = {
        'version': '1.0',
        'source': 'Google Business Profile Categories - Organized Hierarchically',
        'extraction_date': '2025-01-01',
        'total_categories': sum(len(sub_data.get('children', {})) for major_data in hierarchy.values()
                              for sub_data in major_data.get('children', {}).values()),
        'hierarchy': hierarchy,
        'note': 'Complete Google Business Profile categories organized into a hierarchical taxonomy for better mapping and navigation.'
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Saved hierarchical categories to: {output_file}")
    print(f"Total major categories: {len(hierarchy)}")
    print(f"Total categories organized: {output_data['total_categories']}")

def main():
    """Main function to create hierarchical categories."""
    print("Loading complete Google Business Profile categories...")

    # Load categories
    categories = load_categories()
    print(f"Loaded {len(categories)} categories")

    # Create hierarchical organization
    print("Creating hierarchical organization...")
    hierarchy = create_hierarchical_categories(categories)

    # Save to file
    output_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'google_business_categories_hierarchical.json')
    save_hierarchical_categories(hierarchy, output_file)

    # Show sample of the hierarchy
    print("\nSample of hierarchical organization:")
    count = 0
    for major_cat, major_data in hierarchy.items():
        if count >= 5:  # Show first 5 major categories
            break
        print(f"\n{major_cat}:")
        for sub_cat in list(major_data.get('children', {}).keys())[:3]:  # Show first 3 subcategories
            sub_data = major_data['children'][sub_cat]
            category_count = len(sub_data.get('children', {}))
            print(f"  - {sub_cat}: {category_count} categories")
        count += 1

if __name__ == '__main__':
    main()
