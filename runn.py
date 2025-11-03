from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from predict import predict  # from the GitHub repo's predict.py
import tempfile

app = Flask(__name__)
CORS(app)

@app.route("/predict", methods=["POST"])
def handle_predict():
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        file.save(tmp.name)
        prediction = predict(tmp.name)
        os.unlink(tmp.name)

    return jsonify({"chords": prediction})

if __name__ == "__main__":
    app.run(debug=True)
