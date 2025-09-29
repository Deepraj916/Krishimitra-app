from ml_model.predictor import predict_disease
import os

# Test with a sample image
image_path = os.path.join('static', 'leaf_uploads', 'images.jpg')
if os.path.exists(image_path):
    result = predict_disease(image_path)
    print("Prediction result:")
    print(result)
else:
    print(f"Image not found: {image_path}")
