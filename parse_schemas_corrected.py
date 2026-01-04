#!/usr/bin/env python3
"""
CORRECTED parser - Only includes FI-specific APIs, not general APIs.
This ensures accurate comparison without inflated numbers.
"""

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict
import re

# Import existing functions
from parse_schemas import extract_xsd_data_points

def parse_postman_collection_strict(postman_file: Path) -> Dict[str, Any]:
    """Parse Postman collection - STRICT MODE: Only FI-specific APIs."""
    with open(postman_file, 'r', encoding='utf-8') as f:
        collection = json.load(f)
    
    finn_factor_apis = {}
    
    def extract_from_item(item: Dict, path: str = ''):
        if 'item' in item:
            for sub_item in item['item']:
                new_path = f"{path}/{item.get('name', '')}" if path else item.get('name', '')
                extract_from_item(sub_item, new_path)
        else:
            if 'request' in item and 'response' in item:
                endpoint_name = item.get('name', '')
                request = item.get('request', {})
                url = request.get('url', {})
                
                if isinstance(url, dict):
                    raw_url = url.get('raw', '')
                    path_parts = url.get('path', [])
                else:
                    raw_url = str(url)
                    path_parts = []
                
                # STRICT FI type determination - only from URL path
                fi_type = None
                path_str = '/'.join(path_parts) if path_parts else raw_url.lower()
                
                # Map ONLY if the API path explicitly contains the FI type
                if '/mutual-fund/' in path_str:
                    fi_type = 'mutual_funds'
                elif '/term-deposit/' in path_str:
                    fi_type = 'term_deposit'
                elif '/recurring-deposit/' in path_str:
                    fi_type = 'recurring_deposit'
                elif '/deposit/' in path_str and '/term-deposit/' not in path_str and '/recurring-deposit/' not in path_str:
                    fi_type = 'deposit'
                elif '/etf/' in path_str:
                    fi_type = 'exchange_traded_funds'
                elif '/equities/' in path_str or '/equities-and-etfs/' in path_str:
                    fi_type = 'equity_shares'
                elif '/nps/' in path_str:
                    fi_type = 'national_pension_system'
                
                # Skip general APIs (user-subscriptions, consent, etc.)
                if not fi_type:
                    return  # Skip this API
                
                # Extract response schemas
                responses = item.get('response', [])
                response_schemas = []
                
                for response in responses:
                    if isinstance(response, dict):
                        body = response.get('body', '')
                        status_code = response.get('code', 200)
                        
                        if body and status_code == 200:
                            schema_data = extract_schema_from_body(body)
                            if schema_data:
                                response_schemas.append({
                                    'status_code': status_code,
                                    'schema': schema_data,
                                    'raw_body': body
                                })
                
                api_key = f"{path}/{endpoint_name}" if path else endpoint_name
                if api_key in finn_factor_apis:
                    api_key = f"{api_key}_{len(finn_factor_apis)}"
                
                finn_factor_apis[api_key] = {
                    'name': endpoint_name,
                    'method': request.get('method', 'GET'),
                    'url': raw_url,
                    'path': '/'.join(path_parts) if path_parts else raw_url,
                    'folder_path': path,
                    'fi_type': fi_type,
                    'responses': response_schemas
                }
    
    if 'item' in collection:
        for item in collection['item']:
            extract_from_item(item)
    
    return finn_factor_apis

def extract_schema_from_body(body: str) -> Optional[Dict]:
    """Extract schema from response body."""
    if not body or body == '<string>' or body == '':
        return None
    
    try:
        if body.strip().startswith('{') or body.strip().startswith('['):
            cleaned = body
            cleaned = re.sub(r'<string>', '""', cleaned)
            cleaned = re.sub(r'<integer>', '0', cleaned)
            cleaned = re.sub(r'<double>', '0.0', cleaned)
            cleaned = re.sub(r'<boolean>', 'false', cleaned)
            cleaned = re.sub(r'<dateTime>', '""', cleaned)
            cleaned = re.sub(r'<date>', '""', cleaned)
            cleaned = re.sub(r'<object>', '{}', cleaned)
            cleaned = re.sub(r'<Error:[^>]+>', '{}', cleaned)
            cleaned = re.sub(r'<[^>]+>', '""', cleaned)
            
            try:
                data = json.loads(cleaned)
                return extract_fields_from_json(data)
            except:
                try:
                    cleaned = re.sub(r',\s*}', '}', cleaned)
                    cleaned = re.sub(r',\s*]', ']', cleaned)
                    data = json.loads(cleaned)
                    return extract_fields_from_json(data)
                except:
                    return None
    except:
        return None
    
    return None

def extract_fields_from_json(data: Any, path: str = '') -> Dict:
    """Recursively extract fields from JSON."""
    fields = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            field_info = {
                'name': key,
                'type': 'object' if isinstance(value, (dict, list)) else type(value).__name__,
                'path': current_path
            }
            fields[key] = field_info
            
            if isinstance(value, dict):
                nested = extract_fields_from_json(value, current_path)
                field_info['nested'] = nested
            elif isinstance(value, list) and len(value) > 0:
                if isinstance(value[0], dict):
                    nested = extract_fields_from_json(value[0], current_path)
                    field_info['nested'] = nested
    elif isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict):
            return extract_fields_from_json(data[0], path)
    
    return fields

