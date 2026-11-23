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

# 2. Thông tin liên hệ HR mặc định (bạn có thể sửa lại thông tin này)
DEFAULT_HR_CONTACT = """
- **Bộ phận:** Phòng Nhân sự (HR Department)
- **Email:** hr@congty.com
- **Hotline / Zalo:** 0988.123.456 (Ms. Thảo - Trưởng phòng HR)
- **Địa điểm:** Tầng 3 - Tòa nhà công ty (Giờ hành chính 8h30 - 17h30)
"""

# 3. Lấy API Key (tự động lấy từ Secrets hoặc nhập ở thanh bên)
api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
elif "GEMINI_API_KEY" in os.environ:
    api_key = os.environ["GEMINI_API_KEY"]

# Thanh bên (Sidebar) quản lý
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
        "Tải thêm file Word/PDF chính sách:",
        type=["docx", "pdf"],
        accept_multiple_files=True
    )

# Hàm đọc nội dung từ file Word
def read_docx(file):
    doc = docx.Document(file)
    text = []
    for para in doc.paragraphs:
        if para.text.strip():
            text.append(para.text.strip())
    return "\n".join(text)

# Hàm đọc nội dung từ file PDF
def read_pdf(file):
    reader = pypdf.PdfReader(file)
    text = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text.append(page_text.strip())
    return "\n".join(text)

# Đọc toàn bộ tài liệu từ thư mục 'documents' và các file tải lên
@st.cache_data(show_spinner=False)
def load_all_documents(uploaded_files_data):
    all_content = []
    doc_folder = "documents"
    
    # Đọc từ thư mục documents nếu có
    if os.path.exists(doc_folder):
        for filename in os.listdir(doc_folder):
            filepath = os.path.join(doc_folder, filename)
            try:
                if filename.endswith(".docx"):
                    content = read_docx(filepath)
                    all_content.append(f"--- TÀI LIỆU: {filename} ---\n{content}\n")
                elif filename.endswith(".pdf"):
                    content = read_pdf(filepath)
                    all_content.append(f"--- TÀI LIỆU: {filename} ---\n{content}\n")
            except Exception as e:
                pass

    # Đọc từ file người dùng tải lên thanh bên (nếu có)
    if uploaded_files_data:
        for file in uploaded_files_data:
            try:
                if file.name.endswith(".docx"):
                    content = read_docx(file)
                    all_content.append(f"--- TÀI LIỆU: {file.name} ---\n{content}\n")
                elif file.name.endswith(".pdf"):
                    content = read_pdf(file)
                    all_content.append(f"--- TÀI LIỆU: {file.name} ---\n{content}\n")
            except Exception as e:
                pass
                
    return "\n\n".join(all_content)

# Tiêu đề chính trang web
st.title("🏢 Trợ Lý Chính Sách Nội Bộ")
st.caption("Tra cứu quy chế, chế độ phúc lợi, nghỉ phép, hợp đồng... dành cho toàn thể cán bộ nhân viên.")

# Đọc tài liệu
doc_text = load_all_documents(uploaded_files)

# Hiển thị số lượng tài liệu đã nạp
with st.sidebar:
    if doc_text.strip():
        st.success("✅ Đã sẵn sàng dữ liệu chính sách.")
    else:
        st.info("💡 Bạn có thể đặt 10 file Word/PDF vào thư mục 'documents' hoặc tải trực tiếp ở trên.")

# Khởi tạo lịch sử chat trong phiên làm việc
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Xin chào! Tôi là trợ lý giải đáp chính sách công ty. Bạn muốn tìm hiểu về quy chế, chế độ nghỉ phép, phúc lợi hay thủ tục nào?"}
    ]

# Hiển thị lịch sử chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Xử lý khi người dùng gửi câu hỏi
if prompt := st.chat_input("Nhập câu hỏi của bạn về chính sách công ty..."):
    if not api_key:
        st.error("Chưa cấu hình API Key. Vui lòng nhập API Key ở thanh bên!")
        st.stop()

    # Thêm câu hỏi vào lịch sử
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Cấu hình AI Gemini
    try:
        genai.configure(api_key=api_key)
        
        # System instruction thiết lập luật nghiêm ngặt cho bot
        system_instruction = f"""
Bạn là Trợ lý giải đáp chính sách công ty chuyên nghiệp, tận tâm và chính xác.
Dưới đây là TOÀN BỘ tài liệu chính sách của công ty:
=== BẮT ĐẦU TÀI LIỆU ===
{doc_text if doc_text.strip() else "HIỆN CHƯA CÓ TÀI LIỆU NÀO ĐƯỢC TẢI LÊN."}
=== KẾT THÚC TÀI LIỆU ===

QUY TẮC BẮT BUỘC KHI TRẢ LỜI:
1. CHỈ ĐƯỢC PHÉP trả lời dựa trên những thông tin có trong tài liệu trên. Hãy trích dẫn rõ tên văn bản hoặc điều khoản (nếu có).
2. Nếu câu hỏi KHÔNG CÓ trong tài liệu, hoặc tài liệu không đề cập rõ ràng, TUYỆT ĐỐI KHÔNG ĐƯỢC BỊA ĐẶT HOẶC SUY DIỄN.
3. Khi không tìm thấy thông tin hoặc ngoài phạm vi tài liệu, bạn BẮT BUỘC phải trả lời theo mẫu sau:
"Thông tin này hiện chưa có trong các quy định, chính sách hiện hành của công ty. Để được hỗ trợ và giải đáp chính xác nhất cho trường hợp của mình, bạn vui lòng liên hệ trực tiếp với bộ phận Nhân sự:

{hr_contact}"
4. Luôn giữ thái độ thân thiện, lịch sự và rõ ràng với đồng nghiệp.
"""
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction
        )

        with st.chat_message("assistant"):
            with st.spinner("Đang tra cứu tài liệu..."):
                response = model.generate_content(prompt)
                bot_reply = response.text
                st.markdown(bot_reply)

        # Lưu câu trả lời vào lịch sử
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})

    except Exception as e:
        st.error(f"Đã xảy ra lỗi khi kết nối: {str(e)}")
