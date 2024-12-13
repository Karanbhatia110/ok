from flask import Flask, request, render_template, jsonify, send_file, session
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import blue, black, red, Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_LEFT
import os
import google.generativeai as genai 
from reportlab.lib.units import inch
from datetime import datetime
from flask_wtf.csrf import CSRFProtect, generate_csrf
import sqlite3

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Replace with any strong secret key
csrf = CSRFProtect(app)

# Configure Gemini API directly
genai.configure(api_key='AIzaSyBVUkGgmigevSsKAt4eF0fN_3R98Rzlv6k')
model = genai.GenerativeModel('gemini-pro')

# Comment out or remove Razorpay configuration
# razorpay_client = razorpay.Client(
#     auth=('rzp_test_your_key_id', 'rzp_test_your_secret_key')
# )

# Update the font registration part
try:
    base_dir = os.path.abspath(os.path.dirname(__file__))
    pdfmetrics.registerFont(TTFont('CustomHandwriting', 
        os.path.join(base_dir, 'ttf', 'another-shabby.shabby-light.ttf')))
    pdfmetrics.registerFont(TTFont('Desyrel', 
        os.path.join(base_dir, 'ttf', 'Desyrel', 'desyrel.ttf')))
    print("Custom fonts loaded successfully")
except Exception as e:
    print(f"Error loading custom fonts: {str(e)}")
    print("Falling back to default fonts")
    if 'Helvetica' in pdfmetrics._fonts:
        pdfmetrics.registerFont(TTFont('CustomHandwriting', 'Helvetica'))
        pdfmetrics.registerFont(TTFont('Desyrel', 'Helvetica'))

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/input')
def input_page():
    return render_template('input.html')

@app.route('/generate_content', methods=['POST'])
def generate_content():
    try:
        data = request.json
        topic = data['topic']
        pages = int(data['pages'])
        
        # Fixed 28 lines per page
        lines_per_page = 28
        total_lines = pages * lines_per_page
        
        prompt = (f"Write a very detailed assignment on the topic '{topic}'. Requirements:\n"
                 f"1. Must be exactly {total_lines} lines long\n"
                 "2. Each line must have exactly 8 words\n"
                 "3. Each line must be a complete thought\n"
                 "4. Fill ALL the requested lines with meaningful content\n"
                 "5. Content should be evenly distributed across all pages\n"
                 "6. Do not use any asterisks or bullet points\n"
                 "7. Write naturally, as if handwritten\n"
                 f"8. Content must be long enough to fill {pages} pages completely\n"
                 "9. Each line should continue the topic discussion meaningfully")
        
        # Generate content multiple times if needed to fill all pages
        full_content = []
        remaining_lines = total_lines
        
        while remaining_lines > 0:
            response = model.generate_content(prompt)
            content = response.text
            
            # Clean and format the content
            content = content.replace('*', '').replace('•', '').replace('-', '')
            words = content.split()
            
            current_line = []
            for word in words:
                if not word.strip():
                    continue
                
                current_line.append(word)
                
                # Use 8 words per line instead of 7
                if len(current_line) >= 8:
                    full_content.append(' '.join(current_line))
                    current_line = []
                    remaining_lines -= 1
                    if remaining_lines <= 0:
                        break
            
            # If we still have remaining lines, generate more content
            if remaining_lines > 0:
                prompt = (f"Continue the assignment about {topic}. Requirements:\n"
                         f"1. Add {remaining_lines} more lines\n"
                         "2. Each line must have exactly 8 words\n"
                         "3. Each line must be a complete thought\n"
                         "4. Continue the previous discussion naturally\n"
                         "5. Do not repeat previous content")
        
        # Ensure exact number of lines without padding
        if len(full_content) > total_lines:
            full_content = full_content[:total_lines]
        
        content = '\n'.join(full_content)
        return jsonify({'content': content})
            
    except Exception as e:
        print(f"Error generating content: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/output')
def output_page():
    return render_template('output.html')

@app.route('/download')
def download_page():
    return render_template('download.html')

# @app.route('/create-order', methods=['POST'])
# def create_order():
#     try:
#         data = request.json
#         amount = int(float(data['amount']) * 100)  # Convert to paise
        
#         payment_data = {
#             'amount': amount,
#             'currency': 'INR',
#             'receipt': f'order_{datetime.now().timestamp()}',
#             'payment_capture': '1'
#         }
        
#         order = razorpay_client.order.create(data=payment_data)
#         return jsonify({
#             'order_id': order['id'],
#             'amount': amount,
#             'key': 'rzp_test_your_key_id'  # Replace with your Razorpay key ID
#         })
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @app.route('/verify-payment', methods=['POST'])
# def verify_payment():
#     try:
#         payment_data = request.json
#         transaction_id = payment_data.get('transaction_id')
        
#         # Here you would typically verify the transaction ID
#         # For now, we'll accept any transaction ID
#         if transaction_id:
#             session['payment_verified'] = True
#             return jsonify({'status': 'success'})
#         return jsonify({'status': 'failed', 'error': 'Invalid transaction ID'}), 400
#     except Exception as e:
#         return jsonify({'status': 'failed', 'error': str(e)}), 400

@app.route('/get-csrf-token')
def get_csrf_token():
    return jsonify({'csrf_token': generate_csrf()})

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    try:
        data = request.json
        content = data['content']
        font = data['font']
        pen_color = data['penColor']
        layout = data['layout']

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)

        # Set custom blue color using hex value #3333ff
        custom_blue = Color(0x33/255, 0x33/255, 0xff/255)
        
        color = {
            'blue': custom_blue,
            'black': black,
            'red': red
        }.get(pen_color, black)

        # Page dimensions and spacing
        page_width, page_height = letter
        top_margin = page_height - (1.5 * inch)
        left_margin = 1.35 * inch
        bottom_margin = inch
        usable_height = top_margin - bottom_margin

        # Fixed 28 lines per page with adjusted line height
        lines_per_page = 28
        line_height = (usable_height / (lines_per_page - 1)) * 1.2  # Added back the 1.2 multiplier for more spacing

        # Set font size
        font_size = 16

        background_path = {
            'lined': os.path.join('images', 'lined.png'),
            'grid': os.path.join('images', 'grid-background.png')
        }.get(layout)

        # Clean and split content into lines
        cleaned_content = content.replace('*', '').replace('•', '').strip()
        lines = [line.strip() for line in cleaned_content.split('\n') if line.strip()]
        current_line = 0
        total_lines = len(lines)

        while current_line < total_lines:
            if background_path and os.path.exists(background_path):
                p.drawImage(background_path, 0, 0, width=page_width, height=page_height)
            
            y = top_margin

            for _ in range(lines_per_page):
                if current_line >= total_lines:
                    break

                clean_line = lines[current_line]
                if clean_line:
                    p.setFont(font, font_size)  # Using font size 18
                    p.setFillColor(color)
                    p.drawString(left_margin, y, clean_line)
                
                y -= line_height
                current_line += 1

            if current_line < total_lines:
                p.showPage()

        p.save()
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name='assignment.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)