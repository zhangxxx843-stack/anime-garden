#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>

/* A debugger for our own child process only. It does not attach to other apps,
 * install handlers in the system, or change registry/debugger settings. */
typedef struct { uintptr_t base; DWORD size; char path[MAX_PATH * 2]; } Module;
static Module modules[256];
static unsigned module_count;

static void remember_module(HANDLE process, HANDLE file, void *base, const char *fallback) {
    if (module_count >= 256) return;
    Module *m = &modules[module_count++];
    memset(m, 0, sizeof(*m));
    m->base = (uintptr_t)base;
    if (!file || !GetFinalPathNameByHandleA(file, m->path, sizeof(m->path), 0))
        snprintf(m->path, sizeof(m->path), "%s", fallback);
    IMAGE_DOS_HEADER dos;
    IMAGE_NT_HEADERS64 nt;
    SIZE_T read = 0;
    if (ReadProcessMemory(process, base, &dos, sizeof(dos), &read) && dos.e_magic == IMAGE_DOS_SIGNATURE &&
        ReadProcessMemory(process, (char *)base + dos.e_lfanew, &nt, sizeof(nt), &read) &&
        nt.Signature == IMAGE_NT_SIGNATURE)
        m->size = nt.OptionalHeader.SizeOfImage;
    printf("MODULE base=0x%llx size=0x%lx %s\n", (unsigned long long)m->base,
           (unsigned long)m->size, m->path);
    fflush(stdout);
}

static void print_address(const char *label, uintptr_t address) {
    for (unsigned i = 0; i < module_count; ++i) {
        Module *m = &modules[i];
        if (address >= m->base && address - m->base < m->size) {
            printf("%s 0x%llx %s +0x%llx\n", label, (unsigned long long)address, m->path,
                   (unsigned long long)(address - m->base));
            return;
        }
    }
    printf("%s 0x%llx\n", label, (unsigned long long)address);
}

static void capture_fault(HANDLE process, DWORD thread_id, EXCEPTION_DEBUG_INFO *info) {
    printf("EXCEPTION code=0x%08lx firstChance=%lu\n", (unsigned long)info->ExceptionRecord.ExceptionCode,
           (unsigned long)info->dwFirstChance);
    print_address("INSTRUCTION", (uintptr_t)info->ExceptionRecord.ExceptionAddress);
    if ((info->ExceptionRecord.ExceptionCode == EXCEPTION_ACCESS_VIOLATION ||
         info->ExceptionRecord.ExceptionCode == EXCEPTION_IN_PAGE_ERROR) &&
        info->ExceptionRecord.NumberParameters >= 2)
        printf("ACCESS mode=%llu address=0x%llx\n",
               (unsigned long long)info->ExceptionRecord.ExceptionInformation[0],
               (unsigned long long)info->ExceptionRecord.ExceptionInformation[1]);
    HANDLE thread = OpenThread(THREAD_GET_CONTEXT | THREAD_QUERY_INFORMATION, FALSE, thread_id);
    CONTEXT context;
    memset(&context, 0, sizeof(context));
    context.ContextFlags = CONTEXT_FULL;
    if (thread && GetThreadContext(thread, &context)) {
        printf("REGISTERS RIP=%llx RSP=%llx RCX=%llx RDX=%llx R8=%llx R9=%llx\n",
               (unsigned long long)context.Rip, (unsigned long long)context.Rsp,
               (unsigned long long)context.Rcx, (unsigned long long)context.Rdx,
               (unsigned long long)context.R8, (unsigned long long)context.R9);
        unsigned char instruction[32];
        SIZE_T count = 0;
        if (ReadProcessMemory(process, (void *)(uintptr_t)context.Rip, instruction, sizeof(instruction), &count)) {
            printf("INSTRUCTION_BYTES");
            for (SIZE_T i = 0; i < count; ++i) printf(" %02x", instruction[i]);
            printf("\n");
        }
        /* Raw stack candidates, not an unwound call stack. Offline symbol lookup must
         * distinguish real return addresses from pointers that happen to be on stack. */
        uintptr_t stack[48];
        count = 0;
        if (ReadProcessMemory(process, (void *)(uintptr_t)context.Rsp, stack, sizeof(stack), &count))
            for (SIZE_T i = 0; i < count / sizeof(uintptr_t); ++i) {
                char label[32];
                snprintf(label, sizeof(label), "STACK_CANDIDATE[%llu]", (unsigned long long)i);
                print_address(label, stack[i]);
            }
    }
    if (thread) CloseHandle(thread);
    fflush(stdout);
}

