import gradio as gr
from aimodelshare.moral_compass.apps import (
    launch_tutorial_app,
    launch_judge_app,
    launch_what_is_ai_app
)

def test_launch_tutorial():
    launch_tutorial_app(height=600, share=False, debug=False)

def test_launch_judge():
    launch_judge_app(height=600, share=False, debug=False)

def test_launch_what_is_ai():
    launch_what_is_ai_app(height=600, share=False, debug=False)
