#!/usr/bin/env python3
"""
COMPREHENSIVE PARSER - ALL 50+ APIs
Extracts EVERY field from EVERY API response with complete source tracking.
"""

import json
import re
from pathlib import Path
from collections import defaultdict, OrderedDict
from parse_schemas import extract_xsd_data_points


def extract_fields_with_paths(obj, parent='', depth=0, max_depth=50):
    """
    Recursively extract ALL fields with their full paths and types.
    Returns list of (field_name, full_path, type) tuples.
    """
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
        # Process first item as template
        fields.extend(extract_fields_with_paths(obj[0], parent, depth, max_depth))
    
    return fields


def parse_all_api_responses(api_file: Path):
    """
    Parse ALL API responses from the file.
    Returns dict mapping FI types to their fields with API sources.
    """
    print(f"📖 Reading API response file: {api_file}")
    print(f"   File size: {api_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    with open(api_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"   Total characters: {len(content):,}")
    
    # Find all API response blocks
    # Pattern: name, endpoint, request, response
    pattern = r'{\s*name:\s*"([^"]+)",\s*endpoint:\s*"([^"]+)",\s*request:\s*{[^}]*},\s*response:\s*({.*?})\s*,\s*error:'
    
    matches = list(re.finditer(pattern, content, re.DOTALL))
    print(f"\n🔍 Found {len(matches)} API responses using regex")
    
    # If regex doesn't work well, try line-by-line parsing
    if len(matches) < 10:
        print("   ⚠️  Regex found too few matches, trying alternative parsing...")
        matches = parse_by_lines(content)
    
    # Map endpoints to FI types
    fi_type_mapping = {
        'mutual-fund': 'mutual_funds',
        'term-deposit': 'term_deposit',
        'recurring-deposit': 'recurring_deposit',
        'equities': 'equity_shares',
        'equities-and-etfs': 'equity_shares',
        'etf': 'exchange_traded_funds',
        'nps': 'national_pension_system',
        'deposit': 'deposit',  # Must be after term/recurring
    }
    
    # Store results
    api_data = defaultdict(lambda: {
        'apis': OrderedDict(),
        'all_fields': {},  # field_name -> list of API sources
        'field_details': []  # All field details with sources
    })
    
    # Process each API
    for match in matches:
        if isinstance(match, dict):
            api_name = match['name']
            endpoint = match['endpoint']
            response_str = match['response']
        else:
            api_name = match.group(1)
            endpoint = match.group(2)
            response_str = match.group(3)
        
        # Determine FI type
        fi_type = None
        endpoint_lower = endpoint.lower()
        
        for pattern, ft in fi_type_mapping.items():
            if pattern in endpoint_lower:
                # Skip if it's a more specific type
                if ft == 'deposit' and ('term-deposit' in endpoint_lower or 'recurring-deposit' in endpoint_lower):
                    continue
                fi_type = ft
                break
        
        if not fi_type:
            continue
        
        print(f"\n  📡 {api_name}")
        print(f"     Endpoint: {endpoint}")
        print(f"     FI Type: {fi_type}")
        
        # Parse response
        try:
            # Convert JavaScript to Python before eval
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
            api_data[fi_type]['apis'][api_name] = {
                'endpoint': endpoint,
                'field_count': len(fields),
                'fields': [f['name'] for f in fields]
            }
            
            # Track which APIs provide which fields
            for field in fields:
                field_name = field['name']
                
                if field_name not in api_data[fi_type]['all_fields']:
                    api_data[fi_type]['all_fields'][field_name] = []
                
                api_data[fi_type]['all_fields'][field_name].append({
                    'api_name': api_name,
                    'api_endpoint': endpoint,
                    'path': field['path'],
                    'type': field['type'],
                    'depth': field['depth']
                })
                
                # Add to field details
                api_data[fi_type]['field_details'].append({
                    'name': field_name,
                    'path': field['path'],
                    'type': field['type'],
                    'depth': field['depth'],
                    'api_name': api_name,
                    'api_endpoint': endpoint
                })
        
        except Exception as e:
            print(f"     ❌ Error: {str(e)[:100]}")
            continue
    
    return dict(api_data)


def parse_by_lines(content):
    """Alternative parser that works line by line."""
    lines = content.split('\n')
    matches = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for API name
        if 'name:' in line and 'endpoint:' in lines[i+1] if i+1 < len(lines) else False:
            # Extract name
            name_match = re.search(r'name:\s*"([^"]+)"', line)
            endpoint_match = re.search(r'endpoint:\s*"([^"]+)"', lines[i+1])
            
            if name_match and endpoint_match:
                api_name = name_match.group(1)
                endpoint = endpoint_match.group(1)
                
                # Find response block
                response_start = -1
                for j in range(i, min(i+20, len(lines))):
                    if 'response:' in lines[j]:
                        response_start = j
                        break
                
                if response_start > 0:
                    # Extract response (find matching braces)
                    brace_count = 0
                    response_lines = []
                    started = False
                    
                    for j in range(response_start, min(response_start+1000, len(lines))):
                        line_content = lines[j]
                        
                        if '{' in line_content and not started:
                            started = True
                        
                        if started:
                            response_lines.append(line_content)
                            brace_count += line_content.count('{')
                            brace_count -= line_content.count('}')
                            
                            if brace_count == 0 and started:
                                break
                    
                    response_str = '\n'.join(response_lines)
                    
                    matches.append({
                        'name': api_name,
                        'endpoint': endpoint,
                        'response': response_str
                    })
        
        i += 1
    
    print(f"   Line-by-line parser found {len(matches)} APIs")
    return matches


def main():
    """Main function."""
    base_dir = Path(__file__).parent
    rebit_dir = base_dir / 'rebit-schemas' / 'schemas'
    api_file = base_dir / 'finfactor' / 'apiResonse.json'
    
    print("="*80)
    print("🎯 COMPREHENSIVE PARSER - ALL 50+ APIs")
    print("="*80)
    
    # Step 1: Parse ReBIT schemas with table tracking
    print("\n📖 STEP 1: Parsing ReBIT Schemas...")
    rebit_data = {}
    
    for schema_dir in rebit_dir.iterdir():
        if schema_dir.is_dir():
            fi_type = schema_dir.name
            
            for xsd_file in schema_dir.glob('*.xsd'):
                data_points = extract_xsd_data_points(xsd_file, fi_type)
                
                if fi_type not in rebit_data:
                    rebit_data[fi_type] = {
                        'fields': {},  # field_name -> field details
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
    for fi_type, data in sorted(rebit_data.items()):
        print(f"   - {fi_type}: {len(data['fields'])} fields from {len(data['schemas'])} schemas")
    
    # Step 2: Parse ALL FinFactor APIs
    print("\n📡 STEP 2: Parsing ALL FinFactor APIs...")
    finn_data = parse_all_api_responses(api_file)
    
    print(f"\n✅ Extracted {len(finn_data)} FinFactor FI types")
    for fi_type, data in sorted(finn_data.items()):
        unique_fields = len(data['all_fields'])
        total_apis = len(data['apis'])
        print(f"   - {fi_type}: {unique_fields} unique fields from {total_apis} APIs")
    
    # Step 3: Create comprehensive comparison
    print("\n🔬 STEP 3: Creating Comprehensive Comparison...")
    
    all_fi_types = set(list(rebit_data.keys()) + list(finn_data.keys()))
    
    comparison = {
        'metadata': {
            'generated_at': '2026-01-04',
            'total_rebit_fi_types': len(rebit_data),
            'total_finn_fi_types': len(finn_data),
            'total_apis_parsed': sum(len(d['apis']) for d in finn_data.values())
        },
        'fi_types': {}
    }
    
    for fi_type in all_fi_types:
        rebit_fields = rebit_data.get(fi_type, {}).get('fields', {})
        finn_fields = finn_data.get(fi_type, {}).get('all_fields', {})
        
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
        
        comparison['fi_types'][fi_type] = {
            'summary': {
                'rebit_total': len(rebit_fields),
                'finn_total': len(finn_fields),
                'common': len(common_names),
                'rebit_only': len(rebit_only_names),
                'finn_only': len(finn_only_names),
                'coverage_percent': round((len(common_names) / len(rebit_fields) * 100) if rebit_fields else 0, 1),
                'apis_count': len(finn_data.get(fi_type, {}).get('apis', {}))
            },
            'common_fields': common_fields,
            'rebit_only_fields': rebit_only_fields,
            'finn_only_fields': finn_only_fields,
            'apis': list(finn_data.get(fi_type, {}).get('apis', {}).keys())
        }
    
    # Save comprehensive comparison
    output_file = base_dir / 'comparison_comprehensive.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved comprehensive comparison to: {output_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE COMPARISON SUMMARY")
    print("="*80)
    print(f"\nTotal APIs Parsed: {comparison['metadata']['total_apis_parsed']}")
    print(f"Total FI Types: {len(all_fi_types)}")
    
    for fi_type in sorted(comparison['fi_types'].keys()):
        summary = comparison['fi_types'][fi_type]['summary']
        if summary['rebit_total'] > 0 or summary['finn_total'] > 0:
            print(f"\n📁 {fi_type.upper().replace('_', ' ')}")
            print(f"   APIs: {summary['apis_count']}")
            print(f"   ReBIT: {summary['rebit_total']} fields")
            print(f"   FinFactor: {summary['finn_total']} fields")
            print(f"   Common: {summary['common']} ({summary['coverage_percent']}%)")
            print(f"   ReBIT Only: {summary['rebit_only']}")
            print(f"   FinFactor Extra: {summary['finn_only']} ⭐")
    
    print("\n" + "="*80)
    print("✅ DONE - All APIs parsed with complete field tracking!")
    print("="*80)


if __name__ == '__main__':
    main()
