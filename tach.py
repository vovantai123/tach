from flask import Flask, request, send_file, jsonify
import fitz  # PyMuPDF
from PIL import Image
import io
import zipfile

app = Flask(__name__)

@app.route("/pdf-to-images", methods=["POST"])
def pdf_to_images():
    try:
        if "file" not in request.files:
            return jsonify({"error": "Thiếu file PDF trong request"}), 400

        # Nhận file PDF dạng binary từ n8n
        file = request.files["file"]
        pdf_bytes = io.BytesIO(file.read())
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # Chuẩn bị zip để gói ảnh
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for i in range(len(doc)):
                page = doc.load_page(i)
                # Scale lên 300 DPI thực
                pix = page.get_pixmap(matrix=fitz.Matrix(300 / 72, 300 / 72))

                # Dùng Pillow để convert sang JPEG
                img = Image.open(io.BytesIO(pix.tobytes("ppm")))
                img_bytes = io.BytesIO()
                img.save(img_bytes, format="JPEG", quality=95)
                zipf.writestr(f"page_{i + 1}.jpg", img_bytes.getvalue())

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
