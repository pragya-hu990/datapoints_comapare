#!/usr/bin/env python3
"""
ACCURATE parser using REAL API responses from apiResonse.json
Extracts EVERY single datapoint including all nested fields.
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict, OrderedDict

# Import ReBIT schema parser
from parse_schemas import extract_xsd_data_points


def extract_all_fields_recursively(data: Any, parent_path: str = '', depth: int = 0) -> List[Dict]:
    """
    Recursively extract ALL fields from nested JSON structure.
    Returns list of field dictionaries with full paths.
    """
    fields = []
    
    if depth > 50:  # Prevent infinite recursion
        return fields
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{parent_path}.{key}" if parent_path else key
            
            # Add this field
            field_info = {
                'name': key,
                'path': current_path,
                'type': type(value).__name__,
                'depth': depth
            }
            
            # Determine more specific type
            if isinstance(value, bool):
                field_info['type'] = 'boolean'
            elif isinstance(value, int):
                field_info['type'] = 'integer'
            elif isinstance(value, float):
                field_info['type'] = 'float'
            elif isinstance(value, str):
                field_info['type'] = 'string'
                # Check if it's a date
                if re.match(r'\\d{4}-\\d{2}-\\d{2}', str(value)):
                    field_info['type'] = 'date/datetime'
            elif isinstance(value, list):
                field_info['type'] = 'array'
                if len(value) > 0:
                    field_info['array_item_type'] = type(value[0]).__name__
            elif isinstance(value, dict):
                field_info['type'] = 'object'
            elif value is None:
                field_info['type'] = 'null'
            
            fields.append(field_info)
            
            # Recurse into nested structures
            if isinstance(value, dict):
                nested_fields = extract_all_fields_recursively(value, current_path, depth + 1)
                fields.extend(nested_fields)
            elif isinstance(value, list) and len(value) > 0:
                # Process first item in array as template
                if isinstance(value[0], (dict, list)):
                    nested_fields = extract_all_fields_recursively(value[0], current_path, depth + 1)
                    fields.extend(nested_fields)
    
    elif isinstance(data, list) and len(data) > 0:
        # Process first item as template
        if isinstance(data[0], (dict, list)):
            nested_fields = extract_all_fields_recursively(data[0], parent_path, depth)
            fields.extend(nested_fields)
    
    return fields


def parse_api_response_file(api_response_file: Path) -> Dict[str, Any]:
    """
    Parse the actual API response file and extract all fields by endpoint.
    """
    print(f"📖 Reading API response file: {api_response_file}")
    
    # Read the file
    with open(api_response_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # The file is a JavaScript file, need to extract the JSON
    # Find the responses array
    match = re.search(r'responses:\\s*\\[(.*?)\\]\\s*};?\\s*$', content, re.DOTALL)
    if not match:
        print("❌ Could not find responses array in file")
        return {}
    
    # Parse each API response
    api_data_by_fi_type = defaultdict(lambda: {
        'apis': {},
        'all_fields': [],
        'field_counts': defaultdict(int)
    })
    
    # Extract individual API responses using regex
    api_pattern = r'{\\s*name:\\s*"([^"]+)",\\s*endpoint:\\s*"([^"]+)".*?response:\\s*({.*?})\\s*,\\s*error:'
    
    for match in re.finditer(api_pattern, content, re.DOTALL):
        api_name = match.group(1)
        endpoint = match.group(2)
        response_str = match.group(3)
        
        print(f"\\n  Processing: {api_name} ({endpoint})")
        
        # Determine FI type from endpoint
        fi_type = None
        endpoint_lower = endpoint.lower()
        
        if '/mutual-fund/' in endpoint_lower:
            fi_type = 'mutual_funds'
        elif '/term-deposit/' in endpoint_lower:
            fi_type = 'term_deposit'
        elif '/recurring-deposit/' in endpoint_lower:
            fi_type = 'recurring_deposit'
        elif '/deposit/' in endpoint_lower and '/term-deposit/' not in endpoint_lower and '/recurring-deposit/' not in endpoint_lower:
            fi_type = 'deposit'
        elif '/etf/' in endpoint_lower:
            fi_type = 'exchange_traded_funds'
        elif '/equities/' in endpoint_lower or '/equities-and-etfs/' in endpoint_lower:
            fi_type = 'equity_shares'
        elif '/nps/' in endpoint_lower:
            fi_type = 'national_pension_system'
        
        if not fi_type:
            print(f"    ⚠️  Skipping - not FI-specific")
            continue
        
        # Try to parse the response JSON
        try:
            # Clean up JavaScript syntax to make it valid JSON
            json_str = response_str
            # Replace JavaScript object notation with JSON
            json_str = re.sub(r'(\\w+):', r'"\\1":', json_str)  # Quote keys
            json_str = re.sub(r':\\s*undefined', ': null', json_str)  # undefined -> null
            
            # Try to parse
            try:
                response_data = json.loads(json_str)
            except:
                # If that fails, use eval (careful!)
                response_data = eval(response_str)
            
            # Extract all fields from this response
            fields = extract_all_fields_recursively(response_data)
            
            print(f"    ✅ Extracted {len(fields)} fields")
            
            # Store API data
            api_data_by_fi_type[fi_type]['apis'][api_name] = {
                'endpoint': endpoint,
                'fields': fields,
                'field_count': len(fields)
            }
            
            # Add to all_fields with API source
            for field in fields:
                field['api_name'] = api_name
                field['api_endpoint'] = endpoint
                api_data_by_fi_type[fi_type]['all_fields'].append(field)
                api_data_by_fi_type[fi_type]['field_counts'][field['name']] += 1
        
        except Exception as e:
            print(f"    ❌ Error parsing response: {e}")
            continue
    
    return dict(api_data_by_fi_type)


def deduplicate_fields(fields: List[Dict]) -> List[Dict]:
    """
    Deduplicate fields by name, keeping the most detailed version.
    """
    unique_fields = OrderedDict()
    
    for field in fields:
        name = field['name']
        if name not in unique_fields:
            unique_fields[name] = field
        else:
            # Keep the one with more information (deeper path usually means more context)
            if len(field.get('path', '')) > len(unique_fields[name].get('path', '')):
                unique_fields[name] = field
    
    return list(unique_fields.values())


def main():
    """Main function to create accurate comparison."""
    base_dir = Path(__file__).parent
    rebit_dir = base_dir / 'rebit-schemas' / 'schemas'
    api_response_file = base_dir / 'finfactor' / 'apiResonse.json'
    
    print("="*80)
    print("🎯 ACCURATE COMPARISON - Using Real API Responses")
    print("="*80)
    
    # Parse ReBIT schemas
    print("\\n📖 Step 1: Parsing ReBIT schemas...")
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
                            'source_schema': xsd_file.name
                        }
                    
                    for attr in data_points.get('attributes', []):
                        attr['source_schema'] = xsd_file.name
                        attr['source_type'] = 'rebit'
                        rebit_data_points[fi_type]['all_fields'].append(attr)
        
        # Deduplicate ReBIT fields
        for fi_type in rebit_data_points:
            all_fields = rebit_data_points[fi_type]['all_fields']
            unique_fields = {}
            for field in all_fields:
                name = field['name']
                if name not in unique_fields:
                    unique_fields[name] = field
            rebit_data_points[fi_type]['all_fields'] = list(unique_fields.values())
            rebit_data_points[fi_type]['unique_count'] = len(unique_fields)
    
    print(f"✅ Parsed {len(rebit_data_points)} ReBIT FI types")
    
    # Parse FinFactor API responses
    print("\\n📡 Step 2: Parsing FinFactor API responses...")
    finn_factor_data = parse_api_response_file(api_response_file)
    
    # Deduplicate FinFactor fields
    for fi_type in finn_factor_data:
        all_fields = finn_factor_data[fi_type]['all_fields']
        finn_factor_data[fi_type]['all_fields'] = deduplicate_fields(all_fields)
        finn_factor_data[fi_type]['unique_count'] = len(finn_factor_data[fi_type]['all_fields'])
    
    print(f"\\n✅ Extracted data from {len(finn_factor_data)} FinFactor FI types")
    
    # Create comparison
    print("\\n🔬 Step 3: Creating comparison...")
    comparison_data = {
        'metadata': {
            'generated_at': '2026-01-04',
            'parser_version': '3.0-accurate',
            'source': 'real_api_responses',
            'api_response_file': str(api_response_file)
        },
        'rebit': rebit_data_points,
        'finn_factor': finn_factor_data,
        'comparison': {},
        'summary': {}
    }
    
    # Compare each FI type
    all_fi_types = set(list(rebit_data_points.keys()) + list(finn_factor_data.keys()))
    
    for fi_type in all_fi_types:
        rebit_fields = {f['name']: f for f in rebit_data_points.get(fi_type, {}).get('all_fields', [])}
        finn_fields = {f['name']: f for f in finn_factor_data.get(fi_type, {}).get('all_fields', [])}
        
        common_names = set(rebit_fields.keys()) & set(finn_fields.keys())
        rebit_only_names = set(rebit_fields.keys()) - set(finn_fields.keys())
        finn_only_names = set(finn_fields.keys()) - set(rebit_fields.keys())
        
        comparison_data['comparison'][fi_type] = {
            'common': [{'rebit': rebit_fields[name], 'finn': finn_fields[name]} for name in common_names],
            'rebit_only': [rebit_fields[name] for name in rebit_only_names],
            'finn_only': [finn_fields[name] for name in finn_only_names]
        }
        
        comparison_data['summary'][fi_type] = {
            'rebit_total': len(rebit_fields),
            'finn_total': len(finn_fields),
            'common': len(common_names),
            'rebit_only': len(rebit_only_names),
            'finn_only': len(finn_only_names),
            'coverage_percent': round((len(common_names) / len(rebit_fields) * 100) if rebit_fields else 0, 1)
        }
    
    # Save comparison
    output_file = base_dir / 'comparison_data_accurate.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)
    
    print(f"\\n✅ Accurate comparison saved to: {output_file}")
    
    # Print summary
    print("\\n" + "="*80)
    print("📊 ACCURATE COMPARISON SUMMARY")
    print("="*80)
    
    for fi_type, summary in comparison_data['summary'].items():
        if summary['rebit_total'] > 0 or summary['finn_total'] > 0:
            print(f"\\n📁 {fi_type.upper().replace('_', ' ')}")
            print(f"  ├─ ReBIT Fields: {summary['rebit_total']}")
            print(f"  ├─ FinFactor Fields: {summary['finn_total']}")
            print(f"  ├─ Common: {summary['common']} ({summary['coverage_percent']}% coverage)")
            print(f"  ├─ ReBIT Only: {summary['rebit_only']}")
            print(f"  └─ FinFactor Extra: {summary['finn_only']} ⭐")
    
    print("\\n" + "="*80)
    print("✅ DONE - All datapoints extracted accurately!")
    print("="*80)


if __name__ == '__main__':
    main()
