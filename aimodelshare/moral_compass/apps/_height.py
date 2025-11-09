"""
Height estimation utility for Gradio apps in notebook environments.

This module provides utilities for estimating the appropriate iframe height
for Gradio apps when running in notebook environments like Colab.
"""


def estimate_height(
    num_sections: int = 3,
    has_interactive_elements: bool = True,
    base_height: int = 800
) -> int:
    """
    Estimate an appropriate iframe height for a Gradio app.
    
    This is a simple heuristic that can be refined based on actual content.
    Future improvements could analyze the actual Gradio Blocks structure.
    
    Args:
        num_sections: Number of major sections or steps in the app.
        has_interactive_elements: Whether the app has sliders, buttons, etc.
        base_height: Base height to start from (in pixels).
    
    Returns:
        int: Estimated height in pixels.
    """
    height = base_height
    
    # Add height for additional sections
    if num_sections > 3:
        height += (num_sections - 3) * 150
    
    # Add height for interactive elements
    if has_interactive_elements:
        height += 150
    
    # Cap at a reasonable maximum
    return min(height, 1400)
