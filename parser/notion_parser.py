from notion_client import AsyncClient
import json


async def block_parser(block: dict, notion: "AsyncClient")-> dict:
    if block["has_children"]:
        block["children"] = []
        start_cursor = None
        while True:
            if start_cursor is None:
                blocks = await notion.blocks.children.list(block["id"])
            start_cursor = blocks["next_cursor"]
            block["children"].extend(blocks['results'])
            if start_cursor is None:
                break

        for child_block in block["children"]:
            await block_parser(child_block, notion)
    return block
