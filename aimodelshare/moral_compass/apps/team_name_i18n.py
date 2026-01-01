"""
Team Name Translation Utilities for Moral Compass Apps

This module provides centralized team name translations for ES/CA app variants.
Canonical English names are used for internal logic/storage/API; translations
are applied only for UI display (leaderboards, stats screens, certificates).
"""
from typing import Optional, Dict
import pandas as pd

TEAM_NAMES = [
    "The Justice League", "The Moral Champions", "The Data Detectives",
    "The Ethical Explorers", "The Fairness Finders", "The Accuracy Avengers"
]

TEAM_NAME_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "The Justice League": "The Justice League",
        "The Moral Champions": "The Moral Champions",
        "The Data Detectives": "The Data Detectives",
        "The Ethical Explorers": "The Ethical Explorers",
        "The Fairness Finders": "The Fairness Finders",
        "The Accuracy Avengers": "The Accuracy Avengers",
    },
    "es": {
        "The Justice League": "La Liga de la Justicia",
        "The Moral Champions": "Los Campeones Morales",
        "The Data Detectives": "Los Detectives de Datos",
        "The Ethical Explorers": "Los Exploradores Éticos",
        "The Fairness Finders": "Los Buscadores de Equidad",
        "The Accuracy Avengers": "Los Vengadores de Precisión",
    },
    "ca": {
        "The Justice League": "La Lliga de la Justícia",
        "The Moral Champions": "Els Campions Morals",
        "The Data Detectives": "Els Detectives de Dades",
        "The Ethical Explorers": "Els Exploradors Ètics",
        "The Fairness Finders": "Els Cercadors d'Equitat",
        "The Accuracy Avengers": "Els Venjadors de Precisió",
    },
}

def translate_team_name_for_display(team_en: str, lang: str = "en") -> str:
    """
    Translate a canonical English team name to the specified language for UI display.
    
    Args:
        team_en: The canonical English team name
        lang: Target language code ('en', 'es', or 'ca')
    
    Returns:
        Translated team name, or original if translation not found
    """
    if not team_en:
        return ""
    if lang not in TEAM_NAME_TRANSLATIONS:
        lang = "en"
    return TEAM_NAME_TRANSLATIONS[lang].get(str(team_en), str(team_en))

def translate_team_name_to_english(display_name: str, lang: str = "en") -> str:
    """
    Reverse lookup: translate a localized team name back to canonical English.
    
    Args:
        display_name: The localized team name
        lang: Source language code ('en', 'es', or 'ca')
    
    Returns:
        Canonical English team name, or original if not found
    """
    if not display_name:
        return ""
    if lang not in TEAM_NAME_TRANSLATIONS:
        return display_name
    for en, localized in TEAM_NAME_TRANSLATIONS[lang].items():
        if localized == display_name:
            return en
    return display_name

def _format_leaderboard_for_display(df: Optional[pd.DataFrame], lang: str = "en") -> Optional[pd.DataFrame]:
    """
    Create a display copy of a leaderboard DataFrame with translated team names.
    Non-destructive: returns a copy, does not modify the original DataFrame.
    
    Args:
        df: DataFrame containing a 'Team' column
        lang: Target language code ('en', 'es', or 'ca')
    
    Returns:
        Copy of DataFrame with translated team names, or None if input is None
    """
    if df is None:
        return None
    if df.empty or "Team" not in df.columns:
        return df.copy()
    df_display = df.copy()
    df_display["Team"] = df_display["Team"].apply(lambda t: translate_team_name_for_display(t, lang))
    return df_display
