import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__)))
from services.ado_service import AzureDevOpsService

async def main():
    s = AzureDevOpsService()
    try:
        res = await s.get_all_work_items()
        print(res)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
