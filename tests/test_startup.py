from smart_bid_watcher.startup import executable_command


def test_windows_startup_command_does_not_force_minimized_mode():
    assert "--minimized" not in executable_command()
