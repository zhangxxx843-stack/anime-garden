#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
action="${1:-help}"
if (( $# > 0 )); then
    shift
fi

case "$action" in
    help|-h|--help)
        printf '%s\n' \
            '用法：./dev.sh <命令> [参数]' \
            '  build   编译当前作业' \
            '  run     编译并运行当前作业' \
            '  test    运行单元测试' \
            '  test-local  编译并逐包运行测试，适合当前受限会话' \
            '  check   检查版本、依赖、编译、测试和运行' \
            '  gui     构建并打开 Ubuntu Tk 图形界面' \
            '  gui-test 运行图形界面协议解析测试' \
            '  windows-test 运行 Windows PySide6 客户端测试（Ubuntu 上仅做离线检查）' \
            '  windows-build Windows 安装包由 GitHub Actions 构建' \
            '  clean   清理 CJPM 构建产物'
        exit 0
        ;;
    build|run|test|test-local|clean|gui|gui-test|windows-test|windows-build) ;;
    check)
        if (( $# > 0 )); then
            printf 'check 不接受额外参数。\n' >&2
            exit 2
        fi
        ;;
    *)
        printf '未知命令：%s。运行 ./dev.sh help 查看用法。\n' "$action" >&2
        exit 2
        ;;
esac

if [[ "$action" == windows-test ]]; then
    if [[ $# -gt 0 ]]; then
        printf 'windows-test 不接受额外参数。\n' >&2
        exit 2
    fi
    if [[ -n "${MINIPROJECT_WINDOWS_PYTHON:-}" ]]; then
        windows_python="$MINIPROJECT_WINDOWS_PYTHON"
    elif [[ -x "$project_dir/.venv-windows/bin/python" ]]; then
        windows_python="$project_dir/.venv-windows/bin/python"
    else
        windows_python="python3"
    fi
    env QT_QPA_PLATFORM=offscreen "$windows_python" -m unittest discover -s "$project_dir/windows_app" -p 'test_*.py' -v
    exit 0
fi

if [[ "$action" == windows-build ]]; then
    printf '%s\n' 'Windows 构建在 GitHub Actions 的 windows-latest runner 上执行。推送 main 后可在 Actions 下载 suishouji-windows-x64 artifact。'
    exit 0
fi

source "$project_dir/env.sh"
cd -- "$project_dir"

run_local_tests() (
    # 每次使用独立的构建目录，避免误运行已删除源码留下的旧测试程序。
    test_target="$(mktemp -d "${TMPDIR:-/tmp}/miniproject-unit.XXXXXX")"
    trap 'rm -rf -- "$test_target"' EXIT
    cjpm test --no-run --target-dir "$test_target"

    test_count=0
    for test_binary in "$test_target"/release/unittest_bin/*; do
        [[ -f "$test_binary" && -x "$test_binary" ]] || continue
        [[ "${test_binary##*/}" != std.testrunner ]] || continue
        test_count=$((test_count + 1))
        "$test_binary" --parallel=false --death-aware=false --no-color --no-progress "$@"
    done
    if (( test_count == 0 )); then
        printf '没有找到可执行的测试包，无法确认测试通过。\n' >&2
        exit 1
    fi
)

if [[ "$action" == check ]]; then
    cjc --version
    cjpm --version
    cjpm check
    cjpm build
    run_local_tests
    python_bin="${MINIPROJECT_PYTHON:-/home/zhangxxx/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"
    PYTHONPATH="$project_dir/gui" "$python_bin" -m unittest "$project_dir/gui/test_app.py" -v
    "$project_dir/target/release/bin/main" snapshot >/dev/null
elif [[ "$action" == test-local ]]; then
    run_local_tests "$@"
elif [[ "$action" == gui-test ]]; then
    python_bin="${MINIPROJECT_PYTHON:-/home/zhangxxx/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"
    PYTHONPATH="$project_dir/gui" exec "$python_bin" -m unittest "$project_dir/gui/test_app.py" -v "$@"
elif [[ "$action" == gui ]]; then
    cjpm build
    python_bin="${MINIPROJECT_PYTHON:-/home/zhangxxx/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3}"
    PYTHONPATH="$project_dir/gui" exec "$python_bin" "$project_dir/gui/app.py" "$@"
else
    exec cjpm "$action" "$@"
fi
