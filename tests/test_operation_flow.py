from ssh_tool.operation_flow import FlowEdge, FlowNode, OperationFlow


def test_flow_exports_operations_in_arrow_order() -> None:
    flow = OperationFlow(
        nodes=[
            FlowNode(id="start", kind="start", label="Start", x=80, y=80),
            FlowNode(id="cd", kind="command", label="cd", x=220, y=80, text="cd /home/project/app"),
            FlowNode(id="list", kind="command", label="ls", x=360, y=80, text="ls -la"),
            FlowNode(
                id="upload",
                kind="upload",
                label="upload",
                x=500,
                y=80,
                local_path="D:\\build\\app.jar",
                remote_path="/home/project/app/app.jar",
            ),
        ],
        edges=[
            FlowEdge("start", "cd"),
            FlowEdge("cd", "list"),
            FlowEdge("list", "upload"),
        ],
    )

    assert flow.to_operations_text() == (
        "cd /home/project/app\n"
        "ls -la\n"
        "upload D:\\build\\app.jar /home/project/app/app.jar\n"
    )


def test_flow_quotes_upload_paths_with_spaces() -> None:
    flow = OperationFlow(
        nodes=[
            FlowNode(id="start", kind="start", label="Start", x=0, y=0),
            FlowNode(
                id="upload",
                kind="upload",
                label="upload",
                x=0,
                y=0,
                local_path="D:\\build output\\app.jar",
                remote_path="/tmp/app final.jar",
            ),
        ],
        edges=[FlowEdge("start", "upload")],
    )

    assert flow.to_operations_text() == 'upload "D:\\build output\\app.jar" "/tmp/app final.jar"\n'


def test_flow_rejects_branching_because_operations_are_sequential() -> None:
    flow = OperationFlow(
        nodes=[
            FlowNode(id="start", kind="start", label="Start", x=0, y=0),
            FlowNode(id="a", kind="command", label="A", x=0, y=0, text="echo a"),
            FlowNode(id="b", kind="command", label="B", x=0, y=0, text="echo b"),
        ],
        edges=[FlowEdge("start", "a"), FlowEdge("start", "b")],
    )

    try:
        flow.to_operations_text()
    except ValueError as exc:
        assert "only one outgoing arrow" in str(exc)
    else:
        raise AssertionError("Expected branching flow to be rejected")
