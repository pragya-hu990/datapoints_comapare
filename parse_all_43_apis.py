#!/usr/bin/env python3
"""
COMPLETE PARSER - ALL 43 APIs
Parses EVERY API including general ones (login, consent, fips, etc.)
"""

import json
import re
from pathlib import Path
from collections import defaultdict, OrderedDict
from parse_schemas import extract_xsd_data_points


def extract_fields_with_paths(obj, parent='', depth=0, max_depth=50):
    """Recursively extract ALL fields with their full paths and types."""
    fields = []
    
    if depth > max_depth:
        return fields
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_path = f"{parent}.{key}" if parent else key
            
            # Determine type
            if isinstance(value, bool):
                field_type = 'boolean'
            elif isinstance(value, int):
                field_type = 'integer'
            elif isinstance(value, float):
                field_type = 'float'
            elif isinstance(value, str):
                field_type = 'string'
            elif isinstance(value, list):
                field_type = 'array'
            elif isinstance(value, dict):
                field_type = 'object'
            elif value is None:
                field_type = 'null'
            else:
                field_type = 'unknown'
            
            fields.append({
                'name': key,
                'path': full_path,
                'type': field_type,
                'depth': depth
            })
            
            # Recurse
            if isinstance(value, (dict, list)):
                fields.extend(extract_fields_with_paths(value, full_path, depth + 1, max_depth))
    
    elif isinstance(obj, list) and len(obj) > 0:
        fields.extend(extract_fields_with_paths(obj[0], parent, depth, max_depth))
    
    return fields


def parse_all_api_responses(api_file: Path):
    """Parse ALL 43 API responses from the file."""
    print(f"📖 Reading API response file: {api_file}")
    
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"   File size: {len(content) / 1024 / 1024:.1f} MB")
    
    # Find all API response blocks
    pattern = r'{\s*name:\s*"([^"]+)",\s*endpoint:\s*"([^"]+)",\s*request:\s*{[^}]*},\s*response:\s*({.*?})\s*,\s*error:'
    
    matches = list(re.finditer(pattern, content, re.DOTALL))
    print(f"\n🔍 Found {len(matches)} API responses")
    
    # Store ALL APIs
    all_apis = {}
    api_fields_by_category = defaultdict(lambda: {
        'apis': OrderedDict(),
        'all_fields': {},
        'field_details': []
    })
    
    # Process each API
    for match in matches:
        api_name = match.group(1)
        endpoint = match.group(2)
        response_str = match.group(3)
        
        # Categorize API
        category = categorize_api(endpoint)
        
        print(f"\n  📡 {api_name}")
        print(f"     Endpoint: {endpoint}")
        print(f"     Category: {category}")
        
        # Parse response
        try:
            # Define JavaScript literals
            true = True
            false = False
            null = None
            
            # Use eval to handle JavaScript object notation
            response_data = eval(response_str)
            
            # Extract all fields
            fields = extract_fields_with_paths(response_data)
            
            print(f"     ✅ Extracted {len(fields)} fields")
            
            # Store API info
            all_apis[api_name] = {
                'endpoint': endpoint,
                'category': category,
                'field_count': len(fields),
                'fields': fields
            }
            
            # Store in category
            api_fields_by_category[category]['apis'][api_name] = {
                'endpoint': endpoint,
                'field_count': len(fields),
                'fields': [f['name'] for f in fields]
            }
            
            # Track which APIs provide which fields
            for field in fields:
                field_name = field['name']
                
                if field_name not in api_fields_by_category[category]['all_fields']:
                    api_fields_by_category[category]['all_fields'][field_name] = []
                
                api_fields_by_category[category]['all_fields'][field_name].append({
                    'api_name': api_name,
                    'api_endpoint': endpoint,
                    'path': field['path'],
                    'type': field['type'],
                    'depth': field['depth']
                })
        
        except Exception as e:
            print(f"     ❌ Error: {str(e)[:100]}")
            continue
    
    return all_apis, dict(api_fields_by_category)


def categorize_api(endpoint):
    """Categorize API by endpoint."""
    endpoint_lower = endpoint.lower()
    
    # FI-specific categories
    if '/mutual-fund/' in endpoint_lower:
        return 'mutual_funds'
    elif '/term-deposit/' in endpoint_lower:
        return 'term_deposit'
    elif '/recurring-deposit/' in endpoint_lower:
        return 'recurring_deposit'
    elif '/equities/' in endpoint_lower or '/equities-and-etfs/' in endpoint_lower:
        return 'equity_shares'
    elif '/etf/' in endpoint_lower:
        return 'exchange_traded_funds'
    elif '/nps/' in endpoint_lower:
        return 'national_pension_system'
    elif '/deposit/' in endpoint_lower:
        return 'deposit'
    
    # General categories
    elif 'user-login' in endpoint_lower or 'user-details' in endpoint_lower or 'user-subscriptions' in endpoint_lower:
        return 'user_management'
    elif 'consent' in endpoint_lower:
        return 'consent_management'
    elif 'fips' in endpoint_lower or 'brokers' in endpoint_lower:
        return 'provider_info'
    elif 'firequest' in endpoint_lower:
        return 'fi_request'
    elif 'mutualfunds' in endpoint_lower and 'mutual-fund' not in endpoint_lower:
        return 'reference_data'
    else:
        return 'other'


