import streamlit as st
import google.generativeai as genai
import os
import docx
import pypdf

# 1. Cấu hình trang giao diện
st.set_page_config(
    page_title="Trợ Lý Chính Sách Công Ty",
    page_icon="🏢",
    layout="centered"
)

# 2. Thông tin liên hệ HR mặc định
DEFAULT_HR_CONTACT = """
- **Bộ phận:** Phòng Nhân sự (HR Department)
- **Email:** hr@congty.com
- **Hotline / Zalo:** 0988.123.456 (Ms. Thảo - Trưởng phòng HR)
- **Địa điểm:** Tầng 3 - Tòa nhà công ty (Giờ hành chính 8h30 - 17h30)
"""

# 3. Lấy API Key từ Secrets hoặc biến môi trường
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", None))

with st.sidebar:
    st.header("⚙️ Cài đặt & Dữ liệu")
    if not api_key:
        api_key = st.text_input("Nhập Google Gemini API Key:", type="password")
        if not api_key:
            st.warning("Vui lòng nhập API Key để bắt đầu chat!")
    
    st.subheader("📋 Thông tin liên hệ HR")
    hr_contact = st.text_area("Thông tin HR khi không tìm thấy tài liệu:", value=DEFAULT_HR_CONTACT, height=130)
    
    st.subheader("📁 Tài liệu quy định")
    uploaded_files = st.file_uploader(
        "Tải file Word/PDF chính sách:",
        type=["docx", "pdf"],
        accept_multiple_files=True
    )

# Hàm đọc file Word
def read_docx(file):
    try:
        doc = docx.Document(file)
        return "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
    except Exception:
        return ""

# Hàm đọc file PDF
def read_pdf(file):
    try:
        reader = pypdf.PdfReader(file)
        text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text.append(t.strip())
        return "\n".join(text)
    except Exception:
        return ""

# Đọc tài liệu 1 LẦN DUY NHẤT và lưu vào bộ nhớ đệm
if "doc_text" not in st.session_state or uploaded_files:
    all_content = []
    doc_folder = "documents"
    
    # 1. Đọc từ thư mục documents trong code (nếu có)
    if os.path.exists(doc_folder):
        for filename in os.listdir(doc_folder):
            filepath = os.path.join(doc_folder, filename)
            if filename.endswith(".docx"):
                content = read_docx(filepath)
                if content:
                    all_content.append(f"--- TÀI LIỆU: {filename} ---\n{content}")
            elif filename.endswith(".pdf"):
                content = read_pdf(filepath)
                if content:
                    all_content.append(f"--- TÀI LIỆU: {filename} ---\n{content}")

    # 2. Đọc từ file người dùng upload qua thanh bên
    if uploaded_files:
        for f in uploaded_files:
            if f.name.endswith(".docx"):
                c = read_docx(f)
                if c:
                    all_content.append(f"--- TÀI LIỆU: {f.name} ---\n{c}")
            elif f.name.endswith(".pdf"):
                c = read_pdf(f)
                if c:
                    all_content.append(f"--- TÀI LIỆU: {f.name} ---\n{c}")

    st.session_state.doc_text = "\n\n".join(all_content)

doc_text = st.session_state.get("doc_text", "")

# Tiêu đề giao diện
st.title("🏢 Trợ Lý Chính Sách Nội Bộ")
st.caption("Tra cứu quy chế, chế độ phúc lợi, nghỉ phép, hợp đồng... dành cho cán bộ nhân viên.")

# Thông báo trạng thái tài liệu
with st.sidebar:
    if doc_text.strip():
        st.success("✅ Đã nạp dữ liệu chính sách thành công.")
    else:
        st.info("💡 Chưa có tài liệu nào. Hãy bấm 'Upload' ở trên để nạp 10 file chính sách.")

# Khởi tạo lịch sử chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Tôi là trợ lý giải đáp chính sách công ty. Bạn muốn tìm hiểu về quy chế, chế độ nghỉ phép, phúc lợi hay thủ tục nào?"}
    ]

# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Xử lý câu hỏi với chế độ STREAMING (Chữ chạy ra từng từ siêu nhanh)
if prompt := st.chat_input("Nhập câu hỏi của bạn về chính sách công ty..."):
    if not api_key:
        st.error("Chưa cấu hình API Key. Vui lòng nhập API Key ở thanh bên!")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        genai.configure(api_key=api_key)
        
        system_instruction = f"""
Bạn là Trợ lý giải đáp chính sách công ty.
Tài liệu quy định công ty:
=== NỘI DUNG TÀI LIỆU ===
{doc_text if doc_text.strip() else "HIỆN CHƯA CÓ TÀI LIỆU NÀO."}
=== HẾT TÀI LIỆU ===

QUY TẮC:
1. Trả lời ngắn gọn, chuẩn xác dựa vào tài liệu, có trích dẫn văn bản/điều khoản.
2. Nếu câu hỏi KHÔNG CÓ trong tài liệu, TUYỆT ĐỐI KHÔNG BỊA ĐẶT mà hãy trả lời:
"Thông tin này hiện chưa có trong quy định công ty. Vui lòng liên hệ phòng Nhân sự để được giải đáp:

{hr_contact}"
"""
        model = genai.GenerativeModel(
            model_name="gemini-3.8-flash",
            system_instruction=system_instruction
        )

        with st.chat_message("assistant"):
            # Bật streaming: chữ nhảy ra ngay lập tức
            response = model.generate_content(prompt, stream=True)
            
            def stream_data():
                for chunk in response:
                    if chunk.text:
                        yield chunk.text
            
            bot_reply = st.write_stream(stream_data)

        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

    except Exception as e:
        st.error(f"Đã xảy ra lỗi: {str(e)}")
