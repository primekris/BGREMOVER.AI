from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Background Remover API",
    description="Remove backgrounds from images using simple color detection",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    Remove background from uploaded image using simple color detection
    """
    try:
        # Validate file type
        if not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Read the uploaded file
        contents = await file.read()
        logger.info(f"Processing image: {file.filename}, size: {len(contents)} bytes")
        
        # Process image with simple background removal
        input_image = Image.open(io.BytesIO(contents))
        
        # Convert to RGBA if not already
        if input_image.mode != 'RGBA':
            input_image = input_image.convert('RGBA')
        
        # Simple background removal using color similarity
        output_image = simple_background_removal(input_image)
        
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

def simple_background_removal(image):
    """
    Simple background removal using color similarity
    Works best with solid or simple backgrounds
    """
    # Convert to RGB for processing
    rgb_image = image.convert('RGB')
    rgba_image = image.convert('RGBA')
    
    # Get image dimensions
    width, height = rgb_image.size
    
    # Sample corner pixels to determine background color
    corners = [
        rgb_image.getpixel((0, 0)),
        rgb_image.getpixel((width-1, 0)),
        rgb_image.getpixel((0, height-1)),
        rgb_image.getpixel((width-1, height-1))
    ]
    
    # Use the most common corner color as background
    from collections import Counter
    bg_color = Counter(corners).most_common(1)[0][0]
    
    # Create new image with transparent background
    new_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    # Tolerance for color matching (adjust for better results)
    tolerance = 40
    
    for x in range(width):
        for y in range(height):
            pixel = rgb_image.getpixel((x, y))
            
            # Calculate color difference
            diff = sum(abs(pixel[i] - bg_color[i]) for i in range(3))
            
            if diff > tolerance:
                # Keep original pixel
                new_image.putpixel((x, y), rgba_image.getpixel((x, y)))
            # else: leave transparent (already set)
    
    return new_image

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# ... your existing imports and route handlers

# This mounts the root folder so static files like index.html can be served
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# 👇 Mount current directory (so it can serve index.html or CSS, JS, etc.)
app.mount("/static", StaticFiles(directory="."), name="static")

# 👇 Serve index.html when someone visits the base URL (e.g., /)
@app.get("/")
async def serve_homepage():
    return FileResponse("index.html")
