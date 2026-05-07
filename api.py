import requests
import json
import re
from typing import Dict, List
from collections import defaultdict

OPENROUTER_API_KEY = ""
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def load_keyword_database(json_file: str) -> Dict:
    """Load keyword database"""
    print(f"📂 Loading database...")
    with open(json_file, 'r', encoding='utf-8') as f:
        database = json.load(f)
    print(f"✅ Loaded {database['metadata']['total_variables']} variables")
    print(f"   Sources: {database['metadata']['total_files_analyzed']} research papers\n")
    return database

def extract_patterns_smart(database: Dict) -> Dict:
    """Extract patterns with smart keyword extraction"""
    patterns_map = {}
    
    for importance_level in ['high_importance', 'medium_importance', 'low_importance']:
        for item in database.get(importance_level, []):
            variable_name = item.get('variable', 'Unknown')
            for pattern in item.get('patterns', []):
                pattern_lower = pattern.lower().strip()
                patterns_map[pattern_lower] = {
                    'variable': variable_name,
                    'importance': importance_level,
                    'unit': item.get('unit'),
                    'note': item.get('note', ''),
                    'source_files': item.get('source_files', [])
                }
    
    return patterns_map

def search_keywords_smart(user_prompt: str, patterns_map: Dict) -> List[Dict]:
    """Smart keyword matching"""
    prompt_lower = user_prompt.lower()
    matched = []
    matched_variables = set()
    
    sorted_patterns = sorted(patterns_map.items(), key=lambda x: len(x[0]), reverse=True)
    
    for pattern, info in sorted_patterns:
        pattern_len = len(pattern)
        
        if pattern_len < 3:
            continue
        
        # Strategy 1: Exact word boundary match
        pattern_regex = r'\b' + re.escape(pattern) + r'\b'
        if re.search(pattern_regex, prompt_lower):
            if info['variable'] not in matched_variables:
                matched.append({
                    'pattern': pattern,
                    'variable': info['variable'],
                    'importance': info['importance'],
                    'unit': info['unit'],
                    'note': info['note'],
                    'source_files': info['source_files'],
                    'match_type': 'exact'
                })
                matched_variables.add(info['variable'])
            continue
        
        # Strategy 2: Partial word matching
        prompt_words = re.findall(r'\b\w+\b', prompt_lower)
        pattern_words = re.findall(r'\b\w+\b', pattern)
        
        for p_word in pattern_words:
            if p_word in prompt_words and len(p_word) >= 3:
                if info['variable'] not in matched_variables:
                    matched.append({
                        'pattern': pattern,
                        'variable': info['variable'],
                        'importance': info['importance'],
                        'unit': info['unit'],
                        'note': info['note'],
                        'source_files': info['source_files'],
                        'match_type': 'partial'
                    })
                    matched_variables.add(info['variable'])
                break
    
    # Sort by importance
    importance_order = {'high_importance': 0, 'medium_importance': 1, 'low_importance': 2}
    matched.sort(key=lambda x: importance_order.get(x['importance'], 3))
    
    return matched

def extract_numerical_data(matched_keywords: List[Dict]) -> Dict:
    """Extract all numerical data from notes"""
    print("🔢 Extracting numerical data from database...")
    
    numerical_data = defaultdict(list)
    
    for kw in matched_keywords:
        variable = kw['variable']
        note = kw['note']
        unit = kw['unit']
        
        if not note:
            continue
        
        # Extract ranges like "9.5-39%" or "13-50%"
        range_pattern = r'(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*(%)?'
        ranges = re.findall(range_pattern, note)
        
        for min_val, max_val, percent in ranges:
            try:
                min_float = float(min_val)
                max_float = float(max_val)
                
                numerical_data[variable].append({
                    'type': 'range',
                    'min': min_float,
                    'max': max_float,
                    'unit': unit,
                    'context': note[:150]
                })
            except ValueError:
                continue
        
        # Extract single values
        single_pattern = r':\s*(\d+\.?\d*)\s*(%)?'
        singles = re.findall(single_pattern, note)
        
        for value, percent in singles:
            try:
                val_float = float(value)
                numerical_data[variable].append({
                    'type': 'single',
                    'value': val_float,
                    'unit': unit,
                    'context': note[:150]
                })
            except ValueError:
                continue
    
    return dict(numerical_data)

