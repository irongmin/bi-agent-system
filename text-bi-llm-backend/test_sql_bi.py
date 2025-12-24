print("[ask_endpoint] hit:", req.question)
try:
    action, sql, rows, insight_obj, sub_analyses = await route_and_run(db, req.question)
except Exception:
    import traceback
    print(traceback.format_exc())
    raise
