"""
Activity 8: Fairness Fixer - Gradio application for the Justice & Equity Challenge.

This app teaches:
1. How to remove biased features (direct demographics)
2. Identifying and removing proxy variables
3. Developing representative and continuously improving data strategies
4. Building ethical roadmaps for responsible AI

Structure:
- Factory function `create_fairness_fixer_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_fairness_fixer_app()` launches it inline (for notebooks)

Moral Compass Integration:
- Uses ChallengeManager for progress tracking (tasks D-E)
- Task D: Feature removal and proxy identification
- Task E: Representative data and improvement planning
- Debounced sync with Force Sync option
"""
import contextlib
import os
import logging

# Import moral compass integration helpers
from .mc_integration_helpers import (
    get_challenge_manager,
    sync_user_moral_state,
    sync_team_state,
    build_moral_leaderboard_html,
    get_moral_compass_widget_html,
)

logger = logging.getLogger("aimodelshare.moral_compass.apps.fairness_fixer")


def _get_initial_metrics():
    """Get initial fairness metrics before fixes."""
    return {
        "accuracy": 67.2,
        "false_positive_rate": {
            "African-American": 44.9,
            "Caucasian": 23.5,
            "Overall": 34.2
        },
        "false_negative_rate": {
            "African-American": 28.0,
            "Caucasian": 47.7,
            "Overall": 37.9
        }
    }


def _get_post_demographic_removal_metrics():
    """Get metrics after removing direct demographics."""
    return {
        "accuracy": 64.8,  # Slight accuracy drop
        "false_positive_rate": {
            "African-American": 38.2,
            "Caucasian": 26.1,
            "Overall": 32.2
        },
        "false_negative_rate": {
            "African-American": 34.5,
            "Caucasian": 43.2,
            "Overall": 38.9
        }
    }


def _get_post_proxy_removal_metrics():
    """Get metrics after removing proxy variables."""
    return {
        "accuracy": 62.1,  # Further accuracy drop, but more fair
        "false_positive_rate": {
            "African-American": 31.8,
            "Caucasian": 28.4,
            "Overall": 30.1
        },
        "false_negative_rate": {
            "African-American": 39.2,
            "Caucasian": 41.6,
            "Overall": 40.4
        }
    }


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