int main(int argc, char **argv) {
    puts("NATIVE_TRACER_ENTERED");
    fflush(stdout);
    if (argc != 2) { puts("Usage: TraceStartup.exe program.exe"); return 2; }
    char command[MAX_PATH * 2];
    snprintf(command, sizeof(command), "\"%s\"", argv[1]);
    STARTUPINFOA startup;
    PROCESS_INFORMATION child;
    memset(&startup, 0, sizeof(startup)); startup.cb = sizeof(startup);
    memset(&child, 0, sizeof(child));
    if (!CreateProcessA(NULL, command, NULL, NULL, TRUE, DEBUG_ONLY_THIS_PROCESS, NULL, NULL, &startup, &child)) {
        printf("CREATE_PROCESS_FAILED error=%lu\n", (unsigned long)GetLastError()); return 3;
    }
    DWORD exit_code = 0;
    for (;;) {
        DEBUG_EVENT event;
        if (!WaitForDebugEvent(&event, 30000)) {
            printf("DEBUG_WAIT_FAILED error=%lu\n", (unsigned long)GetLastError());
            TerminateProcess(child.hProcess, 124); exit_code = 124; break;
        }
        DWORD continuation = DBG_CONTINUE;
        switch (event.dwDebugEventCode) {
        case CREATE_PROCESS_DEBUG_EVENT:
            remember_module(child.hProcess, event.u.CreateProcessInfo.hFile,
                            event.u.CreateProcessInfo.lpBaseOfImage, argv[1]);
            if (event.u.CreateProcessInfo.hFile) CloseHandle(event.u.CreateProcessInfo.hFile);
            break;
        case LOAD_DLL_DEBUG_EVENT:
            remember_module(child.hProcess, event.u.LoadDll.hFile, event.u.LoadDll.lpBaseOfDll, "unknown DLL");
            if (event.u.LoadDll.hFile) CloseHandle(event.u.LoadDll.hFile);
            break;
        case EXCEPTION_DEBUG_EVENT:
            /* MSVC thread names are debugger notifications, not application faults.
             * x64 THREADNAME_INFO is three ULONG_PTRs; flags occupy the high
             * half of the final parameter. Never swallow genuine access violations. */
            if (event.u.Exception.ExceptionRecord.ExceptionCode == 0x406d1388u &&
                event.u.Exception.ExceptionRecord.NumberParameters == 3 &&
                event.u.Exception.ExceptionRecord.ExceptionInformation[0] == 0x1000 &&
                (event.u.Exception.ExceptionRecord.ExceptionInformation[2] >> 32) == 0) {
                puts("THREAD_NAME_NOTIFICATION_HANDLED");
                fflush(stdout);
                continuation = DBG_CONTINUE;
            } else if (event.u.Exception.ExceptionRecord.ExceptionCode != EXCEPTION_BREAKPOINT) {
                if (event.u.Exception.ExceptionRecord.ExceptionCode == EXCEPTION_ACCESS_VIOLATION ||
                    !event.u.Exception.dwFirstChance)
                    capture_fault(child.hProcess, event.dwThreadId, &event.u.Exception);
                continuation = DBG_EXCEPTION_NOT_HANDLED;
            }
            break;
        case EXIT_PROCESS_DEBUG_EVENT:
            exit_code = event.u.ExitProcess.dwExitCode;
            printf("CHILD_EXIT signed=%ld hex=0x%08lx\n", (long)(int32_t)exit_code, (unsigned long)exit_code);
            fflush(stdout);
            ContinueDebugEvent(event.dwProcessId, event.dwThreadId, DBG_CONTINUE);
            goto done;
        default: break;
        }
        ContinueDebugEvent(event.dwProcessId, event.dwThreadId, continuation);
    }
done:
    CloseHandle(child.hThread); CloseHandle(child.hProcess);
    return exit_code == 0 ? 0 : 1;
}
