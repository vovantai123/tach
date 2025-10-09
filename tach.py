from flask import Flask, request, send_file, jsonify
import fitz  # PyMuPDF
import io
import zipfile
import requests
import re

app = Flask(__name__)

def get_direct_drive_link(url: str):
    """Chuyển link Google Drive sang link tải trực tiếp"""
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if not match:
        return None
    file_id = match.group(1)
    return f"https://drive.google.com/uc?export=download&id={file_id}"

@app.route("/pdf-to-images", methods=["POST"])
def pdf_to_images():
    try:
        data = request.get_json()
        if not data or "url" not in data:
            return jsonify({"error": "Thiếu 'url' trong request body"}), 400

        drive_url = data["url"]
        direct_link = get_direct_drive_link(drive_url)
        if not direct_link:
            return jsonify({"error": "URL Google Drive không hợp lệ"}), 400

        # 🟢 Tải PDF
        response = requests.get(direct_link)
        if response.status_code != 200:
            return jsonify({"error": "Không thể tải file PDF"}), 400

        pdf_bytes = io.BytesIO(response.content)

        # 🟢 Mở PDF bằng PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for page_num in range(len(doc)):
                page = doc[page_num]
        
                # Đảm bảo không bị crop mất phần dưới
                page.set_cropbox(page.mediabox)
        
                # Render ảnh chất lượng cao (200 DPI tương đương Matrix(2,2))
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        
                img_bytes = pix.tobytes("png")
                zipf.writestr(f"page_{page_num + 1}.png", img_bytes)

        doc.close()

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name="pdf_pages.zip",
            mimetype="application/zip"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
