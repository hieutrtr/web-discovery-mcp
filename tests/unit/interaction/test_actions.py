from legacy_web_mcp.interaction import discover_interactions, perform_interactions


def test_discover_interactions_skips_destructive():
    html = """
    <html>
      <body>
        <button id='save'>Save</button>
        <button id='delete-account'>Delete</button>
        <form id='profile'>
          <input type='text' name='name'/>
        </form>
      </body>
    </html>
    """
    actions = discover_interactions(html)
    selectors = {action.selector for action in actions}
    assert "button#save" in selectors
    assert "button#delete-account" not in selectors
    assert any(action.action_type == "fill" for action in actions)


def test_perform_interactions_logs_actions():
    actions = discover_interactions("<button id='go'>Go</button>")
    logs = perform_interactions(actions)
    assert logs
    assert logs[0].status == "simulated"
