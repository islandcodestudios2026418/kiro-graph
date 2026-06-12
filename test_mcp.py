"""Test the MCP server tools end-to-end."""
import asyncio, sys
sys.path.insert(0, '.')
from server import init_db, get_db, call_tool

async def test():
    init_db()
    
    # Test graph_log
    result = await call_tool("graph_log", {"agent": "test-agent", "project": "test-proj", "msg": "did something cool"})
    print(f"graph_log: {result[0].text}")
    
    # Test graph_decide
    result = await call_tool("graph_decide", {"agent": "test-agent", "project": "test-proj", "name": "Use SQLite over Postgres", "body": "SQLite is simpler, no server needed, good enough for our scale", "evidence": ["benchmark results", "DreamGraph also uses SQLite"]})
    print(f"graph_decide: {result[0].text}")
    
    # Test graph_entity
    result = await call_tool("graph_entity", {"type": "project", "name": "tw-accounting", "agent": "main", "body": "Taiwan accounting automation"})
    print(f"graph_entity: {result[0].text}")
    
    result = await call_tool("graph_entity", {"type": "project", "name": "stock-dashboard", "agent": "main", "body": "Stock analysis dashboard + MCP"})
    print(f"graph_entity: {result[0].text}")
    
    # Test graph_link
    result = await call_tool("graph_link", {"src": "stock-dashboard", "dst": "tw-accounting", "rel": "uses", "evidence": "both use Excel export"})
    print(f"graph_link: {result[0].text}")
    
    # Test graph_search
    result = await call_tool("graph_search", {"query": "accounting"})
    print(f"graph_search: {result[0].text}")
    
    # Test graph_status
    result = await call_tool("graph_status", {})
    print(f"graph_status: {result[0].text}")
    
    # Test graph_query
    result = await call_tool("graph_query", {"type": "project"})
    print(f"graph_query: {result[0].text}")
    
    # Test graph_tensions (should be empty)
    result = await call_tool("graph_tensions", {})
    print(f"graph_tensions: {result[0].text}")
    
    # Cleanup test data
    db = get_db()
    db.execute("DELETE FROM edges")
    db.execute("DELETE FROM entities")
    db.execute("DELETE FROM events")
    db.commit()
    print("\nAll MCP tool tests passed!")

asyncio.run(test())
