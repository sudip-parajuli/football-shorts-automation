"""Editorial staging chosen from the narrated point, never a random template cycle."""
import re


def photo_treatment(text):
    if re.search(r'\b(history|historic|career|childhood|early years|legacy|debut|farewell|retirement|retired|remember|199\d|198\d|197\d)\b',text,re.I):
        return 'archive'
    return 'photo'


def is_comparison(text):
    return bool(re.search(r'\b(versus|vs\.?|against|rivalry|compared|comparison|contrast|both)\b',text,re.I))
