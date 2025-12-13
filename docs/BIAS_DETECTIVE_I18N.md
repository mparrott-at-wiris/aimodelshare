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
6. **Dynamic Loading Screens**: `get_loading_screen_html(lang)` and `get_nav_loading_html(lang)` generate translated loading screens
7. **Dynamic Button Labels**: `get_button_label(lang, type)` and `get_button_updates(lang)` generate translated button labels
8. **Module HTML Framework**: `get_module_html(module_id, lang)` provides framework for translatable module content

### What Is Translated

#### ✅ Fully Translated Elements:

- **Quiz Questions** (9-10 quizzes per app)
  - Question text
  - All answer options
  - Success messages for correct answers
  - Feedback messages for incorrect answers

- **Loading Screens**
  - Initial authentication screen
  - Navigation loading overlay
  - All loading messages

- **Navigation Buttons**
  - Previous buttons ("⬅️ Previous" / "⬅️ Anterior" / "⬅️ Anterior")
  - Next buttons ("Next ▶️" / "Siguiente ▶️" / "Següent ▶️")
  - Completion messages

- **UI Messages**
  - Authentication messages  
  - Error messages

- **Dashboard Labels** (defined for future use)
  - Score labels
  - Rank labels
  - Progress indicators

#### 🔄 Framework Ready (Translation TODO):

- **Module HTML Content**: Framework implemented via `get_module_html(module_id, lang)` function
  - To translate a module, create a module-specific HTML generation function (e.g., `get_module_0_html(lang)`)
  - Add translation keys to TRANSLATIONS dictionary
  - Update `get_module_html()` to call the module-specific function
  - See example pattern in code comments

- **Slide Titles**: Can be added to TRANSLATIONS and used in module HTML generation

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

def get_loading_screen_html(lang: str = "en") -> str:
    """Generate loading screen HTML with translated text."""
    return f"""<div>...</div>"""

def get_button_label(lang: str, button_type: str, is_last: bool = False) -> str:
    """Get translated button label based on type."""
    # Returns appropriate translated label

def get_module_html(module_id: int, lang: str = "en") -> str:
    """Get module HTML content with translations (framework for future expansion)."""
    # Framework for module HTML translation
    # To implement: create module-specific HTML generation functions
```

## Translation Coverage

### Bias Detective Part 1
- **Quiz Questions**: 9 quizzes fully translated (quiz IDs: 0, 1, 2, 3, 4, 5, 7, 8, 9, 10)
- **Loading Screens**: Fully translated (2 screens)
- **Navigation Buttons**: Fully translated (22 buttons - 11 modules × 2 buttons)
- **UI Strings**: ~15 translated keys
- **Total Translation Strings**: ~145 per language (435 total)

### Bias Detective Part 2
- **Quiz Questions**: 9 quizzes fully translated (quiz IDs: 1-9)
- **Loading Screens**: Fully translated (2 screens)
- **Navigation Buttons**: Fully translated (20 buttons - 10 modules × 2 buttons)
- **UI Strings**: ~12 translated keys
- **Total Translation Strings**: ~135 per language (405 total)

### Combined
- **Total Translations**: ~280 strings per language
- **Total Across 3 Languages**: ~840 translated strings

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
   - Dynamic loading screen generation
   - Dynamic button label updates
   - Module HTML translation framework

3. **Code Review**: No issues found
4. **Security Scan**: No security vulnerabilities detected

## How Module HTML Translation Works

### Current Implementation
Module HTML content is stored in the `MODULES` list with static English HTML. The `get_module_html(module_id, lang)` function provides a framework for returning translated HTML.

### To Translate a Module

1. **Add translation keys** to TRANSLATIONS dictionary:
```python
TRANSLATIONS = {
    "en": {
        "module_0_title": "🧭 Introducing Your New Moral Compass Score",
        "module_0_intro_p1": "Right now, your model is judged...",
        # ... more keys
    },
    "es": {
        "module_0_title": "🧭 Presentamos tu Nueva Puntuación de Brúixola Moral",
        "module_0_intro_p1": "Ahora mismo, tu modelo se juzga...",
        # ... more keys
    },
    "ca": {
        "module_0_title": "🧭 Presentem la teva Nova Puntuació de Brúixola Moral",
        "module_0_intro_p1": "Ara mateix, el teu model es jutja...",
        # ... more keys
    }
}
```

2. **Create module-specific HTML generation function**:
```python
def get_module_0_html(lang: str) -> str:
    """Generate Module 0 HTML with translations."""
    return f"""
        <div class="scenario-box">
            <h2 class="slide-title">{t(lang, 'module_0_title')}</h2>
            <div class="slide-body">
                <p>{t(lang, 'module_0_intro_p1')}</p>
                <!-- ... more translated content -->
            </div>
        </div>
    """
```

3. **Update get_module_html()** to use the new function:
```python
def get_module_html(module_id: int, lang: str = "en") -> str:
    if module_id == 0:
        return get_module_0_html(lang)
    # ... more modules
    
    # Fallback to original English HTML
    for mod in MODULES:
        if mod["id"] == module_id:
            return mod["html"]
    return ""
```

4. **Update module rendering** to use `get_module_html()`:
```python
# In the module generation loop:
gr.HTML(get_module_html(i, lang))  # Instead of: gr.HTML(mod["html"])
```

### Note on Scope
Given that modules contain ~158,000 characters of HTML content across both apps, full translation of all module HTML would require significant effort. The framework is in place to enable incremental translation of modules as needed.

## Future Enhancements

To provide complete i18n coverage, future work could include:

1. **Module HTML Translation**: Translate remaining module HTML content
   - 11 modules in Part 1 (~64K characters)
   - 10 modules in Part 2 (~94K characters)
   - Use the `get_module_html()` framework demonstrated above

2. **Additional Languages**: Add more language options (French, German, etc.)

3. **Dynamic Component Generation**: Restructure to generate all components based on language from the start

## Maintainers

When adding new text to the apps, please:

1. Add English text to `TRANSLATIONS["en"]`
2. Add Spanish translation to `TRANSLATIONS["es"]`
3. Add Catalan translation to `TRANSLATIONS["ca"]`
4. For quiz questions, update all three quiz configs (QUIZ_CONFIG, QUIZ_CONFIG_ES, QUIZ_CONFIG_CA)
5. For module HTML, follow the pattern in "How Module HTML Translation Works" section above
6. Use the helper functions (`t()`, `get_quiz_config()`, `get_module_html()`) to retrieve translated text

## References

- **Ethical Revelation App**: `/aimodelshare/moral_compass/apps/ethical_revelation.py` - Original i18n implementation pattern
- **Bias Detective Part 1**: `/aimodelshare/moral_compass/apps/bias_detective_part1.py`
- **Bias Detective Part 2**: `/aimodelshare/moral_compass/apps/bias_detective_part2.py`