def main():
    """Main function with STRICT FI-specific API filtering."""
    base_dir = Path(__file__).parent
    rebit_dir = base_dir / 'rebit-schemas' / 'schemas'
    postman_file = base_dir / 'postman.json'
    
    print("🔍 Starting CORRECTED schema parsing (FI-specific APIs only)...")
    
    # Parse ReBIT schemas
    print("\n📖 Parsing ReBIT schemas...")
    rebit_data_points = {}
    if rebit_dir.exists():
        for schema_dir in rebit_dir.iterdir():
            if schema_dir.is_dir():
                fi_type = schema_dir.name
                xsd_files = list(schema_dir.glob('*.xsd'))
                
                for xsd_file in xsd_files:
                    data_points = extract_xsd_data_points(xsd_file, fi_type)
                    
                    if fi_type not in rebit_data_points:
                        rebit_data_points[fi_type] = {
                            'fi_type': fi_type,
                            'all_fields': [],
                            'by_category': defaultdict(list)
                        }
                    
                    for attr in data_points.get('attributes', []):
                        rebit_data_points[fi_type]['all_fields'].append(attr)
                        rebit_data_points[fi_type]['by_category'][attr.get('path', 'root')].append(attr)
    
    print(f"✅ Parsed {len(rebit_data_points)} ReBIT FI types")
    
    # Parse FinFactor APIs - STRICT MODE
    print("\n📡 Parsing FinFactor Postman collection (STRICT MODE)...")
    finn_factor_apis = parse_postman_collection_strict(postman_file)
    print(f"✅ Found {len(finn_factor_apis)} FI-specific API endpoints")
    
    # Show which APIs are included
    fi_api_count = defaultdict(int)
    for api_data in finn_factor_apis.values():
        fi_api_count[api_data['fi_type']] += 1
    
    print("\nAPIs per FI type:")
    for fi_type, count in sorted(fi_api_count.items()):
        print(f"  {fi_type}: {count} APIs")
    
    # Extract FinFactor data points
    print("\n🔍 Extracting FinFactor data points...")
    finn_factor_data_points = defaultdict(lambda: {
        'fi_type': '',
        'all_fields': [],
        'by_api': defaultdict(list)
    })
    
    for api_key, api_data in finn_factor_apis.items():
        fi_type = api_data.get('fi_type')
        if not fi_type:
            continue
        
        if fi_type not in finn_factor_data_points:
            finn_factor_data_points[fi_type] = {
                'fi_type': fi_type,
                'all_fields': [],
                'by_api': defaultdict(list)
            }
        
        finn_factor_data_points[fi_type]['fi_type'] = fi_type
        api_name = api_data.get('name', api_key)
        api_path = api_data.get('path', '')
        api_method = api_data.get('method', 'GET')
        
        def flatten_schema(schema_dict, parent_path='', depth=0):
            if depth > 20:
                return
            
            for field_name, field_data in schema_dict.items():
                if isinstance(field_data, dict):
                    field_info = {
                        'name': field_data.get('name', field_name),
                        'type': field_data.get('type', 'string'),
                        'path': field_data.get('path', parent_path),
                        'api_name': api_name,
                        'api_path': api_path,
                        'api_method': api_method
                    }
                    
                    finn_factor_data_points[fi_type]['all_fields'].append(field_info)
                    finn_factor_data_points[fi_type]['by_api'][api_name].append(field_info)
                    
                    if 'nested' in field_data and field_data['nested']:
                        flatten_schema(field_data['nested'], field_data.get('path', parent_path), depth + 1)
        
        for response in api_data.get('responses', []):
            schema = response.get('schema', {})
            if schema:
                flatten_schema(schema, '', 0)
    
    print(f"✅ Extracted data from {len(finn_factor_data_points)} FinFactor FI types")
    
    # Deduplicate and create comparison
    comparison_data = {
        'rebit': rebit_data_points,
        'finn_factor': dict(finn_factor_data_points),
        'summary': {}
    }
    
    for fi_type in set(list(rebit_data_points.keys()) + list(finn_factor_data_points.keys())):
        # Deduplicate ReBIT fields
        rebit_all = rebit_data_points.get(fi_type, {}).get('all_fields', [])
        rebit_unique = {}
        for field in rebit_all:
            name = field['name']
            if name not in rebit_unique:
                rebit_unique[name] = field
        
        # Deduplicate FinFactor fields
        finn_all = finn_factor_data_points.get(fi_type, {}).get('all_fields', [])
        finn_unique = {}
        for field in finn_all:
            name = field['name']
            if name not in finn_unique:
                finn_unique[name] = field
            else:
                # Track multiple API sources
                if 'api_sources' not in finn_unique[name]:
                    finn_unique[name]['api_sources'] = [finn_unique[name]['api_name']]
                finn_unique[name]['api_sources'].append(field['api_name'])
        
        # Update deduplicated data
        if fi_type in rebit_data_points:
            rebit_data_points[fi_type]['all_fields'] = list(rebit_unique.values())
        if fi_type in finn_factor_data_points:
            finn_factor_data_points[fi_type]['all_fields'] = list(finn_unique.values())
        
        # Calculate summary
        common = set(rebit_unique.keys()) & set(finn_unique.keys())
        rebit_only = set(rebit_unique.keys()) - set(finn_unique.keys())
        finn_only = set(finn_unique.keys()) - set(rebit_unique.keys())
        
        comparison_data['summary'][fi_type] = {
            'rebit_total': len(rebit_unique),
            'finn_factor_total': len(finn_unique),
            'common': len(common),
            'rebit_only': len(rebit_only),
            'finn_factor_only': len(finn_only)
        }
    
    # Save corrected comparison data
    output_file = base_dir / 'comparison_data_corrected.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Corrected comparison saved to: {output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("📊 CORRECTED COMPARISON SUMMARY (FI-specific APIs only)")
    print("="*80)
    
    for fi_type, summary in comparison_data['summary'].items():
        if summary['rebit_total'] > 0 or summary['finn_factor_total'] > 0:
            print(f"\n📁 {fi_type.upper().replace('_', ' ')}")
            print(f"  ├─ ReBIT Fields: {summary['rebit_total']}")
            print(f"  ├─ FinFactor Fields: {summary['finn_factor_total']}")
            print(f"  ├─ Common Fields: {summary['common']}")
            print(f"  ├─ ReBIT Only: {summary['rebit_only']}")
            print(f"  └─ FinFactor Extra: {summary['finn_factor_only']} ⭐")

if __name__ == '__main__':
    main()
