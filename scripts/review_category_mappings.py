#!/usr/bin/env python3
"""
Review and correct curated category mappings.
"""
import json
import sys
from pathlib import Path

def load_google_categories():
    """Load all available Google categories."""
    script_dir = Path(__file__).parent
    cat_file = script_dir.parent / 'data' / 'google_business_categories_complete.json'
    
    with open(cat_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get('categories', [])

def search_google_categories(query, all_categories):
    """Search for Google categories matching a query."""
    query_lower = query.lower()
    matches = []
    
    for cat in all_categories:
        cat_lower = cat.lower()
        if query_lower in cat_lower:
            # Exact substring match
            matches.append((cat, 100))
        elif all(word in cat_lower for word in query_lower.split()):
            # All words present
            matches.append((cat, 80))
    
    # Sort by score and return top 10
    matches.sort(key=lambda x: x[1], reverse=True)
    return [cat for cat, score in matches[:10]]

def review_mappings():
    """Interactive review of category mappings."""
    script_dir = Path(__file__).parent
    mapping_file = script_dir.parent / 'data' / 'curated_category_mappings.json'
    
    # Load mappings
    with open(mapping_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    mappings = data['mappings']
    all_google_cats = load_google_categories()
    
    # Find categories that need review
    needs_review = {cat: info for cat, info in mappings.items() 
                   if info.get('needs_review', False)}
    
    print(f"Found {len(needs_review)} categories needing review")
    print(f"Total tenant coverage: {sum(info['tenant_count'] for info in needs_review.values())}")
    print("\n" + "="*80 + "\n")
    
    # Auto-correct obvious ones
    corrections = {
        "Shoe Shop": "Shoe store",
        "Jewellery Store": "Jewelry store",
        "Ladies' Clothes Shop": "Women's clothing store",
        "Cosmetics shop": "Cosmetics store",
        "Men's Clothes Shop": "Men's clothing store",
        "Children's Clothes Shop": "Children's clothing store",
        "Watch shop": "Watch store",
        "Electronics Retail and Repair Shop": "Electronics store",
        "Sportswear Shop": "Sportswear store",
        "Home Furniture Shop": "Furniture store",
        "Mobile Phone Shop": "Cell phone store",
        "Toy Shop": "Toy store",
        "Homewares Shop": "Home goods store",
        "Sporting Goods Shop": "Sporting goods store",
        "Book Shop": "Book store",
        "Dress Shop": "Dress shop",
        "Leather Goods Shop": "Leather goods store",
        "Boutique": "Boutique",
        "Lingerie shop": "Lingerie store",
        "Baby Shop": "Baby store",
        "Stationery shop": "Stationery store",
        "Sunglasses shop": "Sunglasses store",
        "Handbag Shop": "Handbag shop",
        "Convenience Store": "Convenience store",
        "Outdoor Shop": "Outdoor sports store",
        "Maternity Clothes Shop": "Maternity wear store",
        "Bridal shop": "Bridal shop",
        "Swimwear Shop": "Swimwear store",
        "Pet Shop": "Pet store",
        "Fabric Shop": "Fabric store",
        "Florist": "Florist",
        "Appliances": "Appliance store",
        "Carpet shop": "Carpet store",
        "Tile Shop": "Tile store",
        "Kitchen Supply Shop": "Kitchen supply store",
        "Curtain Shop": "Window treatment store",
        "Lighting Shop": "Lighting store",
        "Bedding Shop": "Bedding store",
        "Interior Designer": "Interior designer",
        "Wallpaper Shop": "Wallpaper store",
        "Paint Shop": "Paint store",
        "Hardware Shop": "Hardware store",
        "Bicycle Shop": "Bicycle store",
        "Scooter Shop": "Scooter shop",
        "ATM": "ATM",
        "Pizza": "Pizza restaurant",
        "Hamburger": "Hamburger restaurant",
        "Chicken": "Chicken restaurant",
        "Shawarma": "Shawarma restaurant",
        "Falafel": "Falafel restaurant",
        "Kebab": "Kebab shop",
        "Ice cream": "Ice cream shop",
        "Bakery": "Bakery",
        "Sweets": "Candy store",
        "Juice": "Juice shop",
        "Tea": "Tea store",
        "Nuts": "Nut store",
        "Dates": "Gourmet grocery store",
        "Honey": "Gourmet grocery store",
        "Spices": "Spice store",
        "Fitness": "Gym",
        "Gym": "Gym",
        "Beauty Salon": "Beauty salon",
        "Hairdresser": "Hair salon",
        "Barber": "Barber shop",
        "Nail Salon": "Nail salon",
        "Spa": "Spa",
        "Massage": "Massage spa",
        "Laser Hair Removal": "Laser hair removal service",
        "Tattoo and Piercing Shop": "Tattoo shop",
        "Optician": "Optician",
        "Pharmacy": "Pharmacy",
        "Medical Centre": "Medical clinic",
        "Dental clinic": "Dentist",
        "Veterinary clinic": "Veterinarian",
        "Travel Agent": "Travel agency",
        "Money transfer service": "Money transfer service",
        "Insurance Agent": "Insurance agency",
        "Real estate agent": "Real estate agency",
        "Lawyer": "Attorney",
        "Accountant": "Accountant"
    }
    
    updated_count = 0
    for tenant_cat, google_cat in corrections.items():
        if tenant_cat in mappings:
            # Verify the Google category exists
            if google_cat in all_google_cats:
                mappings[tenant_cat]['google_category'] = google_cat
                mappings[tenant_cat]['confidence'] = 'high'
                mappings[tenant_cat]['needs_review'] = False
                updated_count += 1
                print(f"✓ {tenant_cat:40} → {google_cat}")
    
    print(f"\nAuto-corrected {updated_count} mappings")
    
    # Save updated mappings
    data['mappings'] = mappings
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nUpdated mappings saved to {mapping_file}")
    
    # Show remaining issues
    still_needs_review = {cat: info for cat, info in mappings.items() 
                         if info.get('needs_review', False)}
    print(f"\nRemaining categories needing review: {len(still_needs_review)}")
    
    if still_needs_review:
        print("\nTop 10 by tenant count:")
        sorted_review = sorted(still_needs_review.items(), 
                             key=lambda x: x[1]['tenant_count'], 
                             reverse=True)
        for cat, info in sorted_review[:10]:
            print(f"  {cat:40} ({info['tenant_count']:5} tenants) → {info['google_category']}")

if __name__ == '__main__':
    review_mappings()


