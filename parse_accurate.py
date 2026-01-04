#!/usr/bin/env python3
"""
Simple and accurate parser for the JavaScript API response file.
Extracts ALL fields from real API responses.
"""

import json
import re
from pathlib import Path
from collections import defaultdict, OrderedDict
from parse_schemas import extract_xsd_data_points


def extract_fields_from_dict(data, parent_path='', fields_set=None):
    """Recursively extract all field names from a dictionary."""
    if fields_set is None:
        fields_set = set()
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{parent_path}.{key}" if parent_path else key
            fields_set.add(current_path)
            
            if isinstance(value, (dict, list)):
                extract_fields_from_dict(value, current_path, fields_set)
    
    elif isinstance(data, list) and len(data) > 0:
        # Process first item as template
        extract_fields_from_dict(data[0], parent_path, fields_set)
    
    return fields_set


def main():
    """Main function."""
    base_dir = Path(__file__).parent
    rebit_dir = base_dir / 'rebit-schemas' / 'schemas'
    api_file = base_dir / 'finfactor' / 'apiResonse.json'
    
    print("="*80)
    print("🎯 ACCURATE PARSER - Real API Responses")
    print("="*80)
    
    # Step 1: Parse ReBIT schemas
    print("\\n📖 Step 1: Parsing ReBIT schemas...")
    rebit_data = {}
    
    for schema_dir in rebit_dir.iterdir():
        if schema_dir.is_dir():
            fi_type = schema_dir.name
            for xsd_file in schema_dir.glob('*.xsd'):
                data_points = extract_xsd_data_points(xsd_file, fi_type)
                
                if fi_type not in rebit_data:
                    rebit_data[fi_type] = set()
                
                for attr in data_points.get('attributes', []):
                    rebit_data[fi_type].add(attr['name'])
    
    print(f"✅ Parsed {len(rebit_data)} ReBIT FI types")
    for fi_type, fields in sorted(rebit_data.items()):
        print(f"  - {fi_type}: {len(fields)} unique fields")
    
    # Step 2: Parse FinFactor API responses
    print("\\n📡 Step 2: Parsing FinFactor API responses...")
    print(f"Reading file: {api_file}")
    
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract API responses using regex
    # Pattern: find response objects
    finn_data = defaultdict(set)
    
    # Define FI-specific endpoints
    fi_endpoints = {
        'mutual_funds': ['/mutual-fund/'],
        'term_deposit': ['/term-deposit/'],
        'recurring_deposit': ['/recurring-deposit/'],
        'deposit': ['/deposit/'],
        'equity_shares': ['/equities/', '/equities-and-etfs/'],
        'exchange_traded_funds': ['/etf/'],
        'national_pension_system': ['/nps/']
    }
    
    # Find all API blocks
    api_blocks = re.findall(
        r'{\\s*name:\\s*"([^"]+)".*?endpoint:\\s*"([^"]+)".*?response:\\s*({.*?})\\s*,\\s*error:',
        content,
        re.DOTALL
    )
    
    print(f"\\nFound {len(api_blocks)} API responses")
    
    for api_name, endpoint, response_str in api_blocks:
        # Determine FI type
        fi_type = None
        for ft, patterns in fi_endpoints.items():
            if any(pattern in endpoint.lower() for pattern in patterns):
                # Make sure it's not a more specific type
                if ft == 'deposit' and ('/term-deposit/' in endpoint.lower() or '/recurring-deposit/' in endpoint.lower()):
                    continue
                fi_type = ft
                break
        
        if not fi_type:
            continue
        
        print(f"  Processing: {api_name} -> {fi_type}")
        
        # Try to convert JavaScript object to JSON
        try:
            # Simple approach: use eval (safe here since we control the file)
            response_data = eval(response_str)
            
            # Extract all fields
            fields = extract_fields_from_dict(response_data)
            finn_data[fi_type].update(fields)
            
            print(f"    ✅ Extracted {len(fields)} fields")
        
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    print(f"\\n✅ Extracted data from {len(finn_data)} FinFactor FI types")
    for fi_type, fields in sorted(finn_data.items()):
        print(f"  - {fi_type}: {len(fields)} unique fields")
    
    # Step 3: Create comparison
    print("\\n🔬 Step 3: Creating comparison...")
    
    all_fi_types = set(list(rebit_data.keys()) + list(finn_data.keys()))
    
    comparison = {}
    for fi_type in all_fi_types:
        rebit_fields = rebit_data.get(fi_type, set())
        finn_fields = finn_data.get(fi_type, set())
        
        common = rebit_fields & finn_fields
        rebit_only = rebit_fields - finn_fields
        finn_only = finn_fields - rebit_fields
        
        comparison[fi_type] = {
            'rebit_total': len(rebit_fields),
            'finn_total': len(finn_fields),
            'common': len(common),
            'rebit_only': len(rebit_only),
            'finn_only': len(finn_only),
            'coverage_percent': round((len(common) / len(rebit_fields) * 100) if rebit_fields else 0, 1),
            'common_fields': sorted(list(common)),
            'rebit_only_fields': sorted(list(rebit_only)),
            'finn_only_fields': sorted(list(finn_only))
        }
    
    # Save comparison
    output_file = base_dir / 'comparison_accurate.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    print(f"\\n✅ Saved to: {output_file}")
    
    # Print summary
    print("\\n" + "="*80)
    print("📊 ACCURATE COMPARISON SUMMARY")
    print("="*80)
    
    for fi_type in sorted(comparison.keys()):
        summary = comparison[fi_type]
        if summary['rebit_total'] > 0 or summary['finn_total'] > 0:
            print(f"\\n📁 {fi_type.upper().replace('_', ' ')}")
            print(f"  ├─ ReBIT: {summary['rebit_total']} fields")
            print(f"  ├─ FinFactor: {summary['finn_total']} fields")
            print(f"  ├─ Common: {summary['common']} ({summary['coverage_percent']}%)")
            print(f"  ├─ ReBIT Only: {summary['rebit_only']}")
            print(f"  └─ FinFactor Extra: {summary['finn_only']} ⭐")
    
    print("\\n" + "="*80)


if __name__ == '__main__':
    main()
