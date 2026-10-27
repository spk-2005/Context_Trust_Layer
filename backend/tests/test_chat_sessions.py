import uuid
import pytest
import httpx
from app.main import app
from app.db.init_db import init_db_schema

DEMO_ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.anyio
async def test_chat_session_lifecycle_and_message_processing():
    await init_db_schema()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch users to get a test user
        users_res = await client.get(f"/v1/users?organization_id={DEMO_ORG_ID}")
        assert users_res.status_code == 200
        users = users_res.json()
        assert len(users) > 0
        test_user = users[0]

        # 2. Create a new chat session for this user
        create_res = await client.post(
            "/v1/chat/sessions",
            json={
                "organization_id": DEMO_ORG_ID,
                "user_id": test_user["id"],
                "user_name": test_user["name"],
                "user_role": test_user["role"],
                "title": "Refund Policy Inquiry",
            }
        )
        assert create_res.status_code == 200
        session = create_res.json()
        session_id = session["id"]
        assert session["title"] == "Refund Policy Inquiry"
        assert session["user_name"] == test_user["name"]

        # 3. List sessions for this user
        list_res = await client.get(f"/v1/chat/sessions?organization_id={DEMO_ORG_ID}&user_id={test_user['id']}")
        assert list_res.status_code == 200
        sessions = list_res.json()
        assert any(s["id"] == session_id for s in sessions)

        # 4. Post a user message and get grounded response
        msg_res = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={
                "organization_id": DEMO_ORG_ID,
                "content": "What is our company refund window for enterprise tiers?",
                "user_id": test_user["id"],
                "user_name": test_user["name"],
                "user_role": test_user["role"],
            }
        )
        assert msg_res.status_code == 200
        msg_data = msg_res.json()
        assert "user_message" in msg_data
        assert "assistant_message" in msg_data
        assert msg_data["user_message"]["content"] == "What is our company refund window for enterprise tiers?"
        
        assistant_msg = msg_data["assistant_message"]
        assert assistant_msg["role"] == "assistant"
        assert "metadata_json" in assistant_msg
        assert assistant_msg["metadata_json"]["mode"] == "document_qa"
        assert "answer_status" in assistant_msg["metadata_json"]
        assert "decision" in assistant_msg["metadata_json"]
        assert "citations" in assistant_msg["metadata_json"]
        assert "verification" in assistant_msg["metadata_json"]
        assert "is_verified" in assistant_msg["metadata_json"]["verification"]
        if assistant_msg["metadata_json"]["citations"]:
            first_c = assistant_msg["metadata_json"]["citations"][0]
            assert "evidence_lane" in first_c

        # 4b. Test Mode B: Action Evaluation request
        action_res = await client.post(
            f"/v1/chat/sessions/{session_id}/messages",
            json={
                "organization_id": DEMO_ORG_ID,
                "content": "Can I approve a $5000 refund exception for enterprise client Acme?",
                "user_id": test_user["id"],
                "user_name": test_user["name"],
                "user_role": test_user["role"],
            }
        )
        assert action_res.status_code == 200
        action_data = action_res.json()
        action_assistant = action_data["assistant_message"]
        assert action_assistant["metadata_json"]["mode"] == "action_evaluation"
        assert action_assistant["metadata_json"]["decision"] in ["ALLOW", "BLOCK", "REVIEW", "CLARIFY"]
        assert action_assistant["metadata_json"]["audit_id"] is not None

        # 5. Fetch complete session with messages
        detail_res = await client.get(f"/v1/chat/sessions/{session_id}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert len(detail["messages"]) >= 4

        # 6. Delete the chat session
        del_res = await client.delete(f"/v1/chat/sessions/{session_id}")
        assert del_res.status_code == 200
        assert del_res.json()["status"] == "deleted"

        # 7. Confirm 404 after deletion
        get_deleted = await client.get(f"/v1/chat/sessions/{session_id}")
        assert get_deleted.status_code == 404
