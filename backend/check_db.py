import asyncio
import os
import re
from motor.motor_asyncio import AsyncIOMotorClient

async def check_markers():
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(uri)
    db = client[os.environ.get("MONGODB_DB", "intecheck")]
    
    doc = await db.raw_extractions.find_one()
    if not doc:
        print("No extractions found in DB.")
        return
    
    markdown = doc.get("markdown", "")
    markers = re.findall(r"<a id='[^']*'></a>", markdown)
    
    print(f"Document Hash: {doc.get('document_hash')}")
    print(f"Found {len(markers)} markers.")
    if markers:
        print(f"First marker: {markers[0]}")
    else:
        print("SAMPLE MARKDOWN (first 500 chars):")
        print(markdown[:500])

if __name__ == "__main__":
    asyncio.run(check_markers())
