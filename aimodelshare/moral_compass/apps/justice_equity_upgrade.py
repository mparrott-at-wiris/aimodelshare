"""
Activity 9: Justice & Equity Upgrade - Gradio application for the Justice & Equity Challenge.

This app teaches:
1. Elevating fairness through accessibility and inclusion
2. Stakeholder engagement and community participation
3. Final Moral Compass score reveal and team leaderboard
4. Certificate unlock and challenge completion

Structure:
- Factory function `create_justice_equity_upgrade_app()` returns a Gradio Blocks object
- Convenience wrapper `launch_justice_equity_upgrade_app()` launches it inline (for notebooks)
"""
import contextlib
import os


def _get_user_stats():
    """Get user statistics for final score reveal."""
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


def create_justice_equity_upgrade_app(theme_primary_hue: str = "indigo") -> "gr.Blocks":
    """Create the Justice & Equity Upgrade Gradio Blocks app (not launched yet)."""
    try:
        import gradio as gr
        gr.close_all(verbose=False)
    except ImportError as e:
        raise ImportError(
            "Gradio is required for the justice & equity upgrade app. Install with `pip install gradio`."
        ) from e

    # Track state
    moral_compass_points = {"value": 0}
    accessibility_features = []
    diversity_improvements = []
    stakeholder_priorities = []

    def apply_accessibility_features(multilang, plaintext, screenreader):
        """Apply accessibility features."""
        features_added = []
        
        if multilang:
            features_added.append("Multi-language support (Catalan, Spanish, English)")
            accessibility_features.append("multilang")
        
        if plaintext:
            features_added.append("Plain text summaries for non-technical users")
            accessibility_features.append("plaintext")
        
        if screenreader:
            features_added.append("Screen reader compatibility")
            accessibility_features.append("screenreader")
        
        if features_added:
            moral_compass_points["value"] += 75
            report = "## Accessibility Features Applied\n\n"
            for feature in features_added:
                report += f"- ✓ {feature}\n"
            report += f"\n**Impact:** These features ensure **equal opportunity of access** for all users, "
            report += "regardless of language, technical background, or disability.\n\n"
            report += "🏆 +75 Moral Compass points for improving accessibility!"
        else:
            report = "Select accessibility features to apply."
        
        return report

    def apply_diversity_improvements(team_diversity, community_voices, diverse_review):
        """Apply diversity improvements."""
        improvements = []
        
        if team_diversity:
            improvements.append("Diverse team composition (gender, ethnicity, background)")
            diversity_improvements.append("team_diversity")
        
        if community_voices:
            improvements.append("Community advisory board with affected population representatives")
            diversity_improvements.append("community_voices")
        
        if diverse_review:
            improvements.append("Diverse review panel for model evaluation")
            diversity_improvements.append("diverse_review")
        
        if improvements:
            moral_compass_points["value"] += 100
            report = "## Diversity & Inclusion Improvements\n\n"
            for improvement in improvements:
                report += f"- ✓ {improvement}\n"
            report += f"\n**Impact:** Diverse perspectives help identify blind spots and ensure the "
            report += "system serves all communities fairly.\n\n"
            report += "🏆 +100 Moral Compass points for advancing inclusion!"
        else:
            report = "Select diversity improvements to apply."
        
        return report

    def visualize_improvements():
        """Show before/after comparison."""
        report = """
## Before/After: System-Level Transformation

### Before (Original System)
- ❌ English-only interface
- ❌ Technical jargon throughout
- ❌ No accessibility accommodations
- ❌ Homogeneous development team
- ❌ No community input
- ❌ Decisions made in isolation

### After (Justice & Equity Upgrade)
"""
        
        if "multilang" in accessibility_features:
            report += "- ✅ Multi-language support\n"
        if "plaintext" in accessibility_features:
            report += "- ✅ Plain language explanations\n"
        if "screenreader" in accessibility_features:
            report += "- ✅ Screen reader compatibility\n"
        if "team_diversity" in diversity_improvements:
            report += "- ✅ Diverse development team\n"
        if "community_voices" in diversity_improvements:
            report += "- ✅ Community advisory board\n"
        if "diverse_review" in diversity_improvements:
            report += "- ✅ Inclusive review process\n"
        
        if accessibility_features or diversity_improvements:
            report += "\n**Result:** A more **inclusive, accessible, and just** AI system.\n"
        else:
            report += "\n*Apply accessibility and diversity improvements to see the transformation.*\n"
        
        return report

    def prioritize_stakeholders(judges_pri, defendants_pri, families_pri, community_pri, ngos_pri):
        """Check stakeholder prioritization."""
        scoring = {
            "Defendants": defendants_pri == "Critical",
            "Community Advocates": community_pri == "Critical",
            "Families": families_pri == "High",
            "Judges": judges_pri == "High",
            "NGOs": ngos_pri in ["High", "Medium"]
        }
        
        score = sum(scoring.values())
        feedback = []
        
        if scoring["Defendants"]:
            feedback.append("✓ Defendants are critical - they're directly affected by decisions.")
        else:
            feedback.append("⚠️ Defendants should be 'Critical' - they're most impacted.")
        
        if scoring["Community Advocates"]:
            feedback.append("✓ Community Advocates are critical - they represent affected populations.")
        else:
            feedback.append("⚠️ Community Advocates should be 'Critical' - they ensure community voice.")
        
        if scoring["Families"]:
            feedback.append("✓ Families are highly important - they're indirectly affected.")
        else:
            feedback.append("⚠️ Families should be 'High' importance - they suffer consequences too.")
        
        if scoring["Judges"]:
            feedback.append("✓ Judges are highly important - they make final decisions.")
        else:
            feedback.append("⚠️ Judges should be 'High' importance - they're key decision makers.")
        
        points = 0
        if score >= 4:
            points = 100
            moral_compass_points["value"] += points
            feedback.append(f"\n🎉 Excellent stakeholder prioritization!\n🏆 +{points} Moral Compass points!")
        elif score >= 3:
            points = 50
            moral_compass_points["value"] += points
            feedback.append(f"\n🏆 +{points} Moral Compass points!")
        
        # Store prioritization
        for stakeholder in ["Defendants", "Families", "Judges", "Community Advocates", "NGOs"]:
            stakeholder_priorities.append(stakeholder)
        
        explanation = "\n\n**Why certain groups are critical:**\n"
        explanation += "- **Defendants & Community Advocates:** Directly affected by AI decisions\n"
        explanation += "- **Families:** Bear consequences of incorrect predictions\n"
        explanation += "- **Judges:** Need to trust the system they're using\n"
        explanation += "- **NGOs:** Provide oversight and advocacy\n"
        
        return "\n".join(feedback) + explanation

    def check_stakeholder_question(answer):
        """Check stakeholder identification question."""
        if answer == "Defendants and community members directly affected by the system":
            moral_compass_points["value"] += 50
            return "✓ Correct! Those directly affected by AI decisions must have a voice in system design and oversight.\n\n🏆 +50 Moral Compass points!"
        else:
            return "✗ Not quite. Think about who faces the real-world consequences of AI predictions."

    def check_inclusion_question(answer):
        """Check inclusion definition question."""
        if answer == "Actively involving diverse stakeholders in design, development, and oversight":
            moral_compass_points["value"] += 50
            return "✓ Correct! Inclusion means bringing diverse voices into the process, not just serving diverse populations.\n\n🏆 +50 Moral Compass points!"
        else:
            return "✗ Not quite. Inclusion is about participation and voice, not just access."

    def reveal_final_score():
        """Reveal final Moral Compass score with growth visualization."""
        user_stats = _get_user_stats()
        total_score = moral_compass_points["value"]
        
        # Simulated score progression through activities
        activity7_score = min(400, int(total_score * 0.3))
        activity8_score = min(800, int(total_score * 0.6))
        activity9_score = total_score
        
        report = f"""
# 🎊 Final Moral Compass Score Reveal

## Your Justice & Equity Journey

### Score Progression
- **Activity 7 (Bias Detective):** {activity7_score} points
- **Activity 8 (Fairness Fixer):** {activity8_score} points  
- **Activity 9 (Justice & Equity Upgrade):** {activity9_score} points

### Total Moral Compass Score: {total_score} points

---

## 🏆 Achievement Unlocked: **Justice & Equity Champion**

You've demonstrated mastery of:
- ✅ Expert fairness frameworks (OEIAC)
- ✅ Bias detection and diagnosis
- ✅ Technical fairness interventions
- ✅ Representative data strategies
- ✅ Accessibility and inclusion
- ✅ Stakeholder engagement

---

## Team Leaderboard
"""
        
        if user_stats["is_signed_in"]:
            report += f"""
**Your Team:** {user_stats["team_name"]}
**Username:** {user_stats["username"]}
**Your Score:** {total_score} points

*Check the full leaderboard in the Model Building Game app to see team rankings!*
"""
        else:
            report += """
*Sign in to see your team ranking and compete on the leaderboard!*
"""
        
        report += """
---

## 🎖️ Badge Earned

**Justice & Equity Champion**

*Awarded for completing Activities 7, 8, and 9 with demonstrated understanding 
of fairness principles, technical fixes, and systemic improvements.*
"""
        
        return report

    def generate_completion_certificate():
        """Generate completion message with certificate unlock."""
        user_stats = _get_user_stats()
        
        certificate = f"""
# 🎓 Certificate of Completion

## Ethics at Play: Justice & Equity Challenge

**This certifies that**

### {user_stats["username"]}

**has successfully completed Activities 7, 8, and 9:**

- 🕵️ **Bias Detective:** Diagnosed bias in AI systems using expert frameworks
- 🔧 **Fairness Fixer:** Applied technical fairness interventions
- 🌟 **Justice & Equity Upgrade:** Elevated the system through inclusion and accessibility

**Final Moral Compass Score:** {moral_compass_points["value"]} points

**Team:** {user_stats["team_name"]}

---

### Skills Demonstrated:
- Expert fairness evaluation (OEIAC framework)
- Demographic bias identification
- Group-level disparity analysis
- Feature and proxy removal
- Representative data strategy
- Continuous improvement planning
- Accessibility enhancement
- Stakeholder engagement

**Date Completed:** [Auto-generated in production]

---

### Next Steps:
Proceed to **Section 10** to continue your Ethics at Play journey!
"""
        
        return certificate

    # Create the Gradio app
    with gr.Blocks(
        title="Activity 9: Justice & Equity Upgrade",
        theme=gr.themes.Soft(primary_hue=theme_primary_hue)
    ) as app:
        gr.Markdown("# 🌟 Activity 9: Justice & Equity Upgrade")
        gr.Markdown(
            """
            **Objective:** Elevate fairness improvements by addressing inclusion, accessibility, 
            stakeholder engagement, and structural justice.
            
            **Your Role:** You're now a **Justice Architect**.
            
            **Progress:** Activity 9 of 10 — Elevate the System
            
            **Estimated Time:** 8–10 minutes
            """
        )
        
        # Moral Compass indicator
        moral_compass_display = gr.Markdown("## 🧭 Moral Compass Score: 0 points")
        
        gr.Markdown(
            """
            ### Quick Recap
            
            In Activities 7 & 8, you addressed **technical fairness**:
            - Removed biased features
            - Eliminated proxy variables  
            - Created representative data guidelines
            
            Now, let's elevate to **systemic justice** through inclusion and accessibility.
            """
        )
        
        # Section 9.2: Access & Inclusion Makeover
        with gr.Tab("9.2 Access & Inclusion"):
            gr.Markdown(
                """
                ## Access & Inclusion Makeover
                
                **Principles:**
                - **Equal Opportunity of Access:** Everyone can use the system
                - **Inclusion and Diversity:** Diverse voices shape the system
                
                ### Accessibility Features
                
                Select features to add:
                """
            )
            
            multilang_toggle = gr.Checkbox(label="Multi-language support (Catalan, Spanish, English)", value=False)
            plaintext_toggle = gr.Checkbox(label="Plain text summaries (non-technical language)", value=False)
            screenreader_toggle = gr.Checkbox(label="Screen reader compatibility", value=False)
            
            accessibility_btn = gr.Button("Apply Accessibility Features", variant="primary")
            accessibility_output = gr.Markdown("")
            
            accessibility_btn.click(
                fn=apply_accessibility_features,
                inputs=[multilang_toggle, plaintext_toggle, screenreader_toggle],
                outputs=accessibility_output
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
            
            gr.Markdown("### Diversity & Inclusion")
            
            team_diversity_toggle = gr.Checkbox(label="Diverse team composition (gender, ethnicity, expertise)", value=False)
            community_toggle = gr.Checkbox(label="Community advisory board", value=False)
            review_diversity_toggle = gr.Checkbox(label="Diverse review panel", value=False)
            
            diversity_btn = gr.Button("Apply Diversity Improvements", variant="primary")
            diversity_output = gr.Markdown("")
            
            diversity_btn.click(
                fn=apply_diversity_improvements,
                inputs=[team_diversity_toggle, community_toggle, review_diversity_toggle],
                outputs=diversity_output
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
            
            gr.Markdown("### Before/After Comparison")
            
            compare_btn = gr.Button("Show System Transformation", variant="secondary")
            compare_output = gr.Markdown("")
            
            compare_btn.click(
                fn=visualize_improvements,
                outputs=compare_output
            )
        
        # Section 9.3: Stakeholder Mapping
        with gr.Tab("9.3 Stakeholder Mapping"):
            gr.Markdown(
                """
                ## Stakeholder Prioritization Map
                
                **Principle:** Affected community members must have a voice.
                
                ### Exercise: Prioritize Stakeholders
                
                Drag each stakeholder to the appropriate priority level:
                - **Critical:** Must be involved in all decisions
                - **High:** Important voice in major decisions
                - **Medium:** Should be consulted periodically
                """
            )
            
            judges_priority = gr.Radio(
                choices=["Critical", "High", "Medium"],
                label="Judges (use the system to make decisions):",
                value=None
            )
            defendants_priority = gr.Radio(
                choices=["Critical", "High", "Medium"],
                label="Defendants (directly affected by predictions):",
                value=None
            )
            families_priority = gr.Radio(
                choices=["Critical", "High", "Medium"],
                label="Families (indirectly affected):",
                value=None
            )
            community_priority = gr.Radio(
                choices=["Critical", "High", "Medium"],
                label="Community Advocates (represent affected populations):",
                value=None
            )
            ngos_priority = gr.Radio(
                choices=["Critical", "High", "Medium"],
                label="NGOs (provide oversight):",
                value=None
            )
            
            stakeholder_btn = gr.Button("Submit Prioritization", variant="primary")
            stakeholder_output = gr.Markdown("")
            
            stakeholder_btn.click(
                fn=prioritize_stakeholders,
                inputs=[judges_priority, defendants_priority, families_priority, community_priority, ngos_priority],
                outputs=stakeholder_output
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
            
            gr.Markdown("### Check-In Questions")
            
            stakeholder_question = gr.Radio(
                choices=[
                    "Technical experts and data scientists",
                    "Government officials and administrators",
                    "Defendants and community members directly affected by the system",
                    "Only judges who use the system"
                ],
                label="Who should have the strongest voice in AI criminal justice systems?",
                value=None
            )
            stakeholder_check_btn = gr.Button("Check Answer")
            stakeholder_feedback = gr.Markdown("")
            
            stakeholder_check_btn.click(
                fn=check_stakeholder_question,
                inputs=stakeholder_question,
                outputs=stakeholder_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
            
            inclusion_question = gr.Radio(
                choices=[
                    "Making sure the system works for everyone",
                    "Hiring diverse employees",
                    "Actively involving diverse stakeholders in design, development, and oversight",
                    "Translating the interface into multiple languages"
                ],
                label="What does 'Inclusion' mean in the context of AI ethics?",
                value=None
            )
            inclusion_check_btn = gr.Button("Check Answer")
            inclusion_feedback = gr.Markdown("")
            
            inclusion_check_btn.click(
                fn=check_inclusion_question,
                inputs=inclusion_question,
                outputs=inclusion_feedback
            ).then(
                fn=lambda: f"## 🧭 Moral Compass Score: {moral_compass_points['value']} points",
                outputs=moral_compass_display
            )
        
        # Section 9.4: Final Score Reveal
        with gr.Tab("9.4 Final Score"):
            gr.Markdown(
                """
                ## 🎊 Final Moral Compass Score Reveal
                
                See how you've grown from the start of Section 7 to now!
                """
            )
            
            reveal_btn = gr.Button("Reveal My Final Score", variant="primary", size="lg")
            score_output = gr.Markdown("")
            
            reveal_btn.click(
                fn=reveal_final_score,
                outputs=score_output
            )
        
        # Section 9.5: Completion
        with gr.Tab("9.5 Completion"):
            gr.Markdown(
                """
                ## 🎓 Activity 9 Complete!
                
                Generate your completion certificate and unlock the next section.
                """
            )
            
            certificate_btn = gr.Button("Generate Certificate", variant="primary", size="lg")
            certificate_output = gr.Markdown("")
            
            certificate_btn.click(
                fn=generate_completion_certificate,
                outputs=certificate_output
            )
            
            gr.Markdown(
                """
                ---
                
                ### 🎉 Congratulations!
                
                You've completed the **Justice & Equity Challenge** (Activities 7, 8, and 9).
                
                **What you've learned:**
                - How to diagnose bias using expert frameworks
                - Technical fairness interventions
                - Representative data strategies
                - Accessibility and inclusion principles
                - Stakeholder engagement best practices
                
                **Next:** Continue to **Section 10** to complete your Ethics at Play journey!
                """
            )

    return app


def launch_justice_equity_upgrade_app(
    share: bool = False,
    server_name: str = "127.0.0.1",
    server_port: int = 7862,
    theme_primary_hue: str = "indigo"
) -> None:
    """Convenience wrapper to create and launch the justice & equity upgrade app inline."""
    app = create_justice_equity_upgrade_app(theme_primary_hue=theme_primary_hue)
    app.launch(share=share, server_name=server_name, server_port=server_port)
