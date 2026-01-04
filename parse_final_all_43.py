#!/usr/bin/env python3
"""
FINAL COMPLETE PARSER - ALL 43 APIs INCLUDING NULL RESPONSES
Handles all response formats: objects, null, arrays, etc.
"""

import json
import re
from pathlib import Path
from collections import defaultdict, OrderedDict
from parse_schemas import extract_xsd_data_points


def extract_all_fields_recursive(obj, parent='', depth=0, max_depth=100):
    """Ultra-deep recursive extraction."""
    fields = []
    
    if depth > max_depth or obj is None:
        return fields
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_path = f"{parent}.{key}" if parent else key
            
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
            
            if isinstance(value, dict):
                fields.extend(extract_all_fields_recursive(value, full_path, depth + 1, max_depth))
            elif isinstance(value, list) and len(value) > 0:
                for i, item in enumerate(value[:3]):
                    if isinstance(item, (dict, list)):
                        fields.extend(extract_all_fields_recursive(item, full_path, depth + 1, max_depth))
    
    elif isinstance(obj, list) and len(obj) > 0:
        for i, item in enumerate(obj[:3]):
            if isinstance(item, (dict, list)):
                fields.extend(extract_all_fields_recursive(item, parent, depth, max_depth))
    
    return fields


def parse_all_apis_flexible(content):
    """
    Flexible parser that handles ALL response formats.
    Pattern matches: name, endpoint, request (optional), response (any format)
    """
    # More flexible pattern - response can be anything before error:
    pattern = r'{\\s*name:\\s*"([^"]+)",\\s*endpoint:\\s*"([^"]+)"[^}]*?response:\\s*([^,]*(?:{[^}]*}|null|\\[[^\\]]*\\])?[^,]*),\\s*error:'
    
    matches = []
    
    # Find all API blocks more carefully
    api_blocks = re.finditer(r'{\\s*name:\\s*"([^"]+)"', content)
    
    for match in api_blocks:
        api_name = match.group(1)
        start_pos = match.start()
        
        # Find endpoint
        endpoint_match = re.search(r'endpoint:\\s*"([^"]+)"', content[start_pos:start_pos+500])
        if not endpoint_match:
            continue
        
        endpoint = endpoint_match.group(1)
        
        # Find response - look for 'response:' and capture until 'error:'
        response_match = re.search(r'response:\\s*(.+?)\\s*,\\s*error:', content[start_pos:start_pos+50000], re.DOTALL)
        if response_match:
            response_str = response_match.group(1).strip()
            matches.append({
                'name': api_name,
                'endpoint': endpoint,
                'response': response_str
            })
    
    return matches


def categorize_api(endpoint):
    """Categorize API by endpoint."""
    endpoint_lower = endpoint.lower()
    
    if '/mutual-fund/' in endpoint_lower or '/mutualfunds' in endpoint_lower:
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
    elif 'user-login' in endpoint_lower or 'user-details' in endpoint_lower or 'user-subscriptions' in endpoint_lower or 'user-account-delink' in endpoint_lower:
        return 'user_management'
    elif 'consent' in endpoint_lower:
        return 'consent_management'
    elif 'fips' in endpoint_lower or 'brokers' in endpoint_lower:
        return 'provider_info'
    elif 'firequest' in endpoint_lower or 'account-consents' in endpoint_lower:
        return 'fi_request'
    else:
        return 'other'


