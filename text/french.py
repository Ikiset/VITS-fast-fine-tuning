import re
from phonemizer import phonemize 
# !pip install phonemizer
# !apt-get install espeak

# List of (regular expression, replacement) pairs for abbreviations in french:
abbreviations_fr = [
    (re.compile("\\b%s\\." % x[0], re.IGNORECASE), x[1])
    for x in [
        ("M", "monsieur"),
        ("Mlle", "mademoiselle"),
        ("Mlles", "mesdemoiselles"),
        ("Mme", "Madame"),
        ("Mmes", "Mesdames"),
        ("N.B", "nota bene"),
        ("M", "monsieur"),
        ("p.c.q", "parce que"),
        ("Pr", "professeur"),
        ("qqch", "quelque chose"),
        ("rdv", "rendez-vous"),
        ("max", "maximum"),
        ("min", "minimum"),
        ("no", "numéro"),
        ("adr", "adresse"),
        ("dr", "docteur"),
        ("st", "saint"),
        ("co", "companie"),
        ("jr", "junior"),
        ("sgt", "sergent"),
        ("capt", "capitain"),
        ("col", "colonel"),
        ("av", "avenue"),
        ("av. J.-C", "avant Jésus-Christ"),
        ("apr. J.-C", "après Jésus-Christ"),
        ("art", "article"),
        ("boul", "boulevard"),
        ("c.-à-d", "c’est-à-dire"),
        ("etc", "et cetera"),
        ("ex", "exemple"),
        ("excl", "exclusivement"),
        ("boul", "boulevard"),
    ]
] + [
    (re.compile("\\b%s" % x[0]), x[1])
    for x in [
        ("Mlle", "mademoiselle"),
        ("Mlles", "mesdemoiselles"),
        ("Mme", "Madame"),
        ("Mmes", "Mesdames"),
    ]
]

def expand_abbreviations(text, lang="fr"):
    if lang == "fr":
        _abbreviations = abbreviations_fr
    for regex, replacement in _abbreviations:
        text = re.sub(regex, replacement, text)
    return text

def replace_symbols(text, lang="en"):
    text = text.replace(";", ",")
    text = text.replace("-", " ")
    text = text.replace(":", ",")
    if lang == "fr":
        text = text.replace("&", " et ")
    return text

def remove_aux_symbols(text):
    text = re.sub(r"[\<\>\(\)\[\]\"]+", "", text)
    return text

def french_to_ipa(text):
    text = phonemize(text, language='fr-fr', backend='espeak', strip=True)
    return text