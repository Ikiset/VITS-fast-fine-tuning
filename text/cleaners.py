import re
from text.japanese import japanese_to_romaji_with_accent, japanese_to_ipa, japanese_to_ipa2, japanese_to_ipa3
from text.korean import latin_to_hangul, number_to_hangul, divide_hangul, korean_to_lazy_ipa, korean_to_ipa
from text.mandarin import number_to_chinese, chinese_to_bopomofo, latin_to_bopomofo, chinese_to_romaji, chinese_to_lazy_ipa, chinese_to_ipa, chinese_to_ipa2
from text.sanskrit import devanagari_to_ipa
from text.english import english_to_lazy_ipa, english_to_ipa2, english_to_lazy_ipa2
from text.thai import num_to_thai, latin_to_thai
from text.french import expand_abbreviations, replace_symbols,remove_aux_symbols, french_to_ipa
# from text.shanghainese import shanghainese_to_ipa
# from text.cantonese import cantonese_to_ipa
# from text.ngu_dialect import ngu_dialect_to_ipa

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