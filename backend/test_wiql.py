import asyncio
import httpx
import os
from dotenv import load_dotenv
import base64

load_dotenv('backend/.env')

async def main():
    org = os.getenv('ADO_ORG_URL', '').rstrip('/')
    proj = os.getenv('ADO_PROJECT')
    credential = os.getenv('ADO_CREDENTIAL')
    auth = base64.b64encode(f':{credential}'.encode()).decode()
    headers = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}
    url = f'{org}/{proj}/_apis/wit/wiql?api-version=7.1'
    q = {'query': f"SELECT [System.Id] FROM workitems WHERE [System.TeamProject] = '{proj}'"}
    
    print(f"URL: {url}")
    async with httpx.AsyncClient() as c:
        res = await c.post(url, json=q, headers=headers)
        print(f"Status: {res.status_code}")
        print(f"Response: {repr(res.text)}")

asyncio.run(main())