def main():
    """Main function."""
    base_dir = Path(__file__).parent
    rebit_dir = base_dir / 'rebit-schemas' / 'schemas'
    api_file = base_dir / 'finfactor' / 'apiResonse.json'
    
    print("="*80)
    print("🎯 FINAL COMPLETE PARSER - ALL 43 APIs")
    print("="*80)
    
    # Step 1: Parse ReBIT
    print("\\n📖 STEP 1: Parsing ReBIT Schemas...")
    rebit_data = {}
    
    for schema_dir in rebit_dir.iterdir():
        if schema_dir.is_dir():
            fi_type = schema_dir.name
            for xsd_file in schema_dir.glob('*.xsd'):
                data_points = extract_xsd_data_points(xsd_file, fi_type)
                if fi_type not in rebit_data:
                    rebit_data[fi_type] = {'fields': {}, 'schemas': set()}
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
    print("\\n📡 STEP 2: Parsing ALL 43 FinFactor APIs...")
    
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    apis = parse_all_apis_flexible(content)
    
    print(f"\\n🔍 Found {len(apis)} API responses")
    
    all_apis = {}
    api_fields_by_category = defaultdict(lambda: {
        'apis': OrderedDict(),
        'all_fields': {},
        'field_details': []
    })
    
    for api_info in apis:
        api_name = api_info['name']
        endpoint = api_info['endpoint']
        response_str = api_info['response']
        
        category = categorize_api(endpoint)
        
        print(f"\\n  📡 {api_name}")
        print(f"     Endpoint: {endpoint}")
        print(f"     Category: {category}")
        
        try:
            # Handle null responses
            if response_str.strip() == 'null':
                print(f"     ⚠️  Response is null - no fields to extract")
                all_apis[api_name] = {
                    'endpoint': endpoint,
                    'category': category,
                    'field_count': 0,
                    'fields': []
                }
                api_fields_by_category[category]['apis'][api_name] = {
                    'endpoint': endpoint,
                    'field_count': 0,
                    'fields': []
                }
                continue
            
            # Define JavaScript literals
            true = True
            false = False
            null = None
            
            # Use eval
            response_data = eval(response_str)
            
            # Extract fields
            fields = extract_all_fields_recursive(response_data)
            
            # Deduplicate
            unique_fields = {}
            for field in fields:
                if field['name'] not in unique_fields:
                    unique_fields[field['name']] = field
            
            fields = list(unique_fields.values())
            
            print(f"     ✅ Extracted {len(fields)} unique fields")
            
            all_apis[api_name] = {
                'endpoint': endpoint,
                'category': category,
                'field_count': len(fields),
                'fields': fields
            }
            
            api_fields_by_category[category]['apis'][api_name] = {
                'endpoint': endpoint,
                'field_count': len(fields),
                'fields': [f['name'] for f in fields]
            }
            
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
            print(f"     ❌ Error: {str(e)[:200]}")
            continue
    
    print(f"\\n✅ Successfully parsed {len(all_apis)} / 43 APIs")
    
    # Create comparison (same as before)
    all_categories = set(list(rebit_data.keys()) + list(api_fields_by_category.keys()))
    
    comparison = {
        'metadata': {
            'generated_at': '2026-01-04',
            'total_apis_parsed': len(all_apis),
            'total_categories': len(api_fields_by_category),
            'total_rebit_fi_types': len(rebit_data)
        },
        'all_apis': {api_name: {
            'endpoint': api['endpoint'], 
            'category': api['category'], 
            'field_count': api['field_count']
        } for api_name, api in all_apis.items()},
        'categories': {}
    }
    
    for category in all_categories:
        rebit_fields = rebit_data.get(category, {}).get('fields', {})
        finn_fields = api_fields_by_category.get(category, {}).get('all_fields', {})
        
        common_names = set(rebit_fields.keys()) & set(finn_fields.keys())
        rebit_only_names = set(rebit_fields.keys()) - set(finn_fields.keys())
        finn_only_names = set(finn_fields.keys()) - set(rebit_fields.keys())
        
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
    output_file = base_dir / 'comparison_final_all_43.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    print(f"\\n✅ Saved to: {output_file}")
    
    # Summary
    print("\\n" + "="*80)
    print("📊 FINAL SUMMARY - ALL 43 APIs")
    print("="*80)
    print(f"\\n✅ Total APIs Parsed: {len(all_apis)} / 43")
    
    total_finn_fields = sum(len(data['all_fields']) for data in api_fields_by_category.values())
    print(f"✅ Total FinFactor Fields: {total_finn_fields}")
    
    for category in sorted(comparison['categories'].keys()):
        summary = comparison['categories'][category]['summary']
        if summary['apis_count'] > 0 or summary['rebit_total'] > 0:
            print(f"\\n📁 {category.upper().replace('_', ' ')}")
            print(f"   APIs: {summary['apis_count']}")
            if summary['rebit_total'] > 0:
                print(f"   ReBIT: {summary['rebit_total']} | FinFactor: {summary['finn_total']} | Common: {summary['common']} ({summary['coverage_percent']}%)")
            else:
                print(f"   FinFactor: {summary['finn_total']} fields")
    
    print("\\n" + "="*80)


if __name__ == '__main__':
    main()
