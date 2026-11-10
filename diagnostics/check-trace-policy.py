"""Compile the actual debugger event branch with recorded Windows event data."""
from pathlib import Path
import subprocess, tempfile
source = Path(__file__).with_name('trace-startup.c').read_text()
branch = source.split('case EXCEPTION_DEBUG_EVENT:',1)[1].split('case EXIT_PROCESS_DEBUG_EVENT:',1)[0].strip()
if branch.endswith('break;'): branch = branch[:-6]
preamble = r'''
#include <stdint.h>
#include <stdio.h>
#define EXCEPTION_BREAKPOINT 0x80000003u
#define EXCEPTION_ACCESS_VIOLATION 0xc0000005u
#define EXCEPTION_IN_PAGE_ERROR 0xc0000006u
#define DBG_CONTINUE 0x10002u
#define DBG_EXCEPTION_NOT_HANDLED 0x80010001u
struct Info { struct { uint32_t ExceptionCode, NumberParameters; uintptr_t ExceptionInformation[15]; } ExceptionRecord; uint32_t dwFirstChance; };
static void capture_fault(int p,int t,struct Info *i) {(void)p;(void)t;(void)i;}
static uint32_t policy(uint32_t code, uint32_t count, uintptr_t type, uintptr_t packed) {
struct {struct {struct Info Exception;} u; int dwThreadId;} event = {0};
struct {int hProcess;} child = {0};
event.u.Exception.ExceptionRecord.ExceptionCode=code;
event.u.Exception.ExceptionRecord.NumberParameters=count;
event.u.Exception.ExceptionRecord.ExceptionInformation[0]=type;
event.u.Exception.ExceptionRecord.ExceptionInformation[2]=packed;
event.u.Exception.dwFirstChance=1;
uint32_t continuation=DBG_CONTINUE;
'''
checks = r'''
return continuation; }
int main(void) {
if(policy(0x406d1388u,3,0x1000,0)!=DBG_CONTINUE) {puts("FAIL: recorded thread naming notification was rejected"); return 1;}
if(policy(EXCEPTION_ACCESS_VIOLATION,2,0,0)!=DBG_EXCEPTION_NOT_HANDLED) return 2;
if(policy(0x406d1388u,2,0x1000,0)!=DBG_EXCEPTION_NOT_HANDLED) return 3;
if(policy(0x406d1388u,3,0x999,0)!=DBG_EXCEPTION_NOT_HANDLED) return 4;
if(policy(0x406d1388u,3,0x1000,1ull<<32)!=DBG_EXCEPTION_NOT_HANDLED) return 5;
if(policy(EXCEPTION_BREAKPOINT,0,0,0)!=DBG_CONTINUE) return 6;
puts("PASS: thread notification accepted; access violations and malformed notifications preserved");
}
'''
with tempfile.TemporaryDirectory() as directory:
    c = Path(directory)/'policy.c'; binary=Path(directory)/'policy'
    c.write_text(preamble+branch+checks)
    subprocess.run(['gcc','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
