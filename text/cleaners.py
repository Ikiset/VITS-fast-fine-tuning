import re
from text.french import expand_abbreviations, replace_symbols,remove_aux_symbols, french_to_ipa

# Regular expression matching whitespace:
_whitespace_re = re.compile(r'\s+')

def collapse_whitespace(text):
  return re.sub(_whitespace_re, ' ', text)

def french_cleaners(text):
    """Pipeline for French text. There is no need to expand numbers, phonemizer already does that"""
    text = expand_abbreviations(text, lang="fr")
    text = text.lower()
    text = replace_symbols(text, lang="fr")
    text = remove_aux_symbols(text)
    phonemes = french_to_ipa(text)
    phonemes = collapse_whitespace(phonemes)
    return phonemes