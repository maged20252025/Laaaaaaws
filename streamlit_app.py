
import streamlit as st
import streamlit.components.v1 as components
from docx import Document
import re
import os
import time
import base64

st.set_page_config(page_title="القوانين اليمنية بآخر تعديلاتها حتى عام 2025م", layout="wide")
st.markdown("<h1 style='text-align: center;'>مرحبًا بك في تطبيق القوانين اليمنية بآخر تعديلاتها حتى عام 2025م</h1>", unsafe_allow_html=True)

def is_activated():
    return os.path.exists("activated.txt")

def activate_app(code):
    if not os.path.exists("activation_codes.txt"):
        return False
    with open("activation_codes.txt", "r") as f:
        codes = [line.strip() for line in f.readlines()]
    if code in codes:
        codes.remove(code)
        with open("activation_codes.txt", "w") as f:
            for c in codes:
                f.write(c + "\n")
        with open("activated.txt", "w") as f:
            f.write("activated")
        return True
    return False

def highlight_keywords(text, keywords):
    for kw in keywords:
        text = re.sub(f"({re.escape(kw)})", r"<mark>\\1</mark>", text, flags=re.IGNORECASE)
    return text

def extract_context(paragraphs, keywords, context_lines=5):
    matched_indexes = [i for i, line in enumerate(paragraphs) if any(kw in line for kw in keywords)]
    context_set = set()
    for idx in matched_indexes:
        for i in range(max(0, idx - context_lines), min(len(paragraphs), idx + context_lines + 1)):
            context_set.add(i)
    return "\n".join(paragraphs[i] for i in sorted(context_set))

def export_results_to_docx(results, filename="نتائج_البحث.docx"):
    doc = Document()
    doc.add_heading("نتائج البحث", 0)
    for r in results:
        doc.add_heading(f'{r["law"]} - المادة {r["num"]}', level=1)
        doc.add_paragraph(r["context"])
    filepath = f"/mnt/data/{filename}"
    doc.save(filepath)
    return filepath

def run_main_app():
    components.html("""
    <style>
    .scroll-btn {
        position: fixed;
        left: 10px;
        padding: 12px;
        font-size: 24px;
        border-radius: 50%;
        background-color: #c5e1a5;
        color: black;
        cursor: pointer;
        z-index: 9999;
        border: none;
        box-shadow: 1px 1px 5px #888;
    }
    #scroll-top-btn { bottom: 80px; }
    #scroll-bottom-btn { bottom: 20px; }
    </style>
    <button class='scroll-btn' id='scroll-top-btn' onclick='window.scrollTo({top: 0, behavior: "smooth"});'>⬆️</button>
    <button class='scroll-btn' id='scroll-bottom-btn' onclick='window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"});'>⬇️</button>
    """, height=1)

    subfolders = [f.path for f in os.scandir() if f.is_dir() and f.name not in [".git", ".streamlit"]]
    if not subfolders:
        st.warning("📂 لا توجد مجلدات قوانين.")
        return

    selected_folder = st.selectbox("اختر مجلدًا للبحث فيه:", ["🔍 كل المجلدات"] + subfolders)

    all_files = {}
    if selected_folder == "🔍 كل المجلدات":
        for folder in subfolders:
            files = [f for f in os.listdir(folder) if f.endswith(".docx")]
            all_files[folder] = files
    else:
        files = [f for f in os.listdir(selected_folder) if f.endswith(".docx")]
        all_files[selected_folder] = files

    keywords = st.text_area("الكلمات المفتاحية (افصل بفاصلة)", "")

    if "results" not in st.session_state:
        st.session_state.results = []
    if "search_done" not in st.session_state:
        st.session_state.search_done = False

    if st.button("🔍 بدء البحث") and keywords:
        kw_list = [k.strip() for k in keywords.split(",") if k.strip()]
        results = []

        for folder, files in all_files.items():
            for file in files:
                doc = Document(os.path.join(folder, file))
                law_name = file.replace(".docx", "")
                last_article = "غير معروفة"
                current_article = []
                for para in doc.paragraphs:
                    txt = para.text.strip()
                    if not txt:
                        continue
                    match = re.match(r"مادة\s*\(?\s*(\d+)\)?", txt)
                    if match:
                        if current_article:
                            full_text = "\n".join(current_article)
                            if any(kw in full_text for kw in kw_list):
                                context = extract_context(current_article, kw_list)
                                results.append({
                                    "law": law_name,
                                    "num": last_article,
                                    "text": highlight_keywords(context, kw_list),
                                    "plain": full_text,
                                    "context": context,
                                    "keywords": kw_list
                                })
                            current_article = []
                        last_article = match.group(1)
                    current_article.append(txt)

                if current_article:
                    full_text = "\n".join(current_article)
                    if any(kw in full_text for kw in kw_list):
                        context = extract_context(current_article, kw_list)
                        results.append({
                            "law": law_name,
                            "num": last_article,
                            "text": highlight_keywords(context, kw_list),
                            "plain": full_text,
                            "context": context,
                            "keywords": kw_list
                        })

        st.session_state.results = results
        st.session_state.search_done = True

    if st.session_state.search_done and st.session_state.results:
        results = st.session_state.results
        unique_laws = sorted(set(r["law"] for r in results))
        st.success(f"تم العثور على {len(results)} نتيجة في {len(unique_laws)} قانون/ملف.")
        selected_law = st.selectbox("فلترة حسب القانون", ["الكل"] + unique_laws)
        filtered = results if selected_law == "الكل" else [r for r in results if r["law"] == selected_law]

        for r in filtered:
            st.markdown(f"""
<div style="background-color:#f1f8e9;padding:15px;margin-bottom:15px;border-radius:10px;
            border:1px solid #c5e1a5;direction:rtl;text-align:right">
    <p style="font-weight:bold;font-size:18px;margin:0">🔷 {r["law"]} - المادة {r["num"]}</p>
    <p style="font-size:17px;line-height:1.8;margin-top:10px">
        {r["text"]}
    </p>
</div>
""", unsafe_allow_html=True)

        if filtered:
            filepath = export_results_to_docx(filtered)
            with open(filepath, "rb") as f:
                st.download_button(
                    label="📥 تحميل النتائج كملف Word",
                    data=f,
                    file_name="نتائج_البحث.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

def main():
    if not is_activated():
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔐 لدي كود تفعيل"):
                code = st.text_input("أدخل كود التفعيل هنا")
                if code and activate_app(code.strip()):
                    st.success("✅ تم التفعيل! أعد تشغيل التطبيق.")
        with col2:
            if "trial_start" not in st.session_state:
                if st.button("🕒 تجربة مجانية"):
                    st.session_state.trial_start = time.time()
                    run_main_app()
            elif time.time() - st.session_state.trial_start < 3600:
                st.info("✅ النسخة التجريبية نشطة.")
                run_main_app()
            else:
                st.error("❌ انتهت مدة التجربة المجانية.")
    else:
        run_main_app()

main()
