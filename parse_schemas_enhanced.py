#!/usr/bin/env python3
"""
Enhanced parser with advanced semantic matching for ReBIT vs FinFactor comparison.
This version uses comprehensive semantic mappings to ensure accurate field matching.
"""

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
import re

class SemanticMatcher:
    """Advanced semantic field name matcher."""
    
    def __init__(self, mappings_file: Path):
        """Initialize with semantic mappings."""
        with open(mappings_file, 'r', encoding='utf-8') as f:
            self.mappings = json.load(f)
        
        # Build reverse lookup for fast matching
        self.field_to_canonical = {}
        self._build_reverse_lookup()
    
    def _build_reverse_lookup(self):
        """Build reverse lookup from all variations to canonical names."""
        for category, fields in self.mappings['field_mappings'].items():
            for canonical, variations in fields.items():
                # Canonical name maps to itself
                self.field_to_canonical[self._normalize(canonical)] = canonical
                
                # All variations map to canonical
                for variant in variations:
                    self.field_to_canonical[self._normalize(variant)] = canonical
    
    def _normalize(self, field_name: str) -> str:
        """Normalize field name for comparison."""
        return field_name.lower().replace('_', '').replace('-', '').replace(' ', '')
    
    def get_canonical_name(self, field_name: str, context: str = '') -> str:
        """Get canonical name for a field, considering context."""
        normalized = self._normalize(field_name)
        
        # Direct lookup
        if normalized in self.field_to_canonical:
            return self.field_to_canonical[normalized]
        
        # Context-aware lookup
        if context and field_name in self.mappings.get('context_aware_mappings', {}):
            context_mappings = self.mappings['context_aware_mappings'][field_name]
            for ctx_key, variants in context_mappings.items():
                if ctx_key in context.lower():
                    for variant in variants:
                        if self._normalize(variant) == normalized:
                            return variant
        
        # Abbreviation expansion
        for abbr, expansion in self.mappings.get('abbreviation_expansions', {}).items():
            if abbr in normalized:
                expanded = normalized.replace(abbr, expansion.lower())
                if expanded in self.field_to_canonical:
                    return self.field_to_canonical[expanded]
        
        # Return original if no match
        return field_name
    
    def are_equivalent(self, field1: str, field2: str, context1: str = '', context2: str = '') -> Tuple[bool, str]:
        """Check if two field names are semantically equivalent."""
        canonical1 = self.get_canonical_name(field1, context1)
        canonical2 = self.get_canonical_name(field2, context2)
        
        if canonical1 == canonical2:
            return True, canonical1
        
        # Check semantic equivalents
        for equiv_group in self.mappings.get('semantic_equivalents', {}).get('same_meaning_different_names', []):
            if field1 in equiv_group and field2 in equiv_group:
                return True, equiv_group[0]  # Return first as canonical
        
        return False, ''
    
    def get_similarity_score(self, field1: str, field2: str) -> float:
        """Calculate similarity score between two field names (0-1)."""
        # Exact match
        if field1 == field2:
            return 1.0
        
        # Canonical match
        canonical1 = self.get_canonical_name(field1)
        canonical2 = self.get_canonical_name(field2)
        if canonical1 == canonical2:
            return 0.95
        
        # Normalized match
        norm1 = self._normalize(field1)
        norm2 = self._normalize(field2)
        if norm1 == norm2:
            return 0.9
        
        # Substring match
        if norm1 in norm2 or norm2 in norm1:
            return 0.7
        
        # Levenshtein-like simple similarity
        common_chars = set(norm1) & set(norm2)
        if common_chars:
            return len(common_chars) / max(len(norm1), len(norm2)) * 0.5
        
        return 0.0


def load_semantic_matcher() -> SemanticMatcher:
    """Load semantic matcher with mappings."""
    base_dir = Path(__file__).parent
    mappings_file = base_dir / 'semantic_mappings.json'
    return SemanticMatcher(mappings_file)


# Import existing parser functions
from parse_schemas import (
    extract_xsd_data_points,
    parse_postman_collection,
    extract_schema_from_body,
    extract_fields_from_json,
    extract_fields_from_string
)


def enhanced_comparison(rebit_data: Dict, finn_data: Dict, matcher: SemanticMatcher) -> Dict:
    """Perform enhanced comparison with semantic matching."""
    
    comparison_results = {}
    
    # Get all FI types
    all_fi_types = set(list(rebit_data.keys()) + list(finn_data.keys()))
    
    for fi_type in all_fi_types:
        rebit_fields = rebit_data.get(fi_type, {}).get('all_fields', [])
        finn_fields = finn_data.get(fi_type, {}).get('all_fields', [])
        
        # Build lookup by canonical name
        rebit_by_canonical = defaultdict(list)
        for field in rebit_fields:
            canonical = matcher.get_canonical_name(
                field['name'],
                field.get('path', '')
            )
            field['canonical_name'] = canonical
            rebit_by_canonical[canonical].append(field)
        
        finn_by_canonical = defaultdict(list)
        for field in finn_fields:
            canonical = matcher.get_canonical_name(
                field['name'],
                field.get('path', '')
            )
            field['canonical_name'] = canonical
            finn_by_canonical[canonical].append(field)
        
        # Categorize fields
        common_fields = []
        rebit_only_fields = []
        finn_only_fields = []
        
        # Find common fields (by canonical name)
        common_canonical = set(rebit_by_canonical.keys()) & set(finn_by_canonical.keys())
        
        for canonical in common_canonical:
            rebit_variants = rebit_by_canonical[canonical]
            finn_variants = finn_by_canonical[canonical]
            
            # Take the most representative field from each
            rebit_field = rebit_variants[0]
            finn_field = finn_variants[0]
            
            # Check if names are different (semantic match)
            is_semantic_match = rebit_field['name'] != finn_field['name']
            
            common_fields.append({
                'canonical_name': canonical,
                'rebit_name': rebit_field['name'],
                'finn_name': finn_field['name'],
                'is_semantic_match': is_semantic_match,
                'rebit_field': rebit_field,
                'finn_field': finn_field,
                'similarity_score': matcher.get_similarity_score(
                    rebit_field['name'],
                    finn_field['name']
                )
            })
        
        # ReBIT-only fields
        rebit_only_canonical = set(rebit_by_canonical.keys()) - set(finn_by_canonical.keys())
        for canonical in rebit_only_canonical:
            for field in rebit_by_canonical[canonical]:
                rebit_only_fields.append(field)
        
        # FinFactor-only fields (extra value)
        finn_only_canonical = set(finn_by_canonical.keys()) - set(rebit_by_canonical.keys())
        for canonical in finn_only_canonical:
            for field in finn_by_canonical[canonical]:
                finn_only_fields.append(field)
        
        comparison_results[fi_type] = {
            'common': common_fields,
            'rebit_only': rebit_only_fields,
            'finn_only': finn_only_fields,
            'summary': {
                'total_common': len(common_fields),
                'total_rebit_only': len(rebit_only_fields),
                'total_finn_only': len(finn_only_fields),
                'total_rebit': len(rebit_by_canonical),
                'total_finn': len(finn_by_canonical),
                'semantic_matches': sum(1 for f in common_fields if f['is_semantic_match']),
                'exact_matches': sum(1 for f in common_fields if not f['is_semantic_match'])
            }
        }
    
    return comparison_results


