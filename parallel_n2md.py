import asyncio
import os
import sys
import getopt
import json

from notion_client import AsyncClient
from dotenv import load_dotenv

load_dotenv()

notion = AsyncClient(auth=os.environ["NOTION_TOKEN"])

async def download_page(page_id, path):
    page = await notion.pages.retrieve(page_id)
    blocks = await notion.blocks.children.list(page_id)
    title = page["properties"]["Name"]["title"][0]["plain_text"]

    # for result in blocks["results"]:
    #     if result["has_children"]:
    #         result_json = json.dumps(result, indent=2)
    #         print(result_json)

    page_json = json.dumps(page, indent=2)
    blocks_json = json.dumps(blocks, indent=2)

    if not os.path.exists(f"build/{path}/{title}"):
        os.makedirs(f"build/{path}/{title}")
    with open(f"build/{path}/{title}/page.json", "w") as f:
        f.write(page_json)
    with open(f"build/{path}/{title}/blocks.json", "w") as f:
        f.write(blocks_json)

async def download_database(path, database_id):
    pages = await notion.databases.query(database_id=database_id)
    page_ids = [page["id"] for page in pages["results"]]
    tasks = [download_page(page_id, path) for page_id in page_ids]
    await asyncio.gather(*tasks)


argv = sys.argv[1:]
try:
    opts, args = getopt.getopt(argv, 'p:d:', ['path', 'database_id'])
    path = ""
    database_id = ""
    for arg, val in opts:
        if arg in ("-p", "--path"):
            path = val
        if arg in ("-d", "--database_id"):
            database_id = val
    asyncio.run(download_database(path, database_id))

except getopt.error as err:
    print (str(err))
