# I18N Translation Support for Bias Detective Apps

## Overview

This document describes the internationalization (i18n) implementation for Bias Detective Part 1 and Part 2 apps, following the same pattern used in the Ethical Revelation app.

## Supported Languages

- **English (en)** - Default language
- **Spanish (es)** - Spanish translations
- **Catalan (ca)** - Catalan translations

## Usage

Users can select their preferred language by adding a query parameter to the URL:

```
https://your-app-url.com?lang=en   # English
https://your-app-url.com?lang=es   # Spanish  
https://your-app-url.com?lang=ca   # Catalan
```

If no language parameter is provided, or an invalid language is specified, the app defaults to English.

## Implementation Details

### Architecture

Both `bias_detective_part1.py` and `bias_detective_part2.py` implement i18n using the following components:

1. **TRANSLATIONS Dictionary**: Contains all translatable strings organized by language
2. **t() Helper Function**: Retrieves translated strings based on language and key
3. **get_quiz_config() Function**: Returns language-specific quiz configurations
4. **lang_state**: Gradio state variable that stores the user's selected language throughout the session
5. **Language Detection**: The `handle_load()` function reads the `lang` query parameter and stores it in `lang_state`

### What Is Translated

#### Fully Translated Elements:

- **Quiz Questions** (9-10 quizzes per app)
  - Question text
  - All answer options
  - Success messages for correct answers
  - Feedback messages for incorrect answers

- **UI Messages**
  - Loading screens
  - Authentication messages  
  - Error messages

- **Dashboard Labels** (defined but not yet fully implemented in UI)
  - Score labels
  - Rank labels
  - Progress indicators

#### Not Translated (Technical Limitations):

- **Button Labels**: Generated statically before language is known
- **Module HTML Content**: Static HTML created at component generation time
- **Slide Titles**: Part of static module definitions

To translate these elements would require restructuring the app to generate components dynamically based on language, which is beyond the scope of this implementation.

## Code Structure

### Translation Dictionary Structure

```python
TRANSLATIONS = {
    "en": {
        "key": "English text",
        # ...
    },
    "es": {
        "key": "Spanish text",
        # ...
    },
    "ca": {
        "key": "Catalan text",
        # ...
    }
}
```

### Quiz Configuration Structure

```python
QUIZ_CONFIG = {  # English
    0: {
        "t": "t1",  # Task ID
        "q": "Question text?",
        "o": ["Option A", "Option B", "Option C"],
        "a": "Option A",  # Correct answer
        "success": "Success message"
    },
    # ...
}

QUIZ_CONFIG_ES = {  # Spanish
    # Same structure with translated text
}

QUIZ_CONFIG_CA = {  # Catalan
    # Same structure with translated text
}
```

### Helper Functions

```python
def t(lang: str, key: str) -> str:
    """Get translated text for given language and key."""
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)

def get_quiz_config(lang="en"):
    """Get quiz configuration for the specified language."""
    if lang == "es":
        return QUIZ_CONFIG_ES
    elif lang == "ca":
        return QUIZ_CONFIG_CA
    else:
        return QUIZ_CONFIG
```

## Translation Coverage

### Bias Detective Part 1
- **Quiz Questions**: 9 quizzes fully translated (quiz IDs: 0, 1, 2, 3, 4, 5, 7, 8, 9, 10)
- **UI Strings**: ~15 translated keys
- **Total Translation Strings**: ~135 (45 per language)

### Bias Detective Part 2
- **Quiz Questions**: 9 quizzes fully translated (quiz IDs: 1-9)
- **UI Strings**: ~12 translated keys
- **Total Translation Strings**: ~135 (45 per language)

## Testing

The implementation has been verified with:

1. **Syntax Validation**: Python syntax is valid for both files
2. **Structure Verification**: All required components are present:
   - TRANSLATIONS dicts with en, es, ca
   - QUIZ_CONFIG_ES and QUIZ_CONFIG_CA for each app
   - get_quiz_config() helper functions
   - t() translation helpers
   - lang_state variables
   - Language detection in handle_load()

3. **Code Review**: No issues found
4. **Security Scan**: No security vulnerabilities detected

## Future Enhancements

To provide full i18n support, future work could include:

1. **Dynamic Component Generation**: Restructure apps to generate Gradio components dynamically based on selected language
2. **Module HTML Translation**: Extract all HTML content into translatable strings
3. **Button Label Translation**: Generate buttons dynamically with translated labels
4. **Loading Screen Translation**: Make loading overlays respect language selection
5. **Additional Languages**: Add more language options (French, German, etc.)

## Maintainers

When adding new text to the apps, please:

1. Add English text to `TRANSLATIONS["en"]`
2. Add Spanish translation to `TRANSLATIONS["es"]`
3. Add Catalan translation to `TRANSLATIONS["ca"]`
4. For quiz questions, update all three quiz configs (QUIZ_CONFIG, QUIZ_CONFIG_ES, QUIZ_CONFIG_CA)
5. Use the `t(lang, key)` helper function to retrieve translated text in code

## References

- **Ethical Revelation App**: `/aimodelshare/moral_compass/apps/ethical_revelation.py` - Original i18n implementation pattern
- **Bias Detective Part 1**: `/aimodelshare/moral_compass/apps/bias_detective_part1.py`
- **Bias Detective Part 2**: `/aimodelshare/moral_compass/apps/bias_detective_part2.py`
