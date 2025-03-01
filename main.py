from flask import Flask, request, jsonify, send_file, render_template_string
from google.cloud import vision
import os
from flask_cors import CORS
import re
import csv
from io import StringIO
import toastify

app = Flask(__name__)
CORS(app)

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\ADMIN\OneDrive\Desktop\Practice 2\Google_ocr\original\service-account-file.json"
client = vision.ImageAnnotatorClient()

# Store extracted roll numbers with attendance status
extracted_roll_numbers = {}

@app.route('/')
def serve_frontend():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Attendance System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/toastify-js/src/toastify.min.css">
    <style>
        body {
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            font-family: 'Arial', sans-serif;
        }
        .container {
            background: white;
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            max-width: 900px;
            width: 100%;
            text-align: center;
        }
        .drag-area {
            border: 3px dashed #007bff;
            padding: 40px;
            cursor: pointer;
            border-radius: 10px;
            background: #f8f9fa;
            transition: 0.3s;
            font-size: 1.2rem;
            font-weight: bold;
            color: #007bff;
        }
        .drag-area:hover {
            background: #e9ecef;
        }
        .preview-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
            justify-content: center;
        }
        .preview-container img {
            width: 80px;
            height: 80px;
            object-fit: cover;
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
            border: 2px solid #007bff;
        }
        .btn-primary {
            margin-top: 15px;
        }
        #loading {
            display: none;
        }

        /* Style for the toggle button */
        .btn-toggle {
            background-color: #28a745; /* Green for Present */
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }

        .btn-toggle.absent {
            background-color: #dc3545; /* Red for Absent */
        }

        .btn-toggle:hover {
            opacity: 0.9;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1 class="text-center"><i class="fas fa-users"></i> Student Attendance System</h1>

        <!-- Class Management Section -->
        <div class="class-management mb-4">
            <div class="btn-group" role="group">
                <button onclick="createClass()" class="btn btn-success"><i class="fas fa-plus"></i> Create Class</button>
                <button onclick="deleteClass()" class="btn btn-danger"><i class="fas fa-trash"></i> Delete Class</button>
            </div>
            <select id="classSelect" class="form-select mt-3" onchange="loadClass()">
                <option value="">Select a Class</option>
                <!-- Classes will be populated here dynamically -->
            </select>
        </div>

        <!-- Drag and Drop Area -->
        <div class="drag-area" id="dragArea">Drag & Drop Images Here or Click to Upload</div>
        <input type="file" id="fileInput" accept=".jpg, .jpeg, .png" multiple class="form-control d-none">
        <div class="preview-container" id="previewContainer"></div>
        <button onclick="uploadFiles()" class="btn btn-primary w-100"><i class="fas fa-upload"></i> Upload</button>
        <div id="loading" class="mt-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p>Processing images...</p>
        </div>

        <!-- Search Bar -->
        <input type="text" id="searchInput" class="form-control mt-3" placeholder="Search by Roll Number" oninput="filterStudents()">

        <!-- Result Section -->
        <div id="result"></div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/toastify-js"></script>
    <script>
        const dragArea = document.getElementById('dragArea');
        const fileInput = document.getElementById('fileInput');
        const previewContainer = document.getElementById('previewContainer');
        
        dragArea.addEventListener('click', () => fileInput.click());
        dragArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dragArea.style.background = '#e9ecef';
        });
        dragArea.addEventListener('dragleave', () => dragArea.style.background = '#f8f9fa');
        dragArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dragArea.style.background = '#f8f9fa';
            handleFiles(e.dataTransfer.files);
        });
        fileInput.addEventListener('change', (e) => handleFiles(e.target.files));

        function handleFiles(files) {
            previewContainer.innerHTML = '';
            for (const file of files) {
                const img = document.createElement('img');
                img.src = URL.createObjectURL(file);
                previewContainer.appendChild(img);
            }
        }

        let classes = {}; // Object to store classes and their attendance data

        // Function to create a new class
        function createClass() {
            const className = prompt("Enter the name of the new class:");
            if (className && !classes[className]) {
                classes[className] = {};
                updateClassSelect();
                showNotification(`Class "${className}" created successfully.`, 'success');
            } else if (classes[className]) {
                showNotification("Class already exists.", 'error');
            }
        }

        // Function to delete a class
        function deleteClass() {
            const className = document.getElementById('classSelect').value;
            if (className && confirm(`Are you sure you want to delete class "${className}"?`)) {
                delete classes[className];
                updateClassSelect();
                showNotification(`Class "${className}" deleted successfully.`, 'success');
            } else if (!className) {
                showNotification("Please select a class to delete.", 'error');
            }
        }

        // Function to update the class select dropdown
        function updateClassSelect() {
            const classSelect = document.getElementById('classSelect');
            classSelect.innerHTML = '<option value="">Select a Class</option>';
            for (const className in classes) {
                const option = document.createElement('option');
                option.value = className;
                option.textContent = className;
                classSelect.appendChild(option);
            }
        }

        // Function to load a selected class
        function loadClass() {
            const className = document.getElementById('classSelect').value;
            if (className && classes[className]) {
                let resultHtml = '<h4><i class="fas fa-list-ol"></i> Extracted Roll Numbers</h4>';
                resultHtml += '<table class="table"><tr><th>Roll Number</th><th>Status</th><th>Actions</th></tr>';
                Object.entries(classes[className]).forEach(([roll, status]) => {
                    resultHtml += `
                        <tr>
                            <td>${roll}</td>
                            <td id="status-${roll}">${status}</td>
                            <td>
                                <button class="btn-toggle ${status === 'Present' ? '' : 'absent'}" onclick="markPresent('${roll}')">
                                    ${status === 'Present' ? 'Mark Absent' : 'Mark Present'}
                                </button>
                            </td>
                        </tr>`;
                });
                resultHtml += '</table>';
                document.getElementById('result').innerHTML = resultHtml;
            } else {
                document.getElementById('result').innerHTML = '';
            }
        }

        // Modify the uploadFiles function to save data to the selected class
        async function uploadFiles() {
            const className = document.getElementById('classSelect').value;
            if (!className) {
                showNotification("Please select a class before uploading.", 'error');
                return;
            }
            if (!fileInput.files.length) {
                showNotification("Please select at least one file.", 'error');
                return;
            }
            document.getElementById('loading').style.display = 'block';
            const formData = new FormData();
            for (const file of fileInput.files) {
                formData.append('files', file);
            }
            try {
                const response = await fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                if (data.results) {
                    classes[className] = data.attendance;
                    loadClass();
                    showNotification("Attendance data uploaded successfully.", 'success');
                } else {
                    document.getElementById('result').innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                    showNotification(data.error, 'error');
                }
            } catch (error) {
                document.getElementById('result').innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
                showNotification("An error occurred while uploading files.", 'error');
            } finally {
                document.getElementById('loading').style.display = 'none';
            }
        }

        // Function to toggle student attendance status
        async function markPresent(rollNumber) {
            const className = document.getElementById('classSelect').value;
            if (className && classes[className][rollNumber]) {
                // Toggle the status between "Present" and "Absent"
                classes[className][rollNumber] = classes[className][rollNumber] === 'Present' ? 'Absent' : 'Present';

                // Update the status in the table
                document.getElementById(`status-${rollNumber}`).innerText = classes[className][rollNumber];

                // Update the button text and class
                const button = document.querySelector(`button[onclick="markPresent('${rollNumber}')"]`);
                if (button) {
                    button.textContent = classes[className][rollNumber] === 'Present' ? 'Mark Absent' : 'Mark Present';
                    button.classList.toggle('absent', classes[className][rollNumber] === 'Absent');
                }

                // Show notification
                showNotification(`Roll number ${rollNumber} marked as ${classes[className][rollNumber]}.`, 'success');
            }
        }

        // Function to filter students by roll number
        function filterStudents() {
            const searchQuery = document.getElementById('searchInput').value.toLowerCase();
            const rows = document.querySelectorAll('#result table tr');
            rows.forEach((row, index) => {
                if (index === 0) return; // Skip header row
                const rollNumber = row.cells[0].textContent.toLowerCase();
                if (rollNumber.includes(searchQuery)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        // Function to show notifications
        function showNotification(message, type = 'success') {
            Toastify({
                text: message,
                duration: 3000,
                close: true,
                gravity: 'top',
                position: 'right',
                backgroundColor: type === 'success' ? '#28a745' : '#dc3545',
            }).showToast();
        }
    </script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/js/all.min.js"></script>
</body>
</html>

"""

@app.route('/api/upload', methods=['POST'])
def upload_images():
    if 'files' not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "No files selected"}), 400

    results = []

    for file in files:
        try:
            image_content = file.read()
            if not image_content:
                results.append({"file": file.filename, "error": "Empty file uploaded"})
                continue

            image = vision.Image(content=image_content)
            response = client.text_detection(image=image)
            texts = response.text_annotations

            if not texts:
                results.append({"file": file.filename, "error": "No text detected"})
                continue

            extracted_text = texts[0].description
            cleaned_text = re.sub(r"[^0-9, ]", "", extracted_text)
            cleaned_text = ", ".join(set(cleaned_text.split()))
            for num in cleaned_text.split(", "):
                extracted_roll_numbers[num] = "Present"

            results.append({"file": file.filename, "text": cleaned_text})

        except Exception as e:
            results.append({"file": file.filename, "error": str(e)})

    return jsonify({"results": results, "attendance": extracted_roll_numbers})

@app.route('/api/mark_present', methods=['POST'])
def mark_present():
    data = request.json
    roll_number = data.get("roll_number")
    if roll_number in extracted_roll_numbers:
        extracted_roll_numbers[roll_number] = "Present"
        return jsonify({"success": True, "message": f"Roll number {roll_number} marked as Present"})
    return jsonify({"success": False, "message": "Roll number not found"}), 400

@app.route('/api/export', methods=['GET'])
def export_csv():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll Number", "Status"])
    for number, status in sorted(extracted_roll_numbers.items()):
        writer.writerow([number, status])
    output.seek(0)
    return send_file(StringIO(output.getvalue()), mimetype="text/csv", as_attachment=True, download_name="attendance.csv")

if __name__ == '__main__':
    app.run(debug=True, port=5500)
