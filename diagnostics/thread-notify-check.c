#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
int main(void) {
    ULONG_PTR info[3] = {0x1000, (ULONG_PTR)"XinXuan diagnostic control", (ULONG_PTR)GetCurrentThreadId()};
    if (!IsDebuggerPresent()) { puts("RUN_WITH_TRACER"); return 2; }
    RaiseException(0x406d1388u, 0, 3, info);
    puts("THREAD_NOTIFY_SURVIVED");
    return 0;
}
