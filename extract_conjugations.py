#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import requests
from bs4 import BeautifulSoup
import json

# Ensure stdout uses UTF-8 encoding (Python 3.7+)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def extract_conjugations(verb, tiempo):

    # Get the data
    url = f"https://www.esfacil.eu/nl/werkwoorden/vervoeging.html?verb={verb}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        # Ensure UTF-8 encoding
        response.encoding = 'utf-8'
        html_content = response.text
    except requests.RequestException as e:
        print(f"Error fetching URL: {e}")
        return []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find the section with id="indicativo-presente" (Tegenwoordige tijd)
    presente_section = soup.find('h3', id=tiempo)
    
    if not presente_section:
        print(f"Could not find {tiempo} section for verb '{verb}'")
        return []
    
    # Find the table following this h3 tag
    # The table should be a sibling or within the same parent container
    table = presente_section.find_next('table')
    
    if not table:
        print(f"Could not find table in {tiempo} section for verb '{verb}'")
        return []
    
    # Find all table rows
    rows = table.find_all('tr')
    conjugations = []
    
    # Extract conjugations from each row
    for row in rows:
        # Find the th element (pronoun cell) and td element (conjugation cell)
        th = row.find('th')
        td = row.find('td')
        
        # Extract pronoun if present
        pronoun = None
        if th:
            pronoun_span = th.find('span', class_='pronoun')
            if pronoun_span:
                pronoun = pronoun_span.get_text(strip=True)
        
        if td:
            # Find all spans with class starting with "conjugation-"
            # This includes conjugation-1 (regular), conjugation-3 (irregular), etc.
            conjugation_spans = td.find_all('span', class_=lambda x: x and x.startswith('conjugation-'))
            
            if conjugation_spans:
                # For simple conjugations, get the text directly
                # For compound forms, get the full text from the td
                if len(conjugation_spans) == 1:
                    # Simple conjugation
                    conj_text = conjugation_spans[0].get_text(strip=True)
                else:
                    # Compound form - get all text from td
                    conj_text = td.get_text(strip=False)
                
                if conj_text:
                    # Add pronoun if available
                    if pronoun:
                        conjugations.append((pronoun, conj_text))
                    else:
                        conjugations.append(conj_text)
    
    return conjugations


def main():

    data = []

    tiempos = ['indicativo-presente', 'indicativo-preterito-perfecto', 'indicativo-preterito-indefinido']
    
    f = open("verbos.txt", "r", encoding='utf-8')
    for LINE in f.readlines():
        LINE = LINE.strip()
        if LINE is None: continue

        verb = LINE
        if verb[-2:] == "se": reflexivo = True
        else: reflexivo = False

        json_entry = {}
        json_entry["verb"] = verb
        for tiempo in tiempos:
            conjugations = extract_conjugations(verb, tiempo)
            for i in range(len(conjugations)):
                if not reflexivo:
                    conjugations[i] = conjugations[i][1]
                else:
                    conjugations[i] = conjugations[i][0] + " " + conjugations[i][1]
            json_entry[tiempo] = conjugations
    
        data.append(json_entry)    
    f.close()
    
    with open("output.json", "w", encoding='utf-8') as outfile:
        json.dump(data, outfile, indent=4, ensure_ascii=False)   


if __name__ == "__main__":
    main()