def validate_answer_in_database(user_prompt: str, matched_keywords: List[Dict], numerical_analysis: Dict) -> Dict:
    """
    Validate if the answer to user's question exists in database
    Returns: {
        'has_answer': bool,
        'data_available': str,
        'missing_info': str
    }
    """
    print("✅ Validating if answer exists in database...")
    
    prompt_lower = user_prompt.lower()
    
    # Keywords that indicate specific statistics being asked
    statistics_keywords = ['how many', 'how much', 'number', 'count', 'total', 'cases', 'numbers', 'statistics', 'prevalence', 'incidence']
    asking_for_statistics = any(keyword in prompt_lower for keyword in statistics_keywords)
    
    # Geographic keywords
    geographic_keywords = ['usa', 'united states', 'japan', 'china', 'europe', 'hospital', 'icu', 'country', 'region']
    asking_for_location = any(keyword in prompt_lower for keyword in geographic_keywords)
    
    # Check what we have in database
    has_numerical_data = len(numerical_analysis) > 0
    has_clinical_data = len(matched_keywords) > 0
    
    validation = {
        'asking_for_statistics': asking_for_statistics,
        'asking_for_location_specific': asking_for_location,
        'has_relevant_variables': has_clinical_data,
        'has_numerical_values': has_numerical_data,
        'data_type': 'clinical metrics, diagnostic criteria, outcomes' if has_clinical_data else 'unknown'
    }
    
    # Determine if we can answer
    if asking_for_statistics and asking_for_location:
        if not has_numerical_data:
            validation['can_answer'] = False
            validation['reason'] = "Database contains clinical metrics but NOT location-specific epidemiological statistics"
    else:
        validation['can_answer'] = has_clinical_data or has_numerical_data
        validation['reason'] = "Answer might be possible" if has_clinical_data else "No relevant data found"
    
    return validation

def send_to_llm_smart(user_prompt: str, matched_keywords: List[Dict], numerical_analysis: Dict, validation: Dict) -> str:
    """
    Send to LLM with SMART handling:
    - If answer exists: provide precise data
    - If answer doesn't exist: tell user clearly
    """
    print("🤖 Sending to LLM with validation...")
    
    # Format the numerical data
    data_summary = []
    for variable, analysis in numerical_analysis.items():
        if analysis['statistics']:
            stats = analysis['statistics']
            data_summary.append(
                f"- {variable}:\n"
                f"  Maximum: {stats['maximum']} {stats['unit']}\n"
                f"  Minimum: {stats['minimum']} {stats['unit']}\n"
                f"  Average: {stats['average']:.2f}"
            )
    
    precise_data_context = "\n".join(data_summary) if data_summary else "No numerical data available"
    
    # Create smart prompt that acknowledges limitations
    if not validation.get('can_answer', False):
        prompt = f"""USER QUESTION:
{user_prompt}

DATABASE STATUS:
- Database contains: {validation['data_type']}
- The question asks for: location-specific epidemiological statistics (how many cases in a specific region)

IMPORTANT: This database does NOT contain information about:
- Geographic distribution of sepsis cases (by country/region)
- Total number of sepsis cases
- Epidemiological statistics (incidence, prevalence)

The database DOES contain:
- Clinical diagnostic criteria (qSOFA, SOFA scores)
- Prognostic factors and risk indicators
- Treatment outcomes and mortality rates
- Research data from 20 medical studies

ANSWER:
Please tell the user that this specific question cannot be answered from the available database. Suggest what information IS available in the database instead."""

    else:
        prompt = f"""USER QUESTION:
{user_prompt}

AVAILABLE DATA FROM DATABASE:
{precise_data_context}

MATCHED CLINICAL VARIABLES:
{", ".join([k['variable'] for k in matched_keywords])}

INSTRUCTIONS:
1. Answer based ONLY on the data provided
2. Be specific with numbers and units
3. If data is incomplete, state what information is available
4. Do NOT make assumptions beyond the data

ANSWER:"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        
        result = response.json()
        analysis = result['choices'][0]['message']['content']
        print("✅ Analysis complete\n")
        return analysis
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("=" * 70)
    print("🎯 SMART MEDICAL DATABASE ANALYSIS")
    print("With Data Validation & Limitation Detection")
    print("=" * 70 + "\n")
    
    # Load database
    database = load_keyword_database('final_final.json')
    
    # Extract patterns
    print("🔑 Extracting patterns from database...")
    patterns_map = extract_patterns_smart(database)
    print(f"✅ Ready to search ({len(patterns_map)} patterns)\n")
    
    # Get user input
    print("📝 ENTER YOUR MEDICAL QUESTION (press Enter twice to finish):\n")
    lines = []
    while True:
        try:
            line = input()
            if line == "":
                if lines and lines[-1] == "":
                    break
            lines.append(line)
        except EOFError:
            break
    
    user_prompt = "\n".join(lines[:-1]) if lines else ""
    
    if not user_prompt.strip():
        print("❌ No prompt provided")
        return
    
    print("\n" + "=" * 70)
    print(f"Your question: {user_prompt}")
    print("=" * 70 + "\n")
    
    # Search keywords
    print("🔍 Searching database for relevant variables...")
    matched_keywords = search_keywords_smart(user_prompt, patterns_map)
    print(f"✅ Found {len(matched_keywords)} relevant variables\n")
    
    # Display matches
    if matched_keywords:
        print("📋 Matched Variables from Database:")
        for i, kw in enumerate(matched_keywords, 1):
            importance_emoji = "🔴" if kw['importance'] == 'high_importance' else "🟡"
            print(f"  {i}. {importance_emoji} {kw['variable']} ({kw['unit']})")
        print()
    
    # Extract numerical data
    numerical_data = extract_numerical_data(matched_keywords)
    
    # Analyze numerical data
    from collections import defaultdict
    numerical_analysis = {}
    
    for variable, data_points in numerical_data.items():
        variable_analysis = {
            'data_points': data_points,
            'statistics': {}
        }
        
        all_values = []
        for dp in data_points:
            if dp['type'] == 'range':
                all_values.extend([dp['min'], dp['max']])
            else:
                all_values.append(dp['value'])
        
        if all_values:
            variable_analysis['statistics'] = {
                'minimum': min(all_values),
                'maximum': max(all_values),
                'average': sum(all_values) / len(all_values),
                'unit': data_points[0]['unit'] if data_points else 'unknown'
            }
        
        numerical_analysis[variable] = variable_analysis
    
    # Validate if answer exists
    validation = validate_answer_in_database(user_prompt, matched_keywords, numerical_analysis)
    
    print("\n" + "=" * 70)
    print("📊 DATA VALIDATION:")
    print("=" * 70)
    print(f"Asking for statistics: {validation['asking_for_statistics']}")
    print(f"Asking for location-specific data: {validation['asking_for_location_specific']}")
    print(f"Can answer from database: {validation.get('can_answer', False)}")
    print(f"Reason: {validation.get('reason', 'Unknown')}\n")
    
    # Send to LLM with validation
    llm_analysis = send_to_llm_smart(user_prompt, matched_keywords, numerical_analysis, validation)
    
    # Create result
    result = {
        'user_prompt': user_prompt,
        'database_info': {
            'total_variables': database['metadata']['total_variables'],
            'total_files_analyzed': database['metadata']['total_files_analyzed']
        },
        'validation': validation,
        'database_matches': {
            'matched_keywords': matched_keywords,
            'summary': {
                'total_matches': len(matched_keywords),
                'high_importance_matches': sum(1 for k in matched_keywords if k['importance'] == 'high_importance'),
                'medium_importance_matches': sum(1 for k in matched_keywords if k['importance'] == 'medium_importance')
            }
        },
        'extracted_numerical_data': numerical_analysis,
        'analysis_method': 'Smart validation + conditional LLM synthesis',
        'llm_analysis': llm_analysis
    }
    
    # Save
    print("💾 Saving results...")
    with open('extraction_results.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("✅ Saved to extraction_results.json\n")
    
    # Display analysis
    print("=" * 70)
    print("📝 ANALYSIS RESULT:")
    print("=" * 70)
    if llm_analysis:
        print(llm_analysis)
    else:
        print("No analysis available")
    
    print("\n" + "=" * 70)
    print("✨ DONE!")
    print("=" * 70)

if __name__ == "__main__":
    main()