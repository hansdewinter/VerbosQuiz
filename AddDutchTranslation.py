#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
import deepl

# Ensure stdout uses UTF-8 encoding (Python 3.7+)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def translate_verb(translator, spanish_verb):
    """
    Translate a Spanish verb to Dutch using DeepL API.
    
    Args:
        translator: DeepL Translator instance
        spanish_verb: Spanish verb string to translate
        
    Returns:
        Dutch translation string, or None if translation fails
    """
    try:
        result = translator.translate_text(
            spanish_verb,
            source_lang="ES",
            target_lang="NL"
        )
        return result.text
    except deepl.exceptions.DeepLException as e:
        print(f"Error translating '{spanish_verb}': {e}")
        return None
    except Exception as e:
        print(f"Unexpected error translating '{spanish_verb}': {e}")
        return None


def main():
    # Check for DeepL API key
    api_key = os.getenv('DEEPL_API_KEY')
    if not api_key:
        print("Error: DEEPL_API_KEY environment variable is not set.")
        print("Please set it using: export DEEPL_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Initialize DeepL translator
    try:
        translator = deepl.Translator(api_key)
    except Exception as e:
        print(f"Error initializing DeepL translator: {e}")
        sys.exit(1)
    
    # Load input JSON file
    input_file = "Verbos.json"
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found in current directory.")
        sys.exit(1)
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            verb_data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {input_file}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {input_file}: {e}")
        sys.exit(1)
    
    if not isinstance(verb_data, list):
        print(f"Error: {input_file} should contain a JSON array.")
        sys.exit(1)
    
    # Process each verb entry
    total_verbs = len(verb_data)
    print(f"Processing {total_verbs} verbs...")
    
    for index, verb_entry in enumerate(verb_data, 1):
        if not isinstance(verb_entry, dict):
            print(f"Warning: Entry {index} is not a dictionary, skipping.")
            continue
        
        if "verbo" not in verb_entry:
            print(f"Warning: Entry {index} missing 'verbo' field, skipping.")
            continue
        
        spanish_verb = verb_entry["verbo"]
        
        # Skip if already has dutch translation
        if "dutch" in verb_entry:
            print(f"[{index}/{total_verbs}] '{spanish_verb}' already has Dutch translation, skipping.")
            continue
        
        # Translate verb
        print(f"[{index}/{total_verbs}] Translating '{spanish_verb}'...", end=' ')
        dutch_translation = translate_verb(translator, spanish_verb)
        
        if dutch_translation:
            verb_entry["dutch"] = dutch_translation
            print(f"✓ '{dutch_translation}'")
        else:
            print("✗ Failed")
            # Continue processing other verbs even if one fails
    
    # Save to output file
    output_file = "complete.json"
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(verb_data, f, indent=4, ensure_ascii=False)
        print(f"\nSuccessfully saved {total_verbs} entries to {output_file}")
    except Exception as e:
        print(f"\nError writing to {output_file}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
