"""
Activity 7: Bias Detective - Gradio application for the Justice & Equity Challenge.

This app teaches:
1. How to diagnose where and how bias appears in AI models
2. Expert fairness principles (OEIAC framework)
3. Identifying demographic data in datasets
4. Analyzing group-level bias with fairness metrics

Structure:
- Factory function `create_bias_detective_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_bias_detective_app()` launches it inline (for notebooks)

Moral Compass Integration:
- Uses ChallengeManager for progress tracking (tasks A-C)
- Task A: Framework understanding
- Task B: Demographics identification
- Task C: Bias analysis
- Debounced sync with Force Sync option
"""
import contextlib
import os
import random
import logging

# Import moral compass integration helpers
from .mc_integration_helpers import (
    get_challenge_manager,
    sync_user_moral_state,
    sync_team_state,
    build_moral_leaderboard_html,
    get_moral_compass_widget_html,
)

logger = logging.getLogger("aimodelshare.moral_compass.apps.bias_detective")


def _get_compas_demographic_data():
    """Generate demographic distribution from COMPAS-like dataset."""
    # Simulated demographic distributions based on real COMPAS data patterns
    demographics = {
        "race": {
            "African-American": 3175,
            "Caucasian": 2103,
            "Hispanic": 509,
            "Other": 343,
            "Asian": 31,
            "Native American": 11
        },
        "gender": {
            "Male": 4997,
            "Female": 1175
        },
        "age": {
            "18-25": 1637,
            "26-35": 2184,
            "36-45": 1453,
            "46+": 898
        }
    }
    return demographics


def _get_fairness_metrics():
    """Generate fairness metrics showing group-level bias."""
    # Simulated fairness metrics showing disparate impact
    metrics = {
        "African-American": {
            "false_positive_rate": 44.9,
            "false_negative_rate": 28.0,
            "sample_size": 3175
        },
        "Caucasian": {
            "false_positive_rate": 23.5,
            "false_negative_rate": 47.7,
            "sample_size": 2103
        },
        "Hispanic": {
            "false_positive_rate": 33.8,
            "false_negative_rate": 35.2,
            "sample_size": 509
        },
        "Other": {
            "false_positive_rate": 29.1,
            "false_negative_rate": 38.5,
            "sample_size": 343
        }
    }
    return metrics


def _get_user_stats():
    """Get user statistics."""
    try:
        username = os.environ.get("username")
        team_name = os.environ.get("TEAM_NAME", "Unknown Team")
        
        return {
            "username": username or "Guest",
            "team_name": team_name,
            "is_signed_in": bool(username)
        }
    except Exception:
        return {
            "username": "Guest",
            "team_name": "Unknown Team",
            "is_signed_in": False
        }


def create_bias_detective_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the Bias Detective Gradio Blocks app (not launched yet)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError(
            "Gradio is required for the bias detective app. Install with `pip install gradio`."
        ) from e

    demographics = _get_compas_demographic_data()
    fairness_metrics = _get_fairness_metrics()

    # Get user stats and initialize challenge manager
    user_stats = _get_user_stats()
    challenge_manager = None
    if user_stats["is_signed_in"]:
        challenge_manager = get_challenge_manager(user_stats["username"])
    
    # Track state
    framework_score = {"value": 0}
    identified_issues = {"demographics": [], "biases": []}
    moral_compass_points = {"value": 0}
    server_moral_score = {"value": None}
    is_synced = {"value": False}

    def sync_moral_state(override=False):
        """Sync moral state to server (debounced unless override)."""
        if not challenge_manager:
            return {
                'widget_html': get_moral_compass_widget_html(
                    local_points=moral_compass_points["value"],
                    server_score=None,
                    is_synced=False
                ),
                'status': 'Guest mode - sign in to sync'
            }
        
        # Sync to server
        sync_result = sync_user_moral_state(
            cm=challenge_manager,
            moral_points=moral_compass_points["value"],
            override=override
        )
        
        # Update state
        if sync_result['synced']:
            server_moral_score["value"] = sync_result.get('server_score')
            is_synced["value"] = True
            
            # Trigger team sync if user sync succeeded
            if user_stats.get("team_name"):
                sync_team_state(user_stats["team_name"])
        
        # Generate widget HTML
        widget_html = get_moral_compass_widget_html(
            local_points=moral_compass_points["value"],
            server_score=server_moral_score["value"],
            is_synced=is_synced["value"]
        )
        
        return {
            'widget_html': widget_html,
            'status': sync_result['message']
        }
    
    def check_framework_answer(principle, indicator, observable):
        """Check if framework components are correctly categorized."""
        correct_mapping = {
            "Equal Treatment": "Principle",
            "Bias Mitigation": "Indicator",
            "False Positive Rate Disparity": "Observable"
        }
        
        score = 0
        feedback = []
        
        if principle == "Principle":
            score += 1
            feedback.append("✓ Correct! 'Equal Treatment' is a core ethical principle.")
        else:
            feedback.append("✗ 'Equal Treatment' should be categorized as a Principle.")
        
        if indicator == "Indicator":
            score += 1
            feedback.append("✓ Correct! 'Bias Mitigation' is an indicator of justice.")
        else:
            feedback.append("✗ 'Bias Mitigation' should be categorized as an Indicator.")
        
        if observable == "Observable":
            score += 1
            feedback.append("✓ Correct! 'False Positive Rate Disparity' is a measurable observable.")
        else:
            feedback.append("✗ 'False Positive Rate Disparity' should be categorized as an Observable.")
        
        framework_score["value"] = score
        
        if score == 3:
            moral_compass_points["value"] += 100
            feedback.append("\n🎉 Perfect! You've earned 100 Moral Compass points!")
            
            # Update ChallengeManager (Task A: Framework understanding)
            if challenge_manager:
                challenge_manager.complete_task('A')
                challenge_manager.answer_question('A', 'A1', 1)
            
            # Trigger sync
            sync_result = sync_moral_state()
            feedback.append(f"\n{sync_result['status']}")
        
        return "\n".join(feedback)

    def scan_demographics(race_toggle, gender_toggle, age_toggle):
        """Scan dataset for demographic variables."""
        found = []
        charts = []
        
        if race_toggle:
            found.append("Race")
            identified_issues["demographics"].append("race")
            race_data = demographics["race"]
            chart_text = "**Race Distribution:**\n"
            for race, count in race_data.items():
                chart_text += f"- {race}: {count} ({count/sum(race_data.values())*100:.1f}%)\n"
            charts.append(chart_text)
        
        if gender_toggle:
            found.append("Gender")
            identified_issues["demographics"].append("gender")
            gender_data = demographics["gender"]
            chart_text = "**Gender Distribution:**\n"
            for gender, count in gender_data.items():
                chart_text += f"- {gender}: {count} ({count/sum(gender_data.values())*100:.1f}%)\n"
            charts.append(chart_text)
        
        if age_toggle:
            found.append("Age")
            identified_issues["demographics"].append("age")
            age_data = demographics["age"]
            chart_text = "**Age Distribution:**\n"
            for age_range, count in age_data.items():
                chart_text += f"- {age_range}: {count} ({count/sum(age_data.values())*100:.1f}%)\n"
            charts.append(chart_text)
        
        if found:
            moral_compass_points["value"] += 50
            
            # Update ChallengeManager (Task B: Demographics identification)
            if challenge_manager:
                challenge_manager.complete_task('B')
                challenge_manager.answer_question('B', 'B1', 1)
            
            summary = f"✓ Found demographic variables: {', '.join(found)}\n\n"
            summary += "⚠️ **Warning:** These variables can encode bias in AI predictions.\n\n"
            summary += "\n".join(charts)
            summary += f"\n\n🏆 +50 Moral Compass points for identifying potential bias sources!"
            
            # Trigger sync
            sync_result = sync_moral_state()
            summary += f"\n\n{sync_result['status']}"
        else:
            summary = "Select variables to scan the dataset."
        
        return summary

    def analyze_bias():
        """Analyze group-level bias in the model."""
        report = "## Bias Radar: Fairness Metrics by Race\n\n"
        report += "| Group | False Positive Rate | False Negative Rate | Sample Size |\n"
        report += "|-------|---------------------|---------------------|-------------|\n"
        
        max_fpr = 0
        max_fpr_group = ""
        
        for group, metrics in fairness_metrics.items():
            fpr = metrics["false_positive_rate"]
            fnr = metrics["false_negative_rate"]
            size = metrics["sample_size"]
            report += f"| {group} | {fpr}% | {fnr}% | {size} |\n"
            
            if fpr > max_fpr:
                max_fpr = fpr
                max_fpr_group = group
        
        report += f"\n### ⚠️ High-Risk Disparity Detected\n\n"
        report += f"**{max_fpr_group}** defendants face a **{max_fpr:.1f}%** false positive rate, "
        report += f"nearly **{max_fpr/23.5:.1f}x higher** than Caucasian defendants (23.5%).\n\n"
        report += "**Real-world consequence:** This means African-American defendants are wrongly "
        report += "labeled as 'high risk' at nearly twice the rate of other groups, potentially "
        report += "leading to longer sentences or denial of bail.\n\n"
        
        identified_issues["biases"].append("racial_disparity_in_fpr")
        moral_compass_points["value"] += 100
        
        # Update ChallengeManager (Task C: Bias analysis)
        if challenge_manager:
            challenge_manager.complete_task('C')
            challenge_manager.answer_question('C', 'C1', 1)
        
        report += "🏆 +100 Moral Compass points for identifying bias patterns!"
        
        # Trigger sync
        sync_result = sync_moral_state()
        report += f"\n\n{sync_result['status']}"
        
        return report

    def check_bias_question(answer):
        """Check bias identification question."""
        if answer == "African-American defendants - wrongly labeled high risk":
            moral_compass_points["value"] += 50
            return "✓ Correct! African-American defendants suffer disproportionate false positive rates, meaning they are incorrectly predicted to reoffend at higher rates.\n\n🏆 +50 Moral Compass points!"
        else:
            return "✗ Not quite. Look at the false positive rates - which group has the highest rate of being wrongly predicted as high risk?"

    def generate_diagnosis_report():
        """Generate final Bias Detective report."""
        report = "# 🕵️ Bias Detective: Diagnosis Report\n\n"
        report += f"**Moral Compass Score:** {moral_compass_points['value']} points\n\n"
        report += "## Demographics Found:\n"
        
        if identified_issues["demographics"]:
            for demo in identified_issues["demographics"]:
                report += f"- ✓ {demo.title()}\n"
        else:
            report += "- No demographics scanned yet\n"
        
        report += "\n## Bias Patterns Discovered:\n"
        
        if identified_issues["biases"]:
            report += "- ✓ Racial disparity in false positive rates\n"
            report += "- ✓ African-American defendants disproportionately affected\n"
        else:
            report += "- No bias analysis completed yet\n"
        
        report += "\n## Principle(s) Invoked:\n"
        report += "- Justice & Equity\n"
        report += "- Equal Treatment under the law\n"
        report += "- Bias Mitigation\n\n"
        
        report += "**Status:** Ready to proceed to Activity 8 - Fairness Fixer\n"
        
        return report

    # Create the Gradio app
    with gr.Blocks(
        title="Activity 7: Bias Detective",
        theme=gr.themes.Soft(primary_hue=theme_primary_hue)
    ) as app:
        gr.Markdown("# 🕵️ Activity 7: Bias Detective")
        gr.Markdown(
            """
            **Objective:** Diagnose where and how bias appears in the AI model using expert fairness principles.
            
            **Your Role:** You've joined the **AI Ethics Task Force** as a **Bias Detective**.
            
            **Estimated Time:** 8–12 minutes
            """
        )
        
        # Moral Compass widget with Force Sync
        with gr.Row():
            with gr.Column(scale=3):
                moral_compass_display = gr.HTML(
                    get_moral_compass_widget_html(
                        local_points=0,
                        server_score=None,
                        is_synced=False
                    )
                )
            with gr.Column(scale=1):
                force_sync_btn = gr.Button("Force Sync", variant="secondary", size="sm")
                sync_status = gr.Markdown("")
        
        # Force Sync handler
        def handle_force_sync():
            sync_result = sync_moral_state(override=True)
            return sync_result['widget_html'], sync_result['status']
        
        force_sync_btn.click(
            fn=handle_force_sync,
            outputs=[moral_compass_display, sync_status]
        )
        
        # Section 7.2: Expert Framework Overview
        with gr.Tab("7.2 Expert Framework"):
            gr.Markdown(
                """
                ## Understanding the OEIAC Framework
                
                The **OEIAC (Observatori d'Ètica en Intel·ligència Artificial de Catalunya)** 
                framework helps us evaluate AI systems through three levels:
                
                ### 🎯 Principles
                Core ethical values (e.g., **Justice & Equity**, **Equal Treatment**)
                
                ### 📊 Indicators
                Measurable signs of ethical behavior (e.g., **Bias Mitigation**, **Fairness**)
                
                ### 🔬 Observables
                Specific metrics we can measure (e.g., **False Positive Rate Disparity**)
                
                ---
                
                ### Interactive Exercise: Framework Builder
                
                Categorize these examples correctly:
                """
            )
            
            principle_choice = gr.Radio(
                choices=["Principle", "Indicator", "Observable"],
                label="'Equal Treatment' is a:",
                value=None
            )
            indicator_choice = gr.Radio(
                choices=["Principle", "Indicator", "Observable"],
                label="'Bias Mitigation' is a:",
                value=None
            )
            observable_choice = gr.Radio(
                choices=["Principle", "Indicator", "Observable"],
                label="'False Positive Rate Disparity' is a:",
                value=None
            )
            
            check_btn = gr.Button("Check My Answers", variant="primary")
            framework_feedback = gr.Markdown("")
            
            def update_widget_after_framework(principle, indicator, observable):
                feedback = check_framework_answer(principle, indicator, observable)
                widget_html = get_moral_compass_widget_html(
                    local_points=moral_compass_points["value"],
                    server_score=server_moral_score["value"],
                    is_synced=is_synced["value"]
                )
                return feedback, widget_html
            
            check_btn.click(
                fn=update_widget_after_framework,
                inputs=[principle_choice, indicator_choice, observable_choice],
                outputs=[framework_feedback, moral_compass_display]
            )
        
        # Section 7.3: Identify Demographic Data
        with gr.Tab("7.3 Demographics Scanner"):
            gr.Markdown(
                """
                ## Dataset Demographics Scanner
                
                ⚠️ **Warning:** Demographic variables can encode bias in AI predictions.
                
                Use the toggles below to scan the dataset for sensitive demographic attributes:
                """
            )
            
            race_toggle = gr.Checkbox(label="Scan for Race", value=False)
            gender_toggle = gr.Checkbox(label="Scan for Gender", value=False)
            age_toggle = gr.Checkbox(label="Scan for Age", value=False)
            
            scan_btn = gr.Button("Run Demographics Scan", variant="primary")
            demographics_output = gr.Markdown("")
            
            def update_widget_after_scan(race, gender, age):
                output = scan_demographics(race, gender, age)
                widget_html = get_moral_compass_widget_html(
                    local_points=moral_compass_points["value"],
                    server_score=server_moral_score["value"],
                    is_synced=is_synced["value"]
                )
                return output, widget_html
            
            scan_btn.click(
                fn=update_widget_after_scan,
                inputs=[race_toggle, gender_toggle, age_toggle],
                outputs=[demographics_output, moral_compass_display]
            )
            
            gr.Markdown("### Check-In Question")
            demo_question = gr.Radio(
                choices=[
                    "They help the model make better predictions",
                    "They can lead to unfair treatment of certain groups",
                    "They are required by law",
                    "They have no effect on model outcomes"
                ],
                label="Why are demographic variables concerning in AI models?",
                value=None
            )
            demo_check_btn = gr.Button("Check Answer")
            demo_feedback = gr.Markdown("")
            
            def check_demo_question(answer):
                if answer == "They can lead to unfair treatment of certain groups":
                    moral_compass_points["value"] += 25
                    return "✓ Correct! Demographic variables can perpetuate historical biases and lead to discriminatory outcomes.\n\n🏆 +25 Moral Compass points!"
                else:
                    return "✗ Not quite. Think about how using race or gender in predictions might affect different groups."
            
            demo_check_btn.click(
                fn=check_demo_question,
                inputs=demo_question,
                outputs=demo_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
        
        # Section 7.4: Analyze Group-Level Bias
        with gr.Tab("7.4 Bias Radar"):
            gr.Markdown(
                """
                ## Bias Radar Visualization
                
                Now let's analyze **disparities in error rates** across demographic groups.
                
                **Key Concepts:**
                - **False Positive Rate:** How often the model wrongly predicts someone will reoffend
                - **False Negative Rate:** How often the model wrongly predicts someone won't reoffend
                
                These errors have serious real-world consequences in criminal justice decisions.
                
                ### 📊 Understanding False Positives via Confusion Matrix
                
                <details>
                <summary><b>Click to expand: Example Confusion Matrix by Race</b></summary>
                
                **African-American Defendants (n=3,175):**
                ```
                                Predicted: Low Risk  |  Predicted: High Risk
                ----------------------------------------------------------------
                Actually Safe        805 (TN)       |      1,425 (FP ⚠️)
                Actually Risky       890 (FN)       |        55 (TP)
                ```
                
                **Caucasian Defendants (n=2,103):**
                ```
                                Predicted: Low Risk  |  Predicted: High Risk
                ----------------------------------------------------------------
                Actually Safe      1,210 (TN)       |       494 (FP)
                Actually Risky       203 (FN)       |       196 (TP)
                ```
                
                **Key Finding:** 
                - African-American FP rate: 1,425 / (805 + 1,425) = **63.9%** wrongly flagged
                - Caucasian FP rate: 494 / (1,210 + 494) = **28.9%** wrongly flagged
                - **Disparity: 2.2x higher** for African-American defendants
                
                **Real-world impact of False Positives:**
                - Denied bail → pretrial detention
                - Longer sentences recommended
                - Family/job disruption while innocent person detained
                
                </details>
                
                ---
                """
            )
            
            analyze_btn = gr.Button("Analyze Fairness Metrics", variant="primary")
            bias_analysis_output = gr.Markdown("")
            
            def update_widget_after_analysis():
                output = analyze_bias()
                widget_html = get_moral_compass_widget_html(
                    local_points=moral_compass_points["value"],
                    server_score=server_moral_score["value"],
                    is_synced=is_synced["value"]
                )
                return output, widget_html
            
            analyze_btn.click(
                fn=update_widget_after_analysis,
                outputs=[bias_analysis_output, moral_compass_display]
            )
            
            gr.Markdown("### Check-In Question")
            bias_question = gr.Radio(
                choices=[
                    "Caucasian defendants - wrongly labeled low risk",
                    "African-American defendants - wrongly labeled high risk",
                    "Hispanic defendants - correctly labeled high risk",
                    "All groups are treated equally"
                ],
                label="Which group is most harmed by this model's bias?",
                value=None
            )
            bias_check_btn = gr.Button("Check Answer")
            bias_feedback = gr.Markdown("")
            
            bias_check_btn.click(
                fn=check_bias_question,
                inputs=bias_question,
                outputs=bias_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
        
        # Ethics Leaderboard Tab
        with gr.Tab("Ethics Leaderboard"):
            gr.Markdown(
                """
                ## 🏆 Ethics Leaderboard
                
                This leaderboard shows **combined ethical engagement + performance scores**.
                
                **What's measured:**
                - Moral compass points (bias detection skills)
                - Model accuracy (technical performance)
                - Combined score = accuracy × normalized_moral_points
                
                **Why this matters:**
                Being good at building models isn't enough - we must also understand fairness and bias!
                """
            )
            
            leaderboard_display = gr.HTML("")
            refresh_leaderboard_btn = gr.Button("Refresh Leaderboard", variant="secondary")
            
            def load_leaderboard():
                return build_moral_leaderboard_html(
                    highlight_username=user_stats.get("username"),
                    include_teams=True
                )
            
            refresh_leaderboard_btn.click(
                fn=load_leaderboard,
                outputs=leaderboard_display
            )
            
            # Load initially
            app.load(fn=load_leaderboard, outputs=leaderboard_display)
        
        # Section 7.5: Completion
        with gr.Tab("7.5 Diagnosis Report"):
            gr.Markdown(
                """
                ## Generate Your Bias Detective Report
                
                Review your findings and generate a comprehensive diagnosis report.
                """
            )
            
            report_btn = gr.Button("Generate Diagnosis Report", variant="primary")
            report_output = gr.Markdown("")
            
            report_btn.click(
                fn=generate_diagnosis_report,
                outputs=report_output
            )
            
            gr.Markdown(
                """
                ---
                
                ### 🎉 Activity 7 Complete!
                
                **Next Step:** Proceed to **Activity 8: Fairness Fixer** to apply hands-on fairness fixes.
                """
            )

    return app


def launch_bias_detective_app(
    share: bool = False,
    server_name: str = None,
    server_port: int = None,
    theme_primary_hue: str = "indigo"
) -> None:
    """Convenience wrapper to create and launch the bias detective app inline."""
    app = create_bias_detective_app(theme_primary_hue=theme_primary_hue)
    # Use provided values or fall back to PORT env var and 0.0.0.0

    if server_port is None:
        server_port = int(os.environ.get("PORT", 8080))
    app.launch(share=share, server_port=server_port)

launch_bias_detective_app()
