from django import template
import re
import html


register = template.Library()

@register.filter
def clean_content(value):
    # 1. Supprimer les balises <p> et </p>
    value = re.sub(r'</?p[^>]*>', '', value)

    # 2. Supprimer toutes les balises sauf <img>
    value = re.sub(r'<(?!img\b)[^>]+>', '', value)

    return value


@register.filter
def strip_html(value):
    """Supprime toutes les balises HTML et décode les entités"""
    # Supprimer les balises HTML
    clean_text = re.sub(r'<.*?>', '', value)
    # Décoder les entités HTML (&eacute; -> é)
    clean_text = html.unescape(clean_text)
    return clean_text