def create_fairness_fixer_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the Fairness Fixer Gradio Blocks app (not launched yet)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError(
            "Gradio is required for the fairness fixer app. Install with `pip install gradio`."
        ) from e

    initial_metrics = _get_initial_metrics()
    
    # Get user stats and initialize challenge manager
    user_stats = _get_user_stats()
    challenge_manager = None
    if user_stats["is_signed_in"]:
        challenge_manager = get_challenge_manager(user_stats["username"])
    
    # Track state
    moral_compass_points = {"value": 0}
    server_moral_score = {"value": None}
    is_synced = {"value": False}
    features_removed = []
    proxy_fixes_applied = []

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
    
    def remove_demographics():
        """Remove direct demographic features and show impact."""
        features_removed.extend(["race", "sex", "age"])
        moral_compass_points["value"] += 100
        
        # Update ChallengeManager (Task D: Remove demographics)
        if challenge_manager:
            challenge_manager.complete_task('D')
            challenge_manager.answer_question('D', 'D1', 1)
        
        before = initial_metrics
        after = _get_post_demographic_removal_metrics()
        
        report = "## Before/After: Removing Direct Demographics\n\n"
        report += "### Overall Metrics\n"
        report += f"| Metric | Before | After | Change |\n"
        report += f"|--------|--------|-------|--------|\n"
        report += f"| Accuracy | {before['accuracy']}% | {after['accuracy']}% | {after['accuracy'] - before['accuracy']:.1f}% |\n\n"
        
        report += "### False Positive Rates (wrongly labeled as high risk)\n"
        report += f"| Group | Before | After | Improvement |\n"
        report += f"|-------|--------|-------|-------------|\n"
        report += f"| African-American | {before['false_positive_rate']['African-American']}% | {after['false_positive_rate']['African-American']}% | {before['false_positive_rate']['African-American'] - after['false_positive_rate']['African-American']:.1f}% |\n"
        report += f"| Caucasian | {before['false_positive_rate']['Caucasian']}% | {after['false_positive_rate']['Caucasian']}% | {after['false_positive_rate']['Caucasian'] - before['false_positive_rate']['Caucasian']:.1f}% |\n\n"
        
        report += "### 📊 Key Findings:\n"
        report += "- ✓ False positive rate disparity **reduced from 21.4% to 12.1%**\n"
        report += "- ⚠️ Overall accuracy decreased by 2.4%\n"
        report += "- ✓ Model is now more equitable across racial groups\n\n"
        report += "**Trade-off Note:** We accept a small accuracy decrease to achieve greater fairness.\n\n"
        report += "🏆 +100 Moral Compass points for removing biased features!"
        
        # Trigger sync
        sync_result = sync_moral_state()
        report += f"\n\n{sync_result['status']}"
        
        return report

    def check_first_step_question(answer):
        """Check the first step question."""
        if answer == "Remove demographic attributes like race and gender":
            moral_compass_points["value"] += 50
            return "✓ Correct! The first step in fairness is removing direct demographic attributes that can cause discriminatory predictions.\n\n🏆 +50 Moral Compass points!"
        else:
            return "✗ Not quite. Think about which variables directly encode protected characteristics."

    def rank_proxy_variables(neighborhood_rank, income_rank, priors_rank):
        """Check proxy variable ranking."""
        correct_ranking = {
            "Neighborhood ZIP code": "1",
            "Prior arrests (count)": "2",
            "Income level": "3"
        }
        
        score = 0
        feedback = []
        
        if neighborhood_rank == "1":
            score += 1
            feedback.append("✓ Correct! Neighborhood is the strongest proxy for race due to residential segregation.")
        else:
            feedback.append("✗ Neighborhood ZIP code is actually the #1 proxy due to residential segregation.")
        
        if priors_rank == "2":
            score += 1
            feedback.append("✓ Correct! Prior arrests reflect historical bias in policing patterns.")
        else:
            feedback.append("✗ Prior arrests is the #2 proxy, reflecting historical policing bias.")
        
        if income_rank == "3":
            score += 1
            feedback.append("✓ Correct! Income correlates with race but is less direct than ZIP code.")
        else:
            feedback.append("✗ Income level is the #3 proxy, less direct than neighborhood.")
        
        if score == 3:
            moral_compass_points["value"] += 100
            feedback.append("\n🎉 Perfect! You understand proxy variables!\n🏆 +100 Moral Compass points!")
        elif score >= 2:
            moral_compass_points["value"] += 50
            feedback.append("\n🏆 +50 Moral Compass points for good understanding!")
        
        return "\n".join(feedback)

    def remove_proxy_variables():
        """Remove proxy variables and reanalyze."""
        proxy_fixes_applied.extend(["neighborhood", "prior_arrests_count", "income"])
        moral_compass_points["value"] += 100
        
        # Update ChallengeManager (continuing Task D: Remove proxies)
        if challenge_manager:
            challenge_manager.answer_question('D', 'D2', 1)
        
        before = _get_post_demographic_removal_metrics()
        after = _get_post_proxy_removal_metrics()
        
        report = "## Impact of Removing Proxy Variables\n\n"
        report += "**Removed:** Neighborhood ZIP code, Prior arrests count, Income level\n\n"
        report += "### False Positive Rate Disparity\n"
        report += f"| Metric | After Demographics Removed | After Proxies Removed | Improvement |\n"
        report += f"|--------|---------------------------|----------------------|-------------|\n"
        report += f"| African-American FPR | {before['false_positive_rate']['African-American']}% | {after['false_positive_rate']['African-American']}% | {before['false_positive_rate']['African-American'] - after['false_positive_rate']['African-American']:.1f}% |\n"
        report += f"| Caucasian FPR | {before['false_positive_rate']['Caucasian']}% | {after['false_positive_rate']['Caucasian']}% | {after['false_positive_rate']['Caucasian'] - before['false_positive_rate']['Caucasian']:.1f}% |\n"
        report += f"| Disparity | {before['false_positive_rate']['African-American'] - before['false_positive_rate']['Caucasian']:.1f}% | {after['false_positive_rate']['African-American'] - after['false_positive_rate']['Caucasian']:.1f}% | {(before['false_positive_rate']['African-American'] - before['false_positive_rate']['Caucasian']) - (after['false_positive_rate']['African-American'] - after['false_positive_rate']['Caucasian']):.1f}% |\n\n"
        
        report += "### 📊 Key Findings:\n"
        report += "- ✓ Disparity further reduced from 12.1% to **3.4%** - nearly equalized!\n"
        report += "- ⚠️ Accuracy decreased to 62.1% (from 64.8%)\n"
        report += "- ✓ **Model now treats groups much more fairly**\n\n"
        report += "**Important:** Removing proxies prevents indirect discrimination through correlated variables.\n\n"
        report += "🏆 +100 Moral Compass points for eliminating proxy bias!"
        
        # Trigger sync
        sync_result = sync_moral_state()
        report += f"\n\n{sync_result['status']}"
        
        return report

    def check_proxy_question(answer):
        """Check proxy identification question."""
        if answer == "ZIP code in a city with segregated neighborhoods":
            moral_compass_points["value"] += 50
            return "✓ Correct! ZIP codes can serve as a strong proxy for race in segregated areas, reintroducing bias even after removing race explicitly.\n\n🏆 +50 Moral Compass points!"
        else:
            return "✗ Not quite. Think about which variable most closely correlates with protected attributes in real-world settings."

    def generate_data_guidelines():
        """Generate representative data guidelines."""
        moral_compass_points["value"] += 75
        
        # Update ChallengeManager (Task E: Representative data)
        if challenge_manager:
            challenge_manager.complete_task('E')
            challenge_manager.answer_question('E', 'E1', 1)
        
        guidelines = """
## 📋 Representative Data Guidelines

Based on expert consensus between data scientists, judges, and community members:

### 1. Population Matching
- ✓ Training data must reflect the demographics of the population where the model will be deployed
- ✓ Include all subgroups that will be affected by model predictions
- ✗ Avoid over-sampling from convenient but unrepresentative sources

### 2. Geographic Balance
- ✓ Collect data from multiple jurisdictions (urban, suburban, rural)
- ✓ Ensure regional representation matches deployment scope
- ✗ Don't rely solely on data from a single city or region

### 3. Temporal Relevance
- ✓ Use recent data that reflects current social conditions
- ✓ Regularly update training data as society evolves
- ✗ Avoid relying on outdated data from different legal/social contexts

### 4. Outcome Diversity
- ✓ Include both positive and negative outcomes for all groups
- ✓ Balance historical bias in outcome labels when possible
- ✗ Don't perpetuate historical discrimination patterns

### 5. Community Input
- ✓ Consult with affected communities about data collection
- ✓ Incorporate local knowledge about relevant features
- ✗ Don't make assumptions without stakeholder input

🏆 +75 Moral Compass points for developing data guidelines!
"""
        # Trigger sync
        sync_result = sync_moral_state()
        guidelines += f"\n\n{sync_result['status']}"
        
        return guidelines

    def check_representative_data_question(answer):
        """Check representative data question."""
        if answer == "Training data that mirrors the demographics and conditions of the target population":
            moral_compass_points["value"] += 25
            return "✓ Correct! Representative data accurately reflects the population where the model will be used.\n\n🏆 +25 Moral Compass points!"
        else:
            return "✗ Not quite. Representative data should match the target deployment population."

    def check_geographic_question(answer):
        """Check geographic mismatch question."""
        if answer == "No - the model may not generalize well to different geographic contexts":
            moral_compass_points["value"] += 25
            return "✓ Correct! Models trained in one region may not work fairly or accurately in areas with different demographics and social conditions.\n\n🏆 +25 Moral Compass points!"
        else:
            return "✗ Not quite. Consider how regional differences might affect model performance and fairness."

    def build_improvement_plan(audit_order, doc_order, stakeholder_order):
        """Check if roadmap steps are correctly ordered."""
        score = 0
        feedback = []
        
        if audit_order == "1":
            score += 1
            feedback.append("✓ Correct! Regular auditing should be the first step.")
        else:
            feedback.append("✗ Regular auditing should be step 1 to catch issues early.")
        
        if doc_order == "2":
            score += 1
            feedback.append("✓ Correct! Documentation enables transparency and accountability.")
        else:
            feedback.append("✗ Documentation should be step 2 to ensure transparency.")
        
        if stakeholder_order == "3":
            score += 1
            feedback.append("✓ Correct! Ongoing stakeholder engagement is the final continuous process.")
        else:
            feedback.append("✗ Stakeholder engagement should be step 3 for continuous improvement.")
        
        if score == 3:
            moral_compass_points["value"] += 100
            plan = """
## 🗺️ Continuous Improvement Plan

### Phase 1: Regular Auditing
- ✓ Quarterly fairness metric reviews
- ✓ Automated bias detection systems
- ✓ Disparate impact analysis across all protected groups

### Phase 2: Transparent Documentation
- ✓ Public model cards with fairness metrics
- ✓ Dataset composition reports
- ✓ Decision-making process documentation

### Phase 3: Stakeholder Engagement
- ✓ Community advisory board meetings
- ✓ Feedback mechanisms for affected individuals
- ✓ Regular consultations with advocacy groups

🎉 Perfect roadmap! 🏆 +100 Moral Compass points!
"""
            feedback.append(plan)
        elif score >= 2:
            moral_compass_points["value"] += 50
            feedback.append("\n🏆 +50 Moral Compass points for good understanding!")
        
        return "\n".join(feedback)

    def check_model_card_question(answer):
        """Check model card question."""
        if answer == "Fairness metrics across demographic groups":
            moral_compass_points["value"] += 50
            return "✓ Correct! Judges need to understand how fairly the model treats different groups to make informed decisions about its use.\n\n🏆 +50 Moral Compass points!"
        else:
            return "✗ Not quite. Think about what information would help a judge evaluate whether the model should be used in court."

    def generate_fairness_summary():
        """Generate final fairness fix summary."""
        report = "# 🔧 Fairness Fix Summary\n\n"
        report += f"**Moral Compass Score:** {moral_compass_points['value']} points\n\n"
        
        report += "## Features Removed:\n"
        if features_removed:
            for feature in set(features_removed):
                report += f"- ✓ {feature}\n"
        else:
            report += "- No features removed yet\n"
        
        report += "\n## Proxy Fixes Applied:\n"
        if proxy_fixes_applied:
            for proxy in set(proxy_fixes_applied):
                report += f"- ✓ {proxy}\n"
        else:
            report += "- No proxy fixes applied yet\n"
        
        report += "\n## Fairness Metric Changes:\n"
        initial = _get_initial_metrics()
        final = _get_post_proxy_removal_metrics()
        
        report += f"- False Positive Rate Disparity: {initial['false_positive_rate']['African-American'] - initial['false_positive_rate']['Caucasian']:.1f}% → {final['false_positive_rate']['African-American'] - final['false_positive_rate']['Caucasian']:.1f}%\n"
        report += f"- Overall Accuracy: {initial['accuracy']:.1f}% → {final['accuracy']:.1f}%\n"
        report += f"- **Fairness Improvement:** {((initial['false_positive_rate']['African-American'] - initial['false_positive_rate']['Caucasian']) - (final['false_positive_rate']['African-American'] - final['false_positive_rate']['Caucasian'])):.1f}% reduction in disparity\n"
        
        report += "\n## Ongoing Improvement Plan:\n"
        report += "- ✓ Regular fairness audits (quarterly)\n"
        report += "- ✓ Transparent model documentation\n"
        report += "- ✓ Stakeholder engagement process\n\n"
        
        report += "**Status:** Ready to proceed to Activity 9 - Justice & Equity Upgrade\n"
        
        return report

    # Create the Gradio app
    with gr.Blocks(
        title="Activity 8: Fairness Fixer",
        theme=gr.themes.Soft(primary_hue=theme_primary_hue)
    ) as app:
        gr.Markdown("# 🔧 Activity 8: Fairness Fixer")
        gr.Markdown(
            """
            **Objective:** Apply hands-on fairness fixes: remove biased features, eliminate proxy variables, 
            and develop a representative and continuously improving data strategy.
            
            **Your Role:** You're now a **Fairness Engineer**.
            
            **Progress:** Activity 8 of 10 — Fix the Model
            
            **Estimated Time:** 12–15 minutes
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
        
        # Section 8.2: Remove Direct Demographics
        with gr.Tab("8.2 Remove Demographics"):
            gr.Markdown(
                """
                ## Remove Direct Demographics
                
                **Problem:** Direct demographic attributes (race, sex, age) create unfair predictions 
                because they encode protected characteristics.
                
                **Solution:** Remove these features from the model entirely.
                """
            )
            
            remove_demo_btn = gr.Button("Remove Demographics & Reanalyze", variant="primary")
            demo_removal_output = gr.Markdown("")
            
            remove_demo_btn.click(
                fn=remove_demographics,
                outputs=demo_removal_output
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
            
            gr.Markdown("### Check-In Question")
            first_step_question = gr.Radio(
                choices=[
                    "Increase model accuracy at all costs",
                    "Remove demographic attributes like race and gender",
                    "Collect more data from the majority group",
                    "Use all available features without restriction"
                ],
                label="What should be the first step in making an AI model fairer?",
                value=None
            )
            first_step_btn = gr.Button("Check Answer")
            first_step_feedback = gr.Markdown("")
            
            first_step_btn.click(
                fn=check_first_step_question,
                inputs=first_step_question,
                outputs=first_step_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
        
        # Section 8.3: Identify & Remove Proxies
        with gr.Tab("8.3 Remove Proxies"):
            gr.Markdown(
                """
                ## Identify & Remove Proxy Variables
                
                **Problem:** Even after removing race, other variables can serve as **proxies** that 
                replicate bias. A proxy is a variable that strongly correlates with a protected attribute.
                
                ### 📚 Fairness Metrics: Statistical Parity vs Equal Opportunity
                
                <details>
                <summary><b>Click to expand: Fairness Metric Comparison</b></summary>
                
                **Scenario:** Pretrial risk model predicting recidivism
                
                | Metric | Definition | Example Calculation | Limitation |
                |--------|-----------|---------------------|------------|
                | **Statistical Parity** | Equal positive prediction rates across groups | P(Predicted High Risk \\| African-American) = P(Predicted High Risk \\| Caucasian) | May require unequal treatment of equally risky individuals |
                | **Equal Opportunity** | Equal true positive rates across groups | P(Predicted High Risk \\| Actually Risky, African-American) = P(Predicted High Risk \\| Actually Risky, Caucasian) | Ignores false positive disparity |
                | **Equalized Odds** | Both TPR and FPR equal across groups | Both conditions above must hold | Difficult to achieve simultaneously |
                
                **Numeric Example:**
                
                **Group A (1,000 people, 200 actually risky):**
                - Predicted High Risk: 250 people
                - True Positives: 150 / 200 = **75% TPR**
                - False Positives: 100 / 800 = 12.5% FPR
                
                **Group B (1,000 people, 200 actually risky):**
                - Predicted High Risk: 400 people
                - True Positives: 180 / 200 = **90% TPR** ⚠️ (disparity!)
                - False Positives: 220 / 800 = **27.5% FPR** ⚠️ (disparity!)
                
                **Analysis:** Even though both groups have same base rate (20% risky), Group B is 
                over-predicted, leading to higher both TPR and FPR. Equal Opportunity would require 
                equalizing TPR; Equalized Odds would require equalizing both.
                
                </details>
                
                ---
                
                ### Proxy Identification Mini-Game
                
                Rank these variables by how likely they are to serve as proxies for race (1 = strongest proxy):
                """
            )
            
            neighborhood_rank = gr.Radio(
                choices=["1", "2", "3"],
                label="Neighborhood ZIP code:",
                value=None
            )
            priors_rank = gr.Radio(
                choices=["1", "2", "3"],
                label="Prior arrests (count):",
                value=None
            )
            income_rank = gr.Radio(
                choices=["1", "2", "3"],
                label="Income level:",
                value=None
            )
            
            rank_btn = gr.Button("Check My Ranking", variant="primary")
            rank_feedback = gr.Markdown("")
            
            rank_btn.click(
                fn=rank_proxy_variables,
                inputs=[neighborhood_rank, income_rank, priors_rank],
                outputs=rank_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
            
            gr.Markdown("### Remove Proxy Variables")
            remove_proxy_btn = gr.Button("Remove Proxy Variables & Reanalyze", variant="primary")
            proxy_removal_output = gr.Markdown("")
            
            remove_proxy_btn.click(
                fn=remove_proxy_variables,
                outputs=proxy_removal_output
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
            
            gr.Markdown("### Check-In Question")
            proxy_question = gr.Radio(
                choices=[
                    "Email address format",
                    "ZIP code in a city with segregated neighborhoods",
                    "Browser type",
                    "Time of day of arrest"
                ],
                label="Which feature is most likely to be a proxy for race?",
                value=None
            )
            proxy_check_btn = gr.Button("Check Answer")
            proxy_feedback = gr.Markdown("")
            
            proxy_check_btn.click(
                fn=check_proxy_question,
                inputs=proxy_question,
                outputs=proxy_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
        
        # Section 8.4: Representative Data
        with gr.Tab("8.4 Representative Data"):
            gr.Markdown(
                """
                ## Representative Data Strategy
                
                **Problem:** Models trained on unrepresentative data may not work fairly for all groups.
                
                **Solution:** Ensure training data matches the intended population.
                
                ### Expert Chat: Building Representative Datasets
                
                Below is a conversation between experts discussing data collection best practices:
                """
            )
            
            gr.Markdown(
                """
                ---
                
                **👨‍💻 Data Scientist:** "We have 10,000 records from City A. Can we deploy this model nationwide?"
                
                **👩‍⚖️ Judge:** "City A has unique demographics. What about rural areas? Different regions?"
                
                **👥 Community Member:** "Our neighborhood isn't represented. The model may not understand our context."
                
                **👨‍💻 Data Scientist:** "You're right. We need geographic, demographic, and temporal balance. Let's create guidelines."
                
                ---
                """
            )
            
            guidelines_btn = gr.Button("Generate Representative Data Guidelines", variant="primary")
            guidelines_output = gr.Markdown("")
            
            guidelines_btn.click(
                fn=generate_data_guidelines,
                outputs=guidelines_output
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
            
            gr.Markdown("### Check-In Questions")
            
            rep_data_question = gr.Radio(
                choices=[
                    "Data from any available source",
                    "Training data that mirrors the demographics and conditions of the target population",
                    "The largest dataset available",
                    "Data collected only from cooperative participants"
                ],
                label="What is representative data?",
                value=None
            )
            rep_data_btn = gr.Button("Check Answer")
            rep_data_feedback = gr.Markdown("")
            
            rep_data_btn.click(
                fn=check_representative_data_question,
                inputs=rep_data_question,
                outputs=rep_data_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
            
            geo_question = gr.Radio(
                choices=[
                    "Yes - data is data regardless of source",
                    "No - the model may not generalize well to different geographic contexts",
                    "Yes - as long as the dataset is large enough",
                    "It doesn't matter where data comes from"
                ],
                label="A model trained on urban data from California - can it be fairly deployed in rural Texas?",
                value=None
            )
            geo_btn = gr.Button("Check Answer")
            geo_feedback = gr.Markdown("")
            
            geo_btn.click(
                fn=check_geographic_question,
                inputs=geo_question,
                outputs=geo_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
        
        # Section 8.5: Continuous Improvement Plan
        with gr.Tab("8.5 Improvement Plan"):
            gr.Markdown(
                """
                ## Continuous Improvement Plan
                
                **Goal:** Create an ongoing process for auditing, documentation, and stakeholder engagement.
                
                ### Ethical Roadmap Builder
                
                Put these steps in the correct order (1 = first, 3 = last) for a responsible model lifecycle:
                """
            )
            
            audit_order = gr.Radio(
                choices=["1", "2", "3"],
                label="Regular fairness auditing:",
                value=None
            )
            doc_order = gr.Radio(
                choices=["1", "2", "3"],
                label="Transparent documentation (model cards):",
                value=None
            )
            stakeholder_order = gr.Radio(
                choices=["1", "2", "3"],
                label="Ongoing stakeholder engagement:",
                value=None
            )
            
            roadmap_btn = gr.Button("Build Improvement Plan", variant="primary")
            roadmap_output = gr.Markdown("")
            
            roadmap_btn.click(
                fn=build_improvement_plan,
                inputs=[audit_order, doc_order, stakeholder_order],
                outputs=roadmap_output
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
            
            gr.Markdown("### Check-In Question")
            model_card_question = gr.Radio(
                choices=[
                    "The model's source code",
                    "Fairness metrics across demographic groups",
                    "The names of data scientists who built it",
                    "Hardware requirements"
                ],
                label="What is the most critical information for a judge's model card?",
                value=None
            )
            model_card_btn = gr.Button("Check Answer")
            model_card_feedback = gr.Markdown("")
            
            model_card_btn.click(
                fn=check_model_card_question,
                inputs=model_card_question,
                outputs=model_card_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
        
        # Section 8.6: Completion
        # Ethics Leaderboard Tab
        with gr.Tab("Ethics Leaderboard"):
            gr.Markdown(
                """
                ## 🏆 Ethics Leaderboard
                
                This leaderboard shows **combined ethical engagement + performance scores**.
                
                **What's measured:**
                - Moral compass points (fairness engineering skills)
                - Model accuracy (technical performance)
                - Combined score = accuracy × normalized_moral_points
                
                **Your progress:**
                Track how you compare to others who have also tackled bias and fairness challenges!
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
        
        with gr.Tab("8.6 Fix Summary"):
            gr.Markdown(
                """
                ## Generate Your Fairness Fix Summary
                
                Review all the improvements you've made to the model.
                """
            )
            
            summary_btn = gr.Button("Generate Fix Summary", variant="primary")
            summary_output = gr.Markdown("")
            
            summary_btn.click(
                fn=generate_fairness_summary,
                outputs=summary_output
            )
            
            gr.Markdown(
                """
                ---
                
                ### 🎉 Activity 8 Complete!
                
                **Next Step:** Proceed to **Activity 9: Justice & Equity Upgrade** to elevate your fairness improvements.
                """
            )

    return app


def launch_fairness_fixer_app(
    share: bool = False,
    server_name: str = None,
    server_port: int = None,
    theme_primary_hue: str = "indigo"
) -> None:
    """Convenience wrapper to create and launch the fairness fixer app inline."""
    app = create_fairness_fixer_app(theme_primary_hue=theme_primary_hue)
    # Use provided values or fall back to PORT env var and 0.0.0.0

    if server_port is None:
        server_port = int(os.environ.get("PORT", 8080))
    app.launch(share=share, sserver_port=server_port)
