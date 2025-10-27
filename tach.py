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
        pdf_bytes = None

        # 🟢 Trường hợp 1: Nhận file binary trực tiếp (multipart/form-data)
        if "file" in request.files:
            file = request.files["file"]
            pdf_bytes = io.BytesIO(file.read())

        # 🟠 Trường hợp 2: Nhận JSON có 'url'
        elif request.is_json:
            data = request.get_json()
            drive_url = data.get("url")
            if not drive_url:
                return jsonify({"error": "Thiếu 'url' hoặc 'file' trong request"}), 400
            direct_link = get_direct_drive_link(drive_url)
            if not direct_link:
                return jsonify({"error": "URL Google Drive không hợp lệ"}), 400

            response = requests.get(direct_link)
            if response.status_code != 200:
                return jsonify({"error": "Không thể tải file PDF"}), 400
            pdf_bytes = io.BytesIO(response.content)

        else:
            return jsonify({"error": "Không có file hoặc url"}), 400

        # 🔍 Đọc PDF bằng PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # 📦 Tạo file zip chứa ảnh từng trang
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for page_num in range(len(doc)):
                page = doc[page_num]

                # 🚀 Dùng ma trận scale chuẩn DPI=300 (rõ nét thật)
                matrix = fitz.Matrix(300 / 72, 300 / 72)
                pix = page.get_pixmap(matrix=matrix, alpha=False)

                # 🔄 Chuyển sang JPEG (nét và nhẹ hơn PNG)
                img_bytes = pix.tobytes("jpeg", quality=95)

                # 🧾 Ghi vào file ZIP
                zipf.writestr(f"page_{page_num + 1}.jpg", img_bytes)

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


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
