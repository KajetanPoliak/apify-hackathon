"""
Extract crime statistics for Praha 1-10
Categories: Násilná, Krádeže vloupáním, Požáry výbuchy
"""
import os
import json
import pandas as pd

# Category IDs we're interested in
CATEGORIES = {
    "nasilna": 1,           # Násilná trestná činnost
    "kradeze_vloupanim": 18, # Krádeže vloupáním
    "pozary": 13            # Požáry výbuchy živelné pohromy
}

# District code to name mapping
DISTRICT_CODES = {
    500054: 1,   # Praha 1
    500089: 2,   # Praha 2
    500097: 3,   # Praha 3
    500119: 4,   # Praha 4
    500143: 5,   # Praha 5
    500178: 6,   # Praha 6
    500186: 7,   # Praha 7
    500208: 8,   # Praha 8
    500216: 9,   # Praha 9
    500224: 10,  # Praha 10
}

def get_category_types(types_df, category_id):
    """Get all type IDs that belong to a category"""
    # Find all types where:
    # - id equals category_id, OR
    # - parent_id1 equals category_id, OR
    # - parent_id2 equals category_id, OR
    # - parent_id3 equals category_id
    
    matching_types = types_df[
        (types_df['id'] == category_id) |
        (types_df['parent_id1'] == category_id) |
        (types_df['parent_id2'] == category_id) |
        (types_df['parent_id3'] == category_id)
    ]
    
    return set(matching_types['id'].tolist())


def process_district(folder_path):
    """Process crime data for a single district"""
    folder_name = os.path.basename(folder_path)
    
    # Extract district code from folder name (format: YYYY_CODE)
    parts = folder_name.split('_')
    if len(parts) == 2:
        district_code = int(parts[1])
        district_number = DISTRICT_CODES.get(district_code)
    else:
        district_code = None
        district_number = None
    
    # Load types
    types_df = pd.read_csv(f"{folder_path}/types.csv")
    
    # Load crime data
    csv_file = f"{folder_path}/{folder_name}.csv"
    crimes_df = pd.read_csv(csv_file)
    
    # Get type IDs for each category
    nasilna_types = get_category_types(types_df, CATEGORIES["nasilna"])
    kradeze_types = get_category_types(types_df, CATEGORIES["kradeze_vloupanim"])
    pozary_types = get_category_types(types_df, CATEGORIES["pozary"])
    
    # Count unique crimes in each category
    nasilna_count = crimes_df[crimes_df['types'].isin(nasilna_types)]['id'].nunique()
    kradeze_count = crimes_df[crimes_df['types'].isin(kradeze_types)]['id'].nunique()
    pozary_count = crimes_df[crimes_df['types'].isin(pozary_types)]['id'].nunique()
    
    return {
        "district": district_number,
        "nasilna": nasilna_count,
        "kradeze_vloupanim": kradeze_count,
        "pozary": pozary_count
    }


def main():
    crimes_folder = "crimes"
    results = {}
    
    # List all folders in crimes/
    folders = [f for f in os.listdir(crimes_folder) 
               if os.path.isdir(os.path.join(crimes_folder, f))]
    
    print(f"Found {len(folders)} district folders\n")
    
    for folder in sorted(folders):
        folder_path = os.path.join(crimes_folder, folder)
        
        print(f"Processing {folder}...")
        try:
            stats = process_district(folder_path)
            results[folder] = stats
            district_info = f"Praha {stats['district']}" if stats['district'] else "Unknown"
            print(f"  ✓ {district_info} - Násilná: {stats['nasilna']}, Krádeže vloupáním: {stats['kradeze_vloupanim']}, Požáry: {stats['pozary']}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    # Save to JSON
    output_file = "crime_statistics.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Results saved to {output_file}")
    
    # Also print the JSON
    print("\n" + "=" * 80)
    print("RESULTS:")
    print("=" * 80)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