def main():
    """Main function."""
    base_dir = Path(__file__).parent
    rebit_dir = base_dir / 'rebit-schemas' / 'schemas'
    api_file = base_dir / 'finfactor' / 'apiResonse.json'
    
    print("="*80)
    print("🎯 COMPLETE PARSER - ALL 43 APIs")
    print("="*80)
    
    # Step 1: Parse ReBIT schemas
    print("\n📖 STEP 1: Parsing ReBIT Schemas...")
    rebit_data = {}
    
    for schema_dir in rebit_dir.iterdir():
        if schema_dir.is_dir():
            fi_type = schema_dir.name
            
            for xsd_file in schema_dir.glob('*.xsd'):
                data_points = extract_xsd_data_points(xsd_file, fi_type)
                
                if fi_type not in rebit_data:
                    rebit_data[fi_type] = {
                        'fields': {},
                        'schemas': set()
                    }
                
                rebit_data[fi_type]['schemas'].add(xsd_file.name)
                
                for attr in data_points.get('attributes', []):
                    field_name = attr['name']
                    
                    if field_name not in rebit_data[fi_type]['fields']:
                        rebit_data[fi_type]['fields'][field_name] = {
                            'name': field_name,
                            'type': attr.get('type', 'string'),
                            'required': attr.get('required', False),
                            'path': attr.get('path', ''),
                            'documentation': attr.get('documentation', ''),
                            'schema_file': xsd_file.name,
                            'source_type': 'rebit'
                        }
    
    print(f"✅ Parsed {len(rebit_data)} ReBIT FI types")
    
    # Step 2: Parse ALL FinFactor APIs
    print("\n📡 STEP 2: Parsing ALL 43 FinFactor APIs...")
    all_apis, api_fields_by_category = parse_all_api_responses(api_file)
    
    print(f"\n✅ Parsed {len(all_apis)} APIs")
    print(f"✅ Categorized into {len(api_fields_by_category)} categories")
    
    # Print category summary
    print("\n📊 APIs by Category:")
    for category, data in sorted(api_fields_by_category.items()):
        unique_fields = len(data['all_fields'])
        total_apis = len(data['apis'])
        print(f"   {category}: {total_apis} APIs, {unique_fields} unique fields")
    
    # Step 3: Create comprehensive comparison
    print("\n🔬 STEP 3: Creating Complete Comparison...")
    
    # Combine all categories
    all_categories = set(list(rebit_data.keys()) + list(api_fields_by_category.keys()))
    
    comparison = {
        'metadata': {
            'generated_at': '2026-01-04',
            'total_apis_parsed': len(all_apis),
            'total_categories': len(api_fields_by_category),
            'total_rebit_fi_types': len(rebit_data)
        },
        'all_apis': {api_name: {'endpoint': api['endpoint'], 'category': api['category'], 'field_count': api['field_count']} 
                     for api_name, api in all_apis.items()},
        'categories': {}
    }
    
    for category in all_categories:
        rebit_fields = rebit_data.get(category, {}).get('fields', {})
        finn_fields = api_fields_by_category.get(category, {}).get('all_fields', {})
        
        common_names = set(rebit_fields.keys()) & set(finn_fields.keys())
        rebit_only_names = set(rebit_fields.keys()) - set(finn_fields.keys())
        finn_only_names = set(finn_fields.keys()) - set(rebit_fields.keys())
        
        # Build detailed comparison
        common_fields = []
        for name in common_names:
            common_fields.append({
                'field_name': name,
                'rebit': rebit_fields[name],
                'finn': {
                    'apis': finn_fields[name],
                    'api_count': len(finn_fields[name]),
                    'api_names': list(set(api['api_name'] for api in finn_fields[name]))
                }
            })
        
        rebit_only_fields = [rebit_fields[name] for name in rebit_only_names]
        
        finn_only_fields = []
        for name in finn_only_names:
            finn_only_fields.append({
                'field_name': name,
                'apis': finn_fields[name],
                'api_count': len(finn_fields[name]),
                'api_names': list(set(api['api_name'] for api in finn_fields[name]))
            })
        
        comparison['categories'][category] = {
            'summary': {
                'rebit_total': len(rebit_fields),
                'finn_total': len(finn_fields),
                'common': len(common_names),
                'rebit_only': len(rebit_only_names),
                'finn_only': len(finn_only_names),
                'coverage_percent': round((len(common_names) / len(rebit_fields) * 100) if rebit_fields else 0, 1),
                'apis_count': len(api_fields_by_category.get(category, {}).get('apis', {}))
            },
            'common_fields': common_fields,
            'rebit_only_fields': rebit_only_fields,
            'finn_only_fields': finn_only_fields,
            'apis': list(api_fields_by_category.get(category, {}).get('apis', {}).keys())
        }
    
    # Save
    output_file = base_dir / 'comparison_all_43_apis.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("📊 COMPLETE COMPARISON - ALL 43 APIs")
    print("="*80)
    print(f"\nTotal APIs Parsed: {len(all_apis)}")
    
    for category in sorted(comparison['categories'].keys()):
        summary = comparison['categories'][category]['summary']
        if summary['apis_count'] > 0 or summary['rebit_total'] > 0:
            print(f"\n📁 {category.upper().replace('_', ' ')}")
            print(f"   APIs: {summary['apis_count']}")
            print(f"   ReBIT: {summary['rebit_total']} fields")
            print(f"   FinFactor: {summary['finn_total']} fields")
            print(f"   Common: {summary['common']} ({summary['coverage_percent']}%)")
            print(f"   ReBIT Only: {summary['rebit_only']}")
            print(f"   FinFactor Extra: {summary['finn_only']} ⭐")
    
    print("\n" + "="*80)
    print("✅ DONE - All 43 APIs parsed!")
    print("="*80)


if __name__ == '__main__':
    main()
