import asyncio
import os
import sys
import getopt
import json
import logging

from notion_client import AsyncClient
from dotenv import load_dotenv

from parser.frontmatter_parser import parse_frontmatter
from parser.markdown_parser import parse_markdown
from parser.notion_parser import parse_blocks
from parser.utils import slugify

load_dotenv()

semaphore = asyncio.Semaphore(3)
notion = AsyncClient(
    auth=os.environ["NOTION_TOKEN"],
    log_level=logging.INFO,
)


async def download_page(page_id, path):
    async with semaphore:
        page = await notion.pages.retrieve(page_id)
        blocks = await notion.blocks.children.list(page_id)

        page = parse_frontmatter(page)
        results = []
        for block in blocks["results"]:
            block = await parse_blocks(block, notion)
            results.append(block)
        blocks["results"] = results

        title = slugify(page["properties"]["Name"]["title"][0]["plain_text"])
        page_md = parse_markdown(page_id, blocks, page["frontmatter"])
        page_json = json.dumps(page, indent=2)
        block_json = json.dumps(blocks, indent=2)

        if not os.path.exists(f"build/{path}/{page_id}"):
            os.makedirs(f"build/{path}/{page_id}")
        if not os.path.exists(f"build/{path}/_markdown"):
            os.makedirs(f"build/{path}/_markdown")

        with open(f"build/{path}/{page_id}/page.json", "w") as f:
            f.write(page_json)
        with open(f"build/{path}/{page_id}/block.json", "w") as f:
            f.write(block_json)
        with open(f"build/{path}/{page_id}/{title}.md", "w") as f:
            f.write(page_md)
        with open(f"build/{path}/_markdown/{title}.md", "w") as f:
            f.write(page_md)


async def parallel_download_pages(path, pages):
    page_ids = [page["id"] for page in pages["results"]]
    tasks = [download_page(page_id, path) for page_id in page_ids]
    await asyncio.gather(*tasks)


async def download_database(path, database_id):
    pages = None
    start_cursor = None
    # pages = await notion.databases.query(database_id=database_id)

    while True:
        if start_cursor is None:
            pages = await notion.databases.query(database_id=database_id)
            await parallel_download_pages(path, pages)
        else:
            pages = await notion.databases.query(database_id=database_id, start_cursor=start_cursor)
            await parallel_download_pages(path, pages)
        if pages:
            start_cursor = pages['next_cursor']
            if start_cursor is None:
                break


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
    print(str(err))
