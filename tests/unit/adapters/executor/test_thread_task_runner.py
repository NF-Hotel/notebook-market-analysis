import threading

from app.adapters.executor.thread_task_runner import ThreadTaskRunner

WAIT_SECONDS = 10


def test_a_task_runs_on_another_thread() -> None:
    runner = ThreadTaskRunner()
    seen: list[str] = []
    done = threading.Event()

    def task() -> None:
        seen.append(threading.current_thread().name)
        done.set()

    runner.submit(task)
    assert done.wait(WAIT_SECONDS)
    runner.close()
    assert seen
    assert seen[0] != threading.current_thread().name


def test_tasks_run_one_after_the_other_in_order() -> None:
    runner = ThreadTaskRunner()
    order: list[int] = []
    release = threading.Event()
    runner.submit(lambda: (release.wait(WAIT_SECONDS), order.append(1)))
    runner.submit(lambda: order.append(2))
    assert order == []
    release.set()
    runner.close()
    assert order == [1, 2]
