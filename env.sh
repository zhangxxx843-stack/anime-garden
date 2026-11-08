#!/usr/bin/env bash
# 在 Bash 中运行：source ./env.sh

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    printf '请使用 source ./env.sh，或通过 ./dev.sh 执行开发命令。\n' >&2
    exit 2
fi

_miniproject_activate() {
    local sdk_root="${CANGJIE_HOME:-/home/zhangxxx/Documents/Codex/2026-10-23/referenced-chatgpt-conversation-this-is-an/outputs/cangjie-study/sdk/cangjie}"
    local compiler_version

    if [[ ! -f "$sdk_root/envsetup.sh" || ! -x "$sdk_root/bin/cjc" || ! -x "$sdk_root/tools/bin/cjpm" ]]; then
        printf '找不到完整的仓颉 SDK：%s\n请将 CANGJIE_HOME 设置为 Cangjie 1.0.5 的安装目录。\n' "$sdk_root" >&2
        return 1
    fi

    # SDK 自带脚本使用此变量；先初始化，兼容调用者开启 set -u 的情况。
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"
    source "$sdk_root/envsetup.sh" || return 1
    export LD_LIBRARY_PATH="${LD_LIBRARY_PATH%:}"

    compiler_version="$(cjc --version)" || return 1
    if [[ "$compiler_version" != *"Cangjie Compiler: 1.0.5 ("* ]]; then
        printf '本作业使用 Cangjie 1.0.5，实际工具链为：\n%s\n' "$compiler_version" >&2
        return 1
    fi
}

if _miniproject_activate; then
    unset -f _miniproject_activate
else
    unset -f _miniproject_activate
    return 1
fi
