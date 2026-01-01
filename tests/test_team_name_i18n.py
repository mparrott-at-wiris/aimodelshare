"""
Tests for Team Name Translation Utilities

This module tests the centralized team name translations for ES/CA app variants.
Tests cover translation functions and DataFrame formatting for display.
"""
import pytest
import pandas as pd
from aimodelshare.moral_compass.apps.team_name_i18n import (
    translate_team_name_for_display,
    translate_team_name_to_english,
    _format_leaderboard_for_display,
    TEAM_NAME_TRANSLATIONS,
    TEAM_NAMES,
)


class TestTeamNameTranslations:
    """Test suite for team name translation functions."""
    
    def test_team_names_list_completeness(self):
        """Test that TEAM_NAMES list contains expected teams."""
        assert len(TEAM_NAMES) == 6
        assert "The Justice League" in TEAM_NAMES
        assert "The Moral Champions" in TEAM_NAMES
        assert "The Data Detectives" in TEAM_NAMES
        assert "The Ethical Explorers" in TEAM_NAMES
        assert "The Fairness Finders" in TEAM_NAMES
        assert "The Accuracy Avengers" in TEAM_NAMES
    
    def test_translation_dictionary_structure(self):
        """Test that TEAM_NAME_TRANSLATIONS has correct structure."""
        assert "en" in TEAM_NAME_TRANSLATIONS
        assert "es" in TEAM_NAME_TRANSLATIONS
        assert "ca" in TEAM_NAME_TRANSLATIONS
        
        # Check all languages have the same teams
        for lang in ["en", "es", "ca"]:
            assert len(TEAM_NAME_TRANSLATIONS[lang]) == 6
            for team in TEAM_NAMES:
                assert team in TEAM_NAME_TRANSLATIONS[lang]
    
    def test_translate_team_name_for_display_english(self):
        """Test translation to English (should be identity)."""
        for team in TEAM_NAMES:
            assert translate_team_name_for_display(team, "en") == team
    
    def test_translate_team_name_for_display_spanish(self):
        """Test translation to Spanish."""
        assert translate_team_name_for_display("The Justice League", "es") == "La Liga de la Justicia"
        assert translate_team_name_for_display("The Moral Champions", "es") == "Los Campeones Morales"
        assert translate_team_name_for_display("The Data Detectives", "es") == "Los Detectives de Datos"
        assert translate_team_name_for_display("The Ethical Explorers", "es") == "Los Exploradores Éticos"
        assert translate_team_name_for_display("The Fairness Finders", "es") == "Los Buscadores de Equidad"
        assert translate_team_name_for_display("The Accuracy Avengers", "es") == "Los Vengadores de Precisión"
    
    def test_translate_team_name_for_display_catalan(self):
        """Test translation to Catalan."""
        assert translate_team_name_for_display("The Justice League", "ca") == "La Lliga de la Justícia"
        assert translate_team_name_for_display("The Moral Champions", "ca") == "Els Campions Morals"
        assert translate_team_name_for_display("The Data Detectives", "ca") == "Els Detectives de Dades"
        assert translate_team_name_for_display("The Ethical Explorers", "ca") == "Els Exploradors Ètics"
        assert translate_team_name_for_display("The Fairness Finders", "ca") == "Els Cercadors d'Equitat"
        assert translate_team_name_for_display("The Accuracy Avengers", "ca") == "Els Venjadors de Precisió"
    
    def test_translate_team_name_for_display_empty_string(self):
        """Test translation with empty string."""
        assert translate_team_name_for_display("", "en") == ""
        assert translate_team_name_for_display("", "es") == ""
        assert translate_team_name_for_display("", "ca") == ""
    
    def test_translate_team_name_for_display_unknown_team(self):
        """Test translation with unknown team name (should return original)."""
        unknown_team = "The Unknown Team"
        assert translate_team_name_for_display(unknown_team, "en") == unknown_team
        assert translate_team_name_for_display(unknown_team, "es") == unknown_team
        assert translate_team_name_for_display(unknown_team, "ca") == unknown_team
    
    def test_translate_team_name_for_display_invalid_lang(self):
        """Test translation with invalid language (should default to English)."""
        team = "The Justice League"
        assert translate_team_name_for_display(team, "fr") == team
        assert translate_team_name_for_display(team, "de") == team
        assert translate_team_name_for_display(team, "invalid") == team
    
    def test_translate_team_name_for_display_default_lang(self):
        """Test translation with default language parameter."""
        team = "The Justice League"
        assert translate_team_name_for_display(team) == team
    
    def test_translate_team_name_to_english_from_spanish(self):
        """Test reverse translation from Spanish to English."""
        assert translate_team_name_to_english("La Liga de la Justicia", "es") == "The Justice League"
        assert translate_team_name_to_english("Los Campeones Morales", "es") == "The Moral Champions"
        assert translate_team_name_to_english("Los Detectives de Datos", "es") == "The Data Detectives"
        assert translate_team_name_to_english("Los Exploradores Éticos", "es") == "The Ethical Explorers"
        assert translate_team_name_to_english("Los Buscadores de Equidad", "es") == "The Fairness Finders"
        assert translate_team_name_to_english("Los Vengadores de Precisión", "es") == "The Accuracy Avengers"
    
    def test_translate_team_name_to_english_from_catalan(self):
        """Test reverse translation from Catalan to English."""
        assert translate_team_name_to_english("La Lliga de la Justícia", "ca") == "The Justice League"
        assert translate_team_name_to_english("Els Campions Morals", "ca") == "The Moral Champions"
        assert translate_team_name_to_english("Els Detectives de Dades", "ca") == "The Data Detectives"
        assert translate_team_name_to_english("Els Exploradors Ètics", "ca") == "The Ethical Explorers"
        assert translate_team_name_to_english("Els Cercadors d'Equitat", "ca") == "The Fairness Finders"
        assert translate_team_name_to_english("Els Venjadors de Precisió", "ca") == "The Accuracy Avengers"
    
    def test_translate_team_name_to_english_from_english(self):
        """Test reverse translation from English (identity)."""
        for team in TEAM_NAMES:
            assert translate_team_name_to_english(team, "en") == team
    
    def test_translate_team_name_to_english_empty_string(self):
        """Test reverse translation with empty string."""
        assert translate_team_name_to_english("", "en") == ""
        assert translate_team_name_to_english("", "es") == ""
        assert translate_team_name_to_english("", "ca") == ""
    
    def test_translate_team_name_to_english_unknown_name(self):
        """Test reverse translation with unknown name (should return original)."""
        unknown_name = "Unknown Team Name"
        assert translate_team_name_to_english(unknown_name, "es") == unknown_name
        assert translate_team_name_to_english(unknown_name, "ca") == unknown_name
    
    def test_translate_team_name_to_english_invalid_lang(self):
        """Test reverse translation with invalid language (should return original)."""
        team = "The Justice League"
        assert translate_team_name_to_english(team, "fr") == team
        assert translate_team_name_to_english(team, "invalid") == team


