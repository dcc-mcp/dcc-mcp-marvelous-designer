from dcc_mcp_core.skill import run_main

from dcc_mcp_marvelous_designer.server import current_api


def main(**params):
    return {"success": True, "context": current_api().create_rectangle(**params)}


if "__mcp_params__" in globals():
    __mcp_result__ = main(**globals()["__mcp_params__"])
if __name__ == "__main__":
    run_main(main)
