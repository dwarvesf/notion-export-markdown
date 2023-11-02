## Notion Export Markdown

This is our internal tool to convert Notion pages to markdown. It is loosely based off of [notion4ever](https://github.com/MerkulovDaniil/notion4ever). Most of the code from notion4ever that is used to parse the Notion objects to markdown is kept as-is with some few tweaks.


### Differences from notion4ever

[notion4ever](https://github.com/MerkulovDaniil/notion4ever) mutates a `notion_content.json` file, before structuring it with `notion_structured.json`. This is so it can process blocks and pages + images in one go. However, this means it can only download blocks, pages, and databases one at a time as it must update those files synchronously. This is considerably slow for large Notion databases like our [memo](https://memo.d.foundation/1f6986deb0db47769ddd7e9012699740). On top of that, Notion images expire after 1 hour as they are accessed through presigned URLs from Amazon's S3 storage, meaning even if we finished downloading Notion metadata, it would be mostly unusable without those images.

Our implementation simplifies a few things:
- Everything is processed in memory and we just dump `page.json` and `blocks.json` files for reference.
- We only update blocks to include nested pages/blocks to keep track of content
- We do **parallel downloads** using `asyncio`
- We **don't** download the images directly, and instead use the [`obsidian-local-images-plus`](https://github.com/Sergei-Korneev/obsidian-local-images-plus) extension on Obsidian to do that for us


## Getting started

This repository uses devcontainers to setup the environment for Python. We recommend using Python 3.10 as versions after this do not support `asyncio` and `aiohttp` since there are no build support for `wheels`. Refer to [VSCode's developing inside a devcontainer](https://code.visualstudio.com/docs/devcontainers/containers) to get started with devcontainers, or you can open it with [DevPod](https://devpod.sh/):

[![Open in DevPod!](https://devpod.sh/assets/open-in-devpod.svg)](https://devpod.sh/open#https://github.com/dwarvesf/notion-export-markdown)

### Exporting an example Notion Database:

Export the `NOTION_TOKEN` environment variable in your current shell, or create a `.env` file with your token:

```
NOTION_TOKEN=...
```

Then we run the command on `parallel_n2md.py` and specify our output path (`-p`) and database ID (`-d`). The files will be built in the `build` folder.

For instance, we will output the markdown files in the `./build/memo/_markdown` folder with our [memo](https://memo.d.foundation/1f6986deb0db47769ddd7e9012699740) Notion page database ID being `1f6986deb0db47769ddd7e9012699740`

```
python parallel_n2md.py -p memo -d 1f6986deb0db47769ddd7e9012699740
```
