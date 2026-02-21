from fastapi import FastAPI, Request, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import processor
import os
import time

app = FastAPI()

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Ensure downloads directory exists
if not os.path.exists("downloads"):
    os.makedirs("downloads")

def cleanup_file(filepath: str):
    """Wait and delete the file after 5 minutes."""
    time.sleep(300) 
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"Cleaned up {filepath}")
        except Exception as e:
            print(f"Error cleaning up {filepath}: {e}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        return f"<h1>Deployment Error</h1><p>Error: {str(e)}</p><p>Current Files: {os.listdir('.')}</p><p>Templates Folder Content: {os.listdir('templates') if os.path.exists('templates') else 'FOLDER MISSING'}</p>"

@app.post("/info")
async def get_info(url: str = Form(...)):
    info = processor.get_video_info(url)
    return info

@app.post("/trim")
async def process_video(
    background_tasks: BackgroundTasks, 
    url: str = Form(...), 
    start: str = Form(None), 
    end: str = Form(None),
    quality: int = Form(720),
    mode: str = Form("trim")
):
    try:
        # Pass parameters to the new unified processor
        res = processor.process_video(url, mode, start, end, quality)
        
        if isinstance(res, dict) and "error" in res:
            return {"error": f"Processing failed: {res['error']}"}
            
        if res and os.path.exists(res):
            # Schedule cleanup
            background_tasks.add_task(cleanup_file, res)
            
            # Determine filename extension based on mode
            filename = os.path.basename(res)
            return FileResponse(
                path=res,
                filename=filename,
                media_type='video/mp4' # We always use MP4 container even for audio (aac inside)
            )
        return {"error": "Failed to process video: Unknown error"}
    except Exception as e:
        return {"error": f"Unexpected server error: {str(e)}"}

@app.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    return "User-agent: *\nAllow: /\nSitemap: http://localhost:8000/sitemap.xml"

@app.get("/sitemap.xml")
async def sitemap():
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
   <url>
      <loc>http://localhost:8000/</loc>
      <lastmod>2026-02-21</lastmod>
      <changefreq>monthly</changefreq>
      <priority>1.0</priority>
   </url>
</urlset>"""
    return Response(content=xml_content, media_type="application/xml")

if __name__ == "__main__":
    import uvicorn
    # Default to 8000 for local, cloud envs will override via PORT env var
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
