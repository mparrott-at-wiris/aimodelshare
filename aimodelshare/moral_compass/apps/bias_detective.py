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
"""
import contextlib
import os
import random


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

    # Track state
    framework_score = {"value": 0}
    identified_issues = {"demographics": [], "biases": []}
    moral_compass_points = {"value": 0}

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
            summary = f"✓ Found demographic variables: {', '.join(found)}\n\n"
            summary += "⚠️ **Warning:** These variables can encode bias in AI predictions.\n\n"
            summary += "\n".join(charts)
            summary += f"\n\n🏆 +50 Moral Compass points for identifying potential bias sources!"
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
        report += "🏆 +100 Moral Compass points for identifying bias patterns!"
        
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
        
        # Moral Compass indicator
        moral_compass_display = gr.Markdown("## 🧭 Moral Compass Score: 0 points")
        
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
            
            check_btn.click(
                fn=check_framework_answer,
                inputs=[principle_choice, indicator_choice, observable_choice],
                outputs=framework_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
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
            
            scan_btn.click(
                fn=scan_demographics,
                inputs=[race_toggle, gender_toggle, age_toggle],
                outputs=demographics_output
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
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
                """
            )
            
            analyze_btn = gr.Button("Analyze Fairness Metrics", variant="primary")
            bias_analysis_output = gr.Markdown("")
            
            analyze_btn.click(
                fn=analyze_bias,
                outputs=bias_analysis_output
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
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
    server_name: str = "127.0.0.1",
    server_port: int = 7860,
    theme_primary_hue: str = "indigo"
) -> None:
    """Convenience wrapper to create and launch the bias detective app inline."""
    app = create_bias_detective_app(theme_primary_hue=theme_primary_hue)
    app.launch(share=share, server_name=server_name, server_port=server_port)
