from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from rembg import remove
import io
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Background Remover API",
    description="Remove backgrounds from images using rembg",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Background Remover API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/remove")
async def remove_background(file: UploadFile = File(...)):
    """
    Remove background from uploaded image
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read the uploaded file
        contents = await file.read()
        logger.info(f"Processing image: {file.filename}, size: {len(contents)} bytes")
        
        # Process image with rembg
        input_image = Image.open(io.BytesIO(contents))
        
        # Remove background
        output_image = remove(input_image)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        output_image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        logger.info("Background removal completed successfully")
        
        # Return the processed image
        return StreamingResponse(
            io.BytesIO(img_byte_arr.read()),
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=no_bg_{file.filename.split('.')[0]}.png"
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
