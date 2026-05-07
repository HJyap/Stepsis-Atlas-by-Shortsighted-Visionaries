import requests
import json
from typing import Dict, List

OPENROUTER_API_KEY = ""
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def extract_keywords_with_llm(user_prompt: str) -> Dict:
    """
    Use LLM to intelligently extract important keywords from question
    """
    print(f"📝 Your question: {user_prompt}\n")
    print("🤖 Extracting keywords with LLM...\n")
    
    # Create prompt for LLM to extract keywords
    llm_prompt = f"""Extract the most important keywords from this question.

Question: {user_prompt}

Return ONLY a JSON object with:
{{
    "keywords": ["keyword1", "keyword2", "keyword3", ...]
}}

Be concise. Only include truly important words (skip: how, is, the, a, etc).
Include medical terms, locations, and main topics."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": llm_prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }
    
    try:
        print("⏳ Waiting for LLM response...")
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        response_text = result['choices'][0]['message']['content']
        
        # Parse JSON from response
        try:
            # Remove markdown code blocks if present
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            llm_result = json.loads(cleaned_text)
            print("✅ Keywords extracted successfully\n")
            return llm_result
        except json.JSONDecodeError:
            print("⚠️ Could not parse LLM response as JSON")
            return {
                "keywords": [],
                "question_type": "unknown",
                "error": "Could not parse response"
            }
        
    except requests.exceptions.Timeout:
        print("❌ API timeout")
        return {"keywords": [], "error": "timeout"}
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        return {"keywords": [], "error": str(e)}

def save_to_json(user_prompt: str, llm_keywords: Dict, output_file: str = 'keyword_extraction.json') -> str:
    """Save extraction result to JSON file"""
    
    result = {
        'original_question': user_prompt,
        'extracted_keywords': llm_keywords.get('keywords', []),
        'keyword_count': len(llm_keywords.get('keywords', []))
    }
    
    print(f"💾 Saving to {output_file}...\n")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return output_file

def display_result(user_prompt: str, llm_keywords: Dict):
    """Display extraction result"""
    print("=" * 70)
    print("📊 KEYWORD EXTRACTION RESULT:")
    print("=" * 70)
    print(f"\nOriginal Question:")
    print(f"{user_prompt}")
    print(f"\nExtracted Keywords ({len(llm_keywords.get('keywords', []))}):")
    for i, keyword in enumerate(llm_keywords.get('keywords', []), 1):
        print(f"  {i}. {keyword}")
    print("\n" + "=" * 70)

def main():
    print("=" * 70)
    print("🔍 KEYWORD EXTRACTION WITH LLM")
    print("=" * 70 + "\n")
    
    # Check API key
    if OPENROUTER_API_KEY == "sk-...":
        print("❌ Error: Please set your OpenRouter API key!")
        print("   Replace 'sk-...' with your actual key from https://openrouter.ai")
        return
    
    # Get user input
    print("📝 ENTER YOUR QUESTION (press Enter twice to finish):\n")
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
        print("❌ No question provided")
        return
    
    print("\n" + "=" * 70)
    
    # Extract keywords using LLM
    llm_keywords = extract_keywords_with_llm(user_prompt)
    
    # Display result
    display_result(user_prompt, llm_keywords)
    
    # Save to JSON
    output_file = save_to_json(user_prompt, llm_keywords)
    
    print(f"✅ Results saved to: {output_file}\n")
    print("=" * 70)
    print("✨ DONE!")
    print("=" * 70)

if __name__ == "__main__":
    main()