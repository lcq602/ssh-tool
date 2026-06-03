from ssh_tool.console_output import ConsoleOutput


def test_console_output_formats_steps_and_remote_output() -> None:
    lines: list[str] = []
    console = ConsoleOutput(write=lines.append, width=50)

    console.header("SSH Tool")
    console.connection("deploy", "example.com", 22, "linux")
    console.line("[line 2] $ ls -la")
    console.remote("total 12\napp.jar")
    console.success("All operations completed.")

    assert lines == [
        "+------------------------------------------------+",
        "| SSH Tool                                       |",
        "+------------------------------------------------+",
        "[INFO] Connecting to deploy@example.com:22 (linux)",
        "[STEP] [line 2] $ ls -la",
        "       total 12",
        "       app.jar",
        "[ OK ] All operations completed.",
    ]


def test_console_output_formats_error_with_log_path() -> None:
    lines: list[str] = []
    console = ConsoleOutput(write=lines.append, width=40)

    console.error("Authentication failed", "logs/run.log")

    assert lines == [
        "[FAIL] Authentication failed",
        "[LOG ] logs/run.log",
    ]
