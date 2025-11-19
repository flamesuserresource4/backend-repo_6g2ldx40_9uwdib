import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel
from bson.objectid import ObjectId

from database import db, create_document, get_documents
from schemas import Product

app = FastAPI(title="Crafty API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Crafty API is running"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}

@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# ---------- Products API ----------

class ProductCreate(Product):
    pass

class ProductOut(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    price: float
    category: str
    location: Optional[str] = None
    image: Optional[str] = None
    in_stock: bool = True

    class Config:
        from_attributes = True

@app.get("/api/products", response_model=List[ProductOut])
def list_products(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    limit: int = Query(40, ge=1, le=100),
):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    filter_q = {}
    if q:
        filter_q["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}},
            {"location": {"$regex": q, "$options": "i"}},
        ]
    if category:
        filter_q["category"] = {"$regex": f"^{category}$", "$options": "i"}
    price_filter = {}
    if min_price is not None:
        price_filter["$gte"] = min_price
    if max_price is not None:
        price_filter["$lte"] = max_price
    if price_filter:
        filter_q["price"] = price_filter

    docs = get_documents("product", filter_q, limit)
    out = []
    for d in docs:
        d_id = str(d.get("_id")) if d.get("_id") else None
        out.append(ProductOut(
            id=d_id or "",
            name=d.get("name", ""),
            description=d.get("description"),
            price=float(d.get("price", 0)),
            category=d.get("category", ""),
            location=d.get("location"),
            image=d.get("image"),
            in_stock=bool(d.get("in_stock", True)),
        ))
    return out

@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid product id")
    if not doc:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductOut(
        id=str(doc.get("_id")),
        name=doc.get("name", ""),
        description=doc.get("description"),
        price=float(doc.get("price", 0)),
        category=doc.get("category", ""),
        location=doc.get("location"),
        image=doc.get("image"),
        in_stock=bool(doc.get("in_stock", True)),
    )

@app.post("/api/products", response_model=str)
def create_product(payload: ProductCreate):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        new_id = create_document("product", payload)
        return new_id
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------- Seed sample products (utility) ----------

SAMPLE_PRODUCTS = [
    {
        "name": "Block-Printed Dupatta",
        "location": "Jaipur, Rajasthan",
        "price": 1599,
        "image": "https://images.unsplash.com/photo-1685976045770-0562879cff98?ixid=M3w3OTkxMTl8MHwxfHNlYXJjaHwxfHxCbG9jay1QcmludGVkJTIwRHVwYXR0YXxlbnwwfDB8fHwxNzYzNTU5NTY1fDA&ixlib=rb-4.1.0&w=1600&auto=format&fit=crop&q=80",
        "category": "Textiles",
    },
    {
        "name": "Terracotta Vase",
        "location": "Kutch, Gujarat",
        "price": 1299,
        "image": "https://images.unsplash.com/photo-1523419409543-a3215c7beed5?q=80&w=1200&auto=format&fit=crop",
        "category": "Ceramics",
    },
    {
        "name": "Bamboo Basket",
        "location": "Assam",
        "price": 899,
        "image": "https://images.unsplash.com/photo-1519710164239-da123dc03ef4?q=80&w=1200&auto=format&fit=crop",
        "category": "Home",
    },
    {
        "name": "Warli Art Canvas",
        "location": "Maharashtra",
        "price": 2199,
        "image": "https://images.unsplash.com/photo-1580136579312-94651dfd596d?q=80&w=1200&auto=format&fit=crop",
        "category": "Art",
    },
    {
        "name": "Blue Pottery Bowl",
        "location": "Jaipur, Rajasthan",
        "price": 749,
        "image": "https://images.unsplash.com/photo-1616046229478-9901c5536a45?q=80&w=1200&auto=format&fit=crop",
        "category": "Ceramics",
    },
    {
        "name": "Phulkari Shawl",
        "location": "Punjab",
        "price": 1899,
        "image": "https://images.unsplash.com/photo-1685976045770-0562879cff98?ixid=M3w3OTkxMTl8MHwxfHNlYXJjaHwxfHxCbG9jay1QcmludGVkJTIwRHVwYXR0YXxlbnwwfDB8fHwxNzYzNTU5NTY1fDA&ixlib=rb-4.1.0&w=1600&auto=format&fit=crop&q=80",
        "category": "Textiles",
    },
]

@app.post("/api/seed", response_model=int)
def seed_products():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    inserted = 0
    for p in SAMPLE_PRODUCTS:
        # Avoid duplicates by name if already exists
        exists = db["product"].find_one({"name": p["name"]})
        if not exists:
            create_document("product", Product(**p))
            inserted += 1
    return inserted

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
