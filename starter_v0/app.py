import streamlit as st
import os
import sys
from pathlib import Path

# Đảm bảo python tìm thấy các module trong thư mục hiện tại
ROOT = Path(__file__).parent
sys.path.append(str(ROOT))

ARTIFACTS_DIR = ROOT / "artifacts"

# Import các thành phần từ chính code gốc của bạn
try:
    from env_loader import load_lab_env
    from providers import make_provider
    from tools import load_tool_declarations, to_openai_tools
    from versioning import build_artifact_version, artifact_version_dict
    from chat import run_model_tool_loop, now_iso, safe_slug, write_transcript
    LOAD_SUCCESS = True
except ImportError as e:
    LOAD_SUCCESS = False
    IMPORT_ERROR = str(e)

# Load môi trường lab
if ROOT:
    try:
        load_lab_env(ROOT)
    except Exception:
        pass

st.set_page_config(
    page_title="Research Agent Tool Eval - Dashboard",
    page_icon="🔬",
    layout="wide"
)

# Custom CSS hiện đại, sang trọng (Dark mode tinh tế)
st.markdown("""
    <style>
    .main {
        background-color: #0b0f19;
        color: #e5e7eb;
    }
    .stChatMessage {
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 12px;
        border: 1px solid #1f2937;
    }
    h1 {
        color: #f3f4f6;
        font-weight: 800;
        letter-spacing: -0.5px;
    }
    .stSidebar {
        background-color: #111827;
        border-right: 1px solid #1f2937;
    }
    .stExpander {
        border: 1px solid #374151;
        border-radius: 8px;
        background-color: #111827;
    }
    </style>
""", unsafe_allow_html=True)

# Tiêu đề ứng dụng
st.title("🔬 Research Agent Tool Eval & Trace Dashboard")
st.markdown("Hệ thống kiểm tra vòng lặp Agent, trace request/response từng round, tool execution và artifact version trực quan.")

# Sidebar cấu hình hệ thống
st.sidebar.markdown("### ⚙️ Cấu hình phiên bản")
selected_version = st.sidebar.selectbox("Chọn Version Agent", ["v3", "v2", "v1"], index=0)
selected_provider = st.sidebar.selectbox("Chọn Provider", ["openrouter", "openai", "anthropic", "gemini"], index=0)
model_input = st.sidebar.text_input("Model tùy chỉnh (Bỏ trống để dùng mặc định)", value="")
history_window = st.sidebar.slider("History Window", min_value=1, max_value=10, value=5)
max_tool_rounds = st.sidebar.slider("Max Tool Rounds", min_value=1, max_value=8, value=4)

st.sidebar.markdown("---")
if LOAD_SUCCESS:
    st.sidebar.success("🟢 Môi trường & Module sẵn sàng")
else:
    st.sidebar.error(f"🔴 Lỗi Import: {IMPORT_ERROR}")

# Khởi tạo Session State cho hội thoại và lịch sử ngữ cảnh
if "messages" not in st.session_state:
    st.session_state.messages = [] # Cho UI hiển thị
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [] # Cho agent nhớ ngữ cảnh (history window)

# Nút xoá lịch sử chat
if st.sidebar.button("🗑️ Xoá hội thoại & Reset"):
    st.session_state.messages = []
    st.session_state.chat_history = []
    st.rerun()

# Hiển thị lịch sử chat giao diện
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "trace_payload" in msg and msg["trace_payload"]:
            with st.expander("🔍 Chi tiết Tool Trace, Rounds & Artifact Version"):
                st.json(msg["trace_payload"])

# Xử lý input nhập từ người dùng
if user_prompt := st.chat_input("Nhập yêu cầu nghiên cứu của bạn..."):
    if not LOAD_SUCCESS:
        st.error("Không thể khởi chạy vì lỗi import module gốc. Vui lòng kiểm tra lại cấu trúc thư mục.")
    else:
        # Thêm tin nhắn user vào UI
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner(f"Agent đang xử lý vòng lặp với [{selected_version.upper()} - {selected_provider}]..."):
                try:
                    # Load system prompt và tools giống hệt chat.py
                    system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
                    tools_path = ARTIFACTS_DIR / "tools.yaml"
                    
                    system_prompt = system_prompt_path.read_text(encoding="utf-8") if system_prompt_path.exists() else ""
                    tool_declarations = load_tool_declarations(tools_path)
                    openai_tools = to_openai_tools(tool_declarations)
                    
                    prov = make_provider(selected_provider)
                    sel_model = model_input.strip() if model_input.strip() else getattr(prov, "default_model", None)
                    artifact_version = build_artifact_version(selected_version, system_prompt_path, tools_path)

                    # Xây dựng danh sách messages theo chuẩn chat.py
                    # Sử dụng hàm trim_history từ chat.py
                    from chat import trim_history
                    messages_for_loop = [
                        {"role": "system", "content": system_prompt},
                        *trim_history(st.session_state.chat_history, history_window),
                        {"role": "user", "content": user_prompt},
                    ]

                    # Gọi trực tiếp hàm gốc run_model_tool_loop từ chat.py của bạn
                    result = run_model_tool_loop(
                        provider=prov,
                        messages=messages_for_loop,
                        tools=openai_tools,
                        model=sel_model,
                        max_tool_rounds=max_tool_rounds,
                    )

                    assistant_text = result.get("assistant_text", "")
                    st.markdown(assistant_text)

                    # Đóng gói toàn bộ trace, round, tool events và artifact version
                    trace_payload = {
                        "artifact_version": artifact_version.artifact_version,
                        "provider": selected_provider,
                        "model": sel_model,
                        "status": result.get("status"),
                        "rounds": result.get("rounds", []),
                        "tool_events": result.get("tool_events", []),
                        "artifact_metadata": artifact_version_dict(artifact_version)
                    }

                    with st.expander("🔍 Xem Tool Trace, Rounds & Artifact Version chi tiết"):
                        st.json(trace_payload)

                    # Cập nhật lịch sử ngữ cảnh
                    st.session_state.chat_history.append({"role": "user", "content": user_prompt})
                    st.session_state.chat_history.append({"role": "assistant", "content": assistant_text})

                    # Lưu vào session UI messages
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": assistant_text,
                        "trace_payload": trace_payload
                    })

                    # Tự động ghi transcript tương tự logic của chat.py để phục vụ nộp bài
                    try:
                        transcripts_dir = ROOT / "transcripts"
                        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
                        transcript_id = "_".join([safe_slug(selected_version), safe_slug(selected_provider), timestamp])
                        transcript_path = transcripts_dir / f"{transcript_id}.transcript.json"
                        
                        transcript_data = {
                            "transcript_id": transcript_id,
                            **artifact_version_dict(artifact_version),
                            "provider": selected_provider,
                            "model": sel_model,
                            "system_prompt": str(system_prompt_path),
                            "tools": str(tools_path),
                            "history_window": history_window,
                            "max_tool_rounds": max_tool_rounds,
                            "created_at": now_iso(),
                            "updated_at": now_iso(),
                            "turns": [{
                                "turn_index": len(st.session_state.messages) // 2,
                                "started_at": now_iso(),
                                "user": user_prompt,
                                **result,
                                "ended_at": now_iso()
                            }]
                        }
                        write_transcript(transcript_path, transcript_data)
                    except Exception:
                        pass

                except Exception as exc:
                    err_msg = f"Lỗi thực thi vòng lặp agent: {type(exc).__name__}: {str(exc)}"
                    st.error(err_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": err_msg
                    })