class TestLeaderboardFormatting:
    """Test suite for leaderboard DataFrame formatting functions."""
    
    def test_format_leaderboard_for_display_none(self):
        """Test formatting with None DataFrame."""
        assert _format_leaderboard_for_display(None, "en") is None
        assert _format_leaderboard_for_display(None, "es") is None
        assert _format_leaderboard_for_display(None, "ca") is None
    
    def test_format_leaderboard_for_display_empty(self):
        """Test formatting with empty DataFrame."""
        df = pd.DataFrame()
        result = _format_leaderboard_for_display(df, "en")
        assert result is not None
        assert result.empty
        assert result is not df  # Should be a copy
    
    def test_format_leaderboard_for_display_no_team_column(self):
        """Test formatting with DataFrame missing Team column."""
        df = pd.DataFrame({"Score": [0.5, 0.6, 0.7]})
        result = _format_leaderboard_for_display(df, "en")
        assert result is not None
        assert len(result) == 3
        assert "Team" not in result.columns
        assert result is not df  # Should be a copy
    
    def test_format_leaderboard_for_display_english(self):
        """Test formatting with English language (identity)."""
        df = pd.DataFrame({
            "Team": ["The Justice League", "The Moral Champions", "The Data Detectives"],
            "Score": [0.85, 0.82, 0.79]
        })
        result = _format_leaderboard_for_display(df, "en")
        
        assert result is not None
        assert result is not df  # Should be a copy
        assert len(result) == 3
        assert list(result["Team"]) == ["The Justice League", "The Moral Champions", "The Data Detectives"]
        assert list(result["Score"]) == [0.85, 0.82, 0.79]
    
    def test_format_leaderboard_for_display_spanish(self):
        """Test formatting with Spanish translations."""
        df = pd.DataFrame({
            "Team": ["The Justice League", "The Moral Champions", "The Data Detectives"],
            "Score": [0.85, 0.82, 0.79]
        })
        result = _format_leaderboard_for_display(df, "es")
        
        assert result is not None
        assert result is not df  # Should be a copy
        assert len(result) == 3
        assert list(result["Team"]) == [
            "La Liga de la Justicia",
            "Los Campeones Morales",
            "Los Detectives de Datos"
        ]
        assert list(result["Score"]) == [0.85, 0.82, 0.79]
        
        # Original DataFrame should be unchanged
        assert list(df["Team"]) == ["The Justice League", "The Moral Champions", "The Data Detectives"]
    
    def test_format_leaderboard_for_display_catalan(self):
        """Test formatting with Catalan translations."""
        df = pd.DataFrame({
            "Team": ["The Justice League", "The Moral Champions", "The Data Detectives"],
            "Score": [0.85, 0.82, 0.79]
        })
        result = _format_leaderboard_for_display(df, "ca")
        
        assert result is not None
        assert result is not df  # Should be a copy
        assert len(result) == 3
        assert list(result["Team"]) == [
            "La Lliga de la Justícia",
            "Els Campions Morals",
            "Els Detectives de Dades"
        ]
        assert list(result["Score"]) == [0.85, 0.82, 0.79]
        
        # Original DataFrame should be unchanged
        assert list(df["Team"]) == ["The Justice League", "The Moral Champions", "The Data Detectives"]
    
    def test_format_leaderboard_for_display_non_destructive(self):
        """Test that formatting does not modify original DataFrame."""
        original_teams = ["The Justice League", "The Moral Champions"]
        df = pd.DataFrame({
            "Team": original_teams.copy(),
            "Score": [0.85, 0.82]
        })
        
        # Format for Spanish
        result = _format_leaderboard_for_display(df, "es")
        
        # Original should be unchanged
        assert list(df["Team"]) == original_teams
        
        # Result should have translations
        assert list(result["Team"]) == ["La Liga de la Justicia", "Los Campeones Morales"]
    
    def test_format_leaderboard_for_display_all_teams(self):
        """Test formatting with all team names."""
        df = pd.DataFrame({
            "Team": TEAM_NAMES.copy(),
            "Score": [0.85, 0.84, 0.83, 0.82, 0.81, 0.80]
        })
        
        # Test Spanish
        result_es = _format_leaderboard_for_display(df, "es")
        expected_es = [
            "La Liga de la Justicia",
            "Los Campeones Morales",
            "Los Detectives de Datos",
            "Los Exploradores Éticos",
            "Los Buscadores de Equidad",
            "Los Vengadores de Precisión"
        ]
        assert list(result_es["Team"]) == expected_es
        
        # Test Catalan
        result_ca = _format_leaderboard_for_display(df, "ca")
        expected_ca = [
            "La Lliga de la Justícia",
            "Els Campions Morals",
            "Els Detectives de Dades",
            "Els Exploradors Ètics",
            "Els Cercadors d'Equitat",
            "Els Venjadors de Precisió"
        ]
        assert list(result_ca["Team"]) == expected_ca
        
        # Original should be unchanged
        assert list(df["Team"]) == TEAM_NAMES


class TestRoundTripTranslations:
    """Test suite for round-trip translation consistency."""
    
    def test_roundtrip_spanish(self):
        """Test that translating to Spanish and back preserves English names."""
        for team_en in TEAM_NAMES:
            team_es = translate_team_name_for_display(team_en, "es")
            team_back = translate_team_name_to_english(team_es, "es")
            assert team_back == team_en, f"Round-trip failed for {team_en} via Spanish"
    
    def test_roundtrip_catalan(self):
        """Test that translating to Catalan and back preserves English names."""
        for team_en in TEAM_NAMES:
            team_ca = translate_team_name_for_display(team_en, "ca")
            team_back = translate_team_name_to_english(team_ca, "ca")
            assert team_back == team_en, f"Round-trip failed for {team_en} via Catalan"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