def main():
    """Main function with enhanced semantic matching."""
    base_dir = Path(__file__).parent
    rebit_dir = base_dir / 'rebit-schemas' / 'schemas'
    postman_file = base_dir / 'postman.json'
    
    print("🚀 Starting ENHANCED schema parsing with semantic matching...")
    
    # Load semantic matcher
    print("📚 Loading semantic mappings...")
    matcher = load_semantic_matcher()
    print(f"✅ Loaded {len(matcher.field_to_canonical)} field mappings")
    
    # Parse ReBIT schemas (reuse existing function)
    print("\n📖 Parsing ReBIT schemas...")
    rebit_data_points = {}
    if rebit_dir.exists():
        for schema_dir in rebit_dir.iterdir():
            if schema_dir.is_dir():
                fi_type = schema_dir.name
                xsd_files = list(schema_dir.glob('*.xsd'))
                
                for xsd_file in xsd_files:
                    print(f"  ├─ {fi_type}: {xsd_file.name}")
                    data_points = extract_xsd_data_points(xsd_file, fi_type)
                    
                    if fi_type not in rebit_data_points:
                        rebit_data_points[fi_type] = {
                            'fi_type': fi_type,
                            'all_fields': [],
                            'by_category': defaultdict(list),
                            'source_schema': xsd_file.name
                        }
                    
                    # Add schema source to each field
                    for attr in data_points.get('attributes', []):
                        attr['source_schema'] = xsd_file.name
                        attr['source_type'] = 'rebit'
                        rebit_data_points[fi_type]['all_fields'].append(attr)
                        rebit_data_points[fi_type]['by_category'][attr.get('path', 'root')].append(attr)
    
    print(f"✅ Parsed {len(rebit_data_points)} ReBIT FI types")
    
    # Parse FinFactor APIs (reuse existing function)
    print("\n📡 Parsing FinFactor Postman collection...")
    finn_factor_apis = parse_postman_collection(postman_file)
    print(f"✅ Found {len(finn_factor_apis)} API endpoints")
    
    # Extract FinFactor data points with API source tracking
    print("\n🔍 Extracting FinFactor data points...")
    finn_factor_data_points = defaultdict(lambda: {
        'fi_type': '',
        'all_fields': [],
        'by_api': defaultdict(list)
    })
    
    general_fi_types = ['term_deposit', 'recurring_deposit', 'deposit', 'mutual_funds',
                       'exchange_traded_funds', 'equity_shares']
    
    for api_key, api_data in finn_factor_apis.items():
        fi_type = api_data.get('fi_type', 'unknown')
        fi_types_to_process = [fi_type] if fi_type != 'general' else general_fi_types
        
        for target_fi_type in fi_types_to_process:
            if target_fi_type == 'unknown':
                continue
            
            if target_fi_type not in finn_factor_data_points:
                finn_factor_data_points[target_fi_type] = {
                    'fi_type': target_fi_type,
                    'all_fields': [],
                    'by_api': defaultdict(list)
                }
            
            finn_factor_data_points[target_fi_type]['fi_type'] = target_fi_type
            api_name = api_data.get('name', api_key)
            api_path = api_data.get('path', '')
            api_method = api_data.get('method', 'GET')
            
            def flatten_schema(schema_dict, parent_path='', field_type='response', depth=0):
                if depth > 20:
                    return
                
                for field_name, field_data in schema_dict.items():
                    if isinstance(field_data, dict):
                        field_info = {
                            'name': field_data.get('name', field_name),
                            'normalized_name': field_data.get('normalized_name', field_name),
                            'type': field_data.get('type', 'string'),
                            'path': field_data.get('path', parent_path),
                            'api_name': api_name,
                            'api_path': api_path,
                            'api_method': api_method,
                            'api_full_endpoint': f"{api_method} {api_path}",
                            'field_category': field_type,
                            'source_type': 'finn_factor'
                        }
                        
                        finn_factor_data_points[target_fi_type]['all_fields'].append(field_info)
                        finn_factor_data_points[target_fi_type]['by_api'][api_name].append(field_info)
                        
                        if 'nested' in field_data and field_data['nested']:
                            flatten_schema(field_data['nested'], field_data.get('path', parent_path), field_type, depth + 1)
            
            # Extract request and response fields
            request_schema = api_data.get('request_schema')
            if request_schema:
                flatten_schema(request_schema, '', 'request')
            
            for response in api_data.get('responses', []):
                schema = response.get('schema', {})
                if schema:
                    flatten_schema(schema, '', 'response')
    
    print(f"✅ Extracted data from {len(finn_factor_data_points)} FinFactor FI types")
    
    # Perform enhanced comparison
    print("\n🔬 Performing enhanced semantic comparison...")
    comparison_results = enhanced_comparison(
        rebit_data_points,
        dict(finn_factor_data_points),
        matcher
    )
    
    # Build final output structure
    output_data = {
        'metadata': {
            'generated_at': '2026-01-04',
            'parser_version': '2.0-enhanced',
            'semantic_matching': True,
            'total_rebit_fi_types': len(rebit_data_points),
            'total_finn_fi_types': len(finn_factor_data_points)
        },
        'rebit': rebit_data_points,
        'finn_factor': dict(finn_factor_data_points),
        'comparison': comparison_results,
        'summary': {}
    }
    
    # Generate summary
    for fi_type, comp_data in comparison_results.items():
        output_data['summary'][fi_type] = comp_data['summary']
    
    # Save enhanced comparison data
    output_file = base_dir / 'comparison_data_enhanced.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Enhanced comparison saved to: {output_file}")
    
    # Print detailed summary
    print("\n" + "="*80)
    print("📊 ENHANCED COMPARISON SUMMARY")
    print("="*80)
    
    total_semantic_matches = 0
    total_exact_matches = 0
    
    for fi_type, comp_data in comparison_results.items():
        summary = comp_data['summary']
        if summary['total_rebit'] > 0 or summary['total_finn'] > 0:
            print(f"\n📁 {fi_type.upper().replace('_', ' ')}")
            print(f"  ├─ ReBIT Fields: {summary['total_rebit']}")
            print(f"  ├─ FinFactor Fields: {summary['total_finn']}")
            print(f"  ├─ Common Fields: {summary['total_common']}")
            print(f"  │  ├─ Exact Matches: {summary['exact_matches']}")
            print(f"  │  └─ Semantic Matches: {summary['semantic_matches']} 🎯")
            print(f"  ├─ ReBIT Only: {summary['total_rebit_only']}")
            print(f"  └─ FinFactor Extra: {summary['total_finn_only']} ⭐")
            
            total_semantic_matches += summary['semantic_matches']
            total_exact_matches += summary['exact_matches']
    
    print("\n" + "="*80)
    print(f"🎯 Total Semantic Matches Found: {total_semantic_matches}")
    print(f"✅ Total Exact Matches: {total_exact_matches}")
    print("="*80)

if __name__ == '__main__':
    main()
