from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import rembg
from PIL import Image
import io
import uvicorn

app = FastAPI(title="Background Remover API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize rembg session
rembg_session = rembg.new_session('u2net')

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
        
        # Read uploaded file
        contents = await file.read()
        
        # Process image with rembg
        input_image = contents
        output_image = rembg.remove(input_image, session=rembg_session)
        
        # Return processed image
        return Response(
            content=output_image,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=removed_bg_{file.filename}",
                "Access-Control-Expose-Headers": "Content-Disposition"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
