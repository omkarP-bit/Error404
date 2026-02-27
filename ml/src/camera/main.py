from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import cv2
import numpy as np
from PIL import Image
import io
import uvicorn

app = FastAPI(title="Camera Service", version="1.0.0")

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "camera"}

@app.post("/process-receipt")
async def process_receipt(file: UploadFile = File(...)):
    try:
        # Read image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))
        
        # Convert to OpenCV format
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Basic image processing for receipt scanning
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
        
        # Edge detection for receipt boundaries
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find largest rectangular contour (receipt)
        receipt_contour = None
        max_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > max_area:
                # Approximate contour to polygon
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                if len(approx) == 4:  # Rectangle
                    receipt_contour = approx
                    max_area = area
        
        result = {
            "processed": True,
            "receipt_detected": receipt_contour is not None,
            "image_size": {"width": cv_image.shape[1], "height": cv_image.shape[0]}
        }
        
        if receipt_contour is not None:
            # Extract corner points
            corners = receipt_contour.reshape(4, 2).tolist()
            result["corners"] = corners
        
        return JSONResponse(content=result)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "processed": False}
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)