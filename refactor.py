import os
import ast
from collections import defaultdict

with open("main.py", "r", encoding="utf-8") as f:
    source = f.read()

lines = source.split("\n")
tree = ast.parse(source)

routers = defaultdict(list)
core_deps = []
core_utils = []
main_nodes = []
node_ranges_to_remove = []

def get_start_line(node):
    if hasattr(node, 'decorator_list') and node.decorator_list:
        return min(d.lineno for d in node.decorator_list) - 1
    return node.lineno - 1

def extract_node_lines(node):
    start_line = get_start_line(node)
    return lines[start_line:node.end_lineno], start_line, node.end_lineno

ROUTER_MAP = {
    "auth": "auth",
    "token": "auth",
    "user": "auth",
    "leads": "leads",
    "admin": "leads",
    "autobid": "autobid",
    "bid": "autobid",
    "sync-receive": "sync",
    "sync-send": "sync",
    "n8n": "sync",
    "fetch-upwork": "fetch",
    "fetch-freelancer": "fetch",
    "fetch-freelancer-plus": "fetch",
    "fetch-limits": "fetch",
    "profile": "users",
    "settings": "users",
    "projects": "users",
    "crm": "users",
    "notifications": "users",
    "dashboard": "users",
    "message": "users",
    "freelancer": "users",  
    "talents": "users",
    "proposal": "users",
}

DEPENDENCY_FUNCS = ["get_db", "get_user_by_email", "get_system_settings", "check_and_reset_daily_limit", "verify_admin", "prepare_freelancer_request"]
UTILS_FUNCS = ["extract_category_from_text", "start_cache_cleanup", "extract_category_from_url", "init_db", "trigger_webhook_async", "_check_db_status"]

for node in tree.body:
    moved = False
    
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name in UTILS_FUNCS:
            node_lines, start, end = extract_node_lines(node)
            core_utils.extend(node_lines)
            core_utils.append("")
            node_ranges_to_remove.append((start, end))
            moved = True
            continue
            
        if node.name in DEPENDENCY_FUNCS:
            node_lines, start, end = extract_node_lines(node)
            core_deps.extend(node_lines)
            core_deps.append("")
            node_ranges_to_remove.append((start, end))
            moved = True
            continue

        is_route = False
        router_name = "misc"
        
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and getattr(decorator.func.value, 'id', '') == 'app':
                if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                    is_route = True
                    try:
                        path_val = decorator.args[0].value
                        parts = path_val.split('/')
                        if len(parts) > 2:
                            prefix = parts[2]
                            router_name = ROUTER_MAP.get(prefix, prefix)
                        elif len(parts) == 2 and parts[1] == "":
                             # e.g "/""
                            router_name = "health"
                    except:
                        pass
        
        if is_route:
            node_lines, start, end = extract_node_lines(node)
            routers[router_name].extend(node_lines)
            routers[router_name].append("")
            node_ranges_to_remove.append((start, end))
            moved = True

os.makedirs("routers", exist_ok=True)
os.makedirs("core", exist_ok=True)

with open("routers/__init__.py", "w") as f:
    pass
with open("core/__init__.py", "w") as f:
    pass

COMMON_IMPORTS = """from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text, Float, case
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
import os
import re
import json
from urllib.parse import unquote
import time

from database import engine, SessionLocal
from models import *
from schemas import *
from core.dependencies import get_db, get_user_by_email, get_system_settings, check_and_reset_daily_limit, verify_admin, prepare_freelancer_request
from core.utils import extract_category_from_text, start_cache_cleanup, extract_category_from_url, init_db, trigger_webhook_async, _check_db_status
from auth import get_password_hash, verify_password, create_access_token, verify_token, SECRET_KEY, ALGORITHM
"""

with open("core/utils.py", "w", encoding="utf-8") as f:
    f.write("import threading\nimport time\nimport re\nimport httpx\nfrom cache_utils import cached, cleanup_cache\nfrom database import SessionLocal\n\n")
    f.write("\n".join(core_utils))

with open("core/dependencies.py", "w", encoding="utf-8") as f:
    f.write("from fastapi import HTTPException, Depends\nfrom sqlalchemy.orm import Session\nfrom datetime import datetime\nfrom sqlalchemy import func\nimport json\nfrom models import *\nfrom auth import verify_token\nfrom database import SessionLocal\n\n")
    f.write("\n".join(core_deps))

for router_name, content in routers.items():
    with open(f"routers/{router_name}.py", "w", encoding="utf-8") as f:
        f.write(COMMON_IMPORTS)
        f.write(f"\nrouter = APIRouter()\n\n")
        for line in content:
            if line.strip().startswith("@app."):
                if "on_event" not in line:
                    line = line.replace("@app.", "@router.")
            f.write(line + "\n")

new_main_lines = []
skip_ranges = sorted(node_ranges_to_remove)

curr_idx = 0
for start, end in skip_ranges:
    while curr_idx < start:
        new_main_lines.append(lines[curr_idx])
        curr_idx += 1
    curr_idx = end

while curr_idx < len(lines):
    new_main_lines.append(lines[curr_idx])
    curr_idx += 1

insert_idx = 0
for i, line in enumerate(new_main_lines):
    if "app = FastAPI(" in line or "app=FastAPI(" in line or line.startswith("app = FastAPI"):
        insert_idx = i + 1
        break

router_includes = ["\n"]
for router_name in routers.keys():
    router_includes.append(f"from routers.{router_name} import router as {router_name.replace('-', '_')}_router")
    router_includes.append(f"app.include_router({router_name.replace('-', '_')}_router)")
router_includes.append("\n")

new_main_source = "\n".join(new_main_lines[:insert_idx]) + "\n" + "\n".join(router_includes) + "\n" + "\n".join(new_main_lines[insert_idx:])

# Ensure pydantic BaseModel import remains if it was removed
if "class BidRequest" in new_main_source or "from pydantic import BaseModel" not in new_main_source:
    new_main_source = "from pydantic import BaseModel\n" + new_main_source


with open("main_new.py", "w", encoding="utf-8") as f:
    f.write(new_main_source)

print(f"Extraction complete! Routers generated: {list(routers.keys())}")
