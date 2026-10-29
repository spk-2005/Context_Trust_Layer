from typing import Any, Dict, List
from app.services.copilot_query_service import CopilotQueryResponse


class SlackBlockKitRenderer:
    """
    Renders structured Copilot results into accessible, clean Slack Block Kit messages.
    Strictly keeps responses ephemeral, prevents @channel mentions, and adds fallback text.
    """

    @staticmethod
    def _sanitize_mrkdwn(text: str) -> str:
        """Suppresses accidental @channel, @here, or <!everyone> mentions."""
        if not text:
            return ""
        return text.replace("<!channel>", "@channel").replace("<!here>", "@here").replace("<!everyone>", "@everyone")

    @classmethod
    def render_policy_answer(cls, response: CopilotQueryResponse, question: str) -> Dict[str, Any]:
        """Formats the verified, cited policy answer into Block Kit."""
        status_badges = {
            "ANSWERED": "✅ *Supported Answer*",
            "PARTIAL": "⚠️ *Partial Evidence*",
            "CLARIFICATION_NEEDED": "❓ *Clarification Needed*",
            "REVIEW_RECOMMENDED": "🔍 *Review Recommended*",
            "DISPUTED": "🚨 *Disputed Evidence*",
        }
        status_label = status_badges.get(response.answer_status, "ℹ️ *Policy Guidance*")

        blocks: List[Dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🛡️ Trulin Policy Assistant",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Question:* {cls._sanitize_mrkdwn(question)}",
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Answer:*\n{cls._sanitize_mrkdwn(response.synthesized_answer)}",
                },
            },
        ]

        # Add conditions and limitations if present
        if response.conditions:
            conditions_text = "\n".join(f"• {cls._sanitize_mrkdwn(c)}" for c in response.conditions)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Conditions & Limitations:*\n{conditions_text}",
                },
            })

        # Add warnings or conflicts if present
        if response.warnings:
            warning_bullets = "\n".join(f"⚠️ {cls._sanitize_mrkdwn(w)}" for w in response.warnings[:3])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Governance Advisories:*\n{warning_bullets}",
                },
            })

        # Add permitted cited sources with authenticated deep links
        if response.citations:
            source_lines = []
            for c in response.citations[:5]:
                sec_str = f" — Section {c.section}" if c.section else ""
                pg_str = f" (p. {c.page})" if c.page else ""
                source_lines.append(
                    f"{c.source_index}. <{c.evidence_url}|*{cls._sanitize_mrkdwn(c.document_name)}*>{sec_str}{pg_str} • Trust: `{c.trust_score}`"
                )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Permitted Sources:*\n" + "\n".join(source_lines),
                },
            })

        # Status badge & Trace ID footer
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Status: {status_label} (Trust: `{response.trust_score}`) • Trace ID: `{response.trace_id}`",
                }
            ],
        })

        # Interactive feedback / review buttons
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Report Issue", "emoji": True},
                    "action_id": "slack_report_issue",
                    "value": response.trace_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Request Review", "emoji": True},
                    "action_id": "slack_request_review",
                    "value": response.trace_id,
                    "style": "primary",
                },
            ],
        })

        fallback_text = f"Trulin Policy Answer: {cls._sanitize_mrkdwn(response.synthesized_answer)[:150]}..."
        return {
            "response_type": "ephemeral",
            "replace_original": False,
            "text": fallback_text,
            "blocks": blocks,
        }

    @classmethod
    def render_account_linking_card(cls, link_url: str) -> Dict[str, Any]:
        """Renders an invitation card to securely link a Slack user to their Trulin account."""
        blocks: List[Dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔒 Connect Your Trulin Account",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "To ask policy questions and inspect authorized evidence collections, "
                        "you must link your Slack user profile to your Trulin organization account.\n\n"
                        "This link is private and expires in 15 minutes."
                    ),
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Connect Trulin Account", "emoji": True},
                        "action_id": "slack_open_link_flow",
                        "url": link_url,
                        "style": "primary",
                    }
                ],
            },
        ]
        return {
            "response_type": "ephemeral",
            "text": "Connect your Trulin account to access authorized sources.",
            "blocks": blocks,
        }

    @classmethod
    def render_help_card(cls) -> Dict[str, Any]:
        """Renders private help overview for /trulin slash commands."""
        blocks: List[Dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📖 Trulin Assistant Help & Usage",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "Trulin provides read-only policy assistance backed by verified enterprise evidence.\n\n"
                        "• `/trulin ask <question>` — Ask a policy or agreement question privately.\n"
                        "• `/trulin link` — Check or update your linked Trulin account.\n"
                        "• `/trulin status` — View installation health and permitted collection count.\n"
                        "• `/trulin help` — Show this guidance card."
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "All answers are strictly private (ephemeral) and visible only to you.",
                    }
                ],
            },
        ]
        return {
            "response_type": "ephemeral",
            "text": "Trulin Assistant Help: Use /trulin ask <question> for private answers.",
            "blocks": blocks,
        }

    @classmethod
    def render_error_card(cls, message: str, trace_id: str) -> Dict[str, Any]:
        """Renders honest, non-leaking error notice."""
        return {
            "response_type": "ephemeral",
            "text": f"Error: {message}",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"⚠️ *Unable to retrieve policy answer:*\n{cls._sanitize_mrkdwn(message)}",
                    },
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Trace ID: `{trace_id}` • Please contact your compliance administrator if this persists.",
                        }
                    ],
                },
            ],
        }
