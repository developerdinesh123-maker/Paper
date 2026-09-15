
import os, json, base64
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import fitz
from openai import OpenAI

load_dotenv()
app = FastAPI(title="Invoice Intelligence")
BASE = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")

def pdf_to_text(data):
    doc = fitz.open(stream=data, filetype="pdf")
    return "\n\n".join(page.get_text("text") for page in doc).strip()

def image_to_data_url(data, content_type):
    return f"data:{content_type};base64,{base64.b64encode(data).decode()}"

def get_client():
    token=os.getenv("GITHUB_TOKEN")
    if not token: raise HTTPException(500,"GITHUB_TOKEN is not configured")
    return OpenAI(api_key=token, base_url=os.getenv("GITHUB_MODELS_BASE_URL","https://models.github.ai/inference"))

def extract_with_ai(request, docs):
    client=get_client()
    model=os.getenv("GITHUB_MODEL","openai/gpt-4.1-mini")
    system='''You are a careful invoice and logistics document extraction agent.
The user provides a natural-language extraction request and one or more documents.
Invoice fields may come from invoices; net weight/gross weight/package information may come from packing lists.
Return ONLY valid JSON:
{"records":[{"source_documents":[],"fields":{},"confidence":0.0,"warnings":[]}]}
Never invent values. Use null when absent. Preserve numbers and units when possible.
If multiple documents refer to the same shipment/invoice, reconcile them into one record.'''
    content=[{"type":"text","text":f"USER REQUEST:\n{request}\n\nDOCUMENTS:"}]
    for d in docs:
        content.append({"type":"text","text":f"\n--- {d['name']} ---\n{d.get('text','')}"})
        if d.get("image"):
            content.append({"type":"image_url","image_url":{"url":d["image"]}})
    r=client.chat.completions.create(
        model=model,
        messages=[{"role":"system","content":system},{"role":"user","content":content}],
        temperature=0
    )
    raw=(r.choices[0].message.content or "{}").strip()
    if raw.startswith("```"):
        raw=raw.split("```",2)[1].removeprefix("json").strip()
    try: return json.loads(raw)
    except Exception: raise HTTPException(502,"AI returned invalid JSON")

@app.get("/",response_class=HTMLResponse)
def home():
    return open(os.path.join(BASE,"static","index.html"),encoding="utf-8").read()

@app.get("/api/health")
def health(): return {"ok":True}

@app.post("/api/extract")
async def extract(request: str=Form(...), files: List[UploadFile]=File(...)):
    if not request.strip(): raise HTTPException(400,"Describe the data you want extracted.")
    docs=[]; limit=float(os.getenv("MAX_FILE_MB","20"))*1024*1024
    for f in files:
        data=await f.read()
        if len(data)>limit: raise HTTPException(413,f"{f.filename} is too large")
        ct=f.content_type or ""
        if f.filename.lower().endswith(".pdf") or ct=="application/pdf":
            docs.append({"name":f.filename,"text":pdf_to_text(data)[:120000]})
        elif ct.startswith("image/") or f.filename.lower().endswith((".png",".jpg",".jpeg",".webp")):
            docs.append({"name":f.filename,"text":"","image":image_to_data_url(data,ct or "image/jpeg")})
        else: raise HTTPException(400,f"Unsupported file: {f.filename}")
    return JSONResponse(extract_with_ai(request,docs))
