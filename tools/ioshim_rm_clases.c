#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <sys/ioctl.h>
/* registra en stderr: clase RM de cada NV_ESC_RM_ALLOC / ALLOC_MEMORY y el numero de cada ioctl a /dev/nvidia-uvm */
int ioctl(int fd, unsigned long req, ...) {
    va_list a; va_start(a, req); void *p = va_arg(a, void *); va_end(a);
    static int (*real)(int, unsigned long, ...);
    if (!real) real = dlsym(RTLD_NEXT, "ioctl");
    char path[64], dst[128]; snprintf(path, sizeof path, "/proc/self/fd/%d", fd);
    ssize_t n = readlink(path, dst, sizeof dst - 1); if (n < 0) n = 0; dst[n] = 0;
    int nr = req & 0xff, ty = (req >> 8) & 0xff;
    if (!strcmp(dst, "/dev/nvidiactl") && ty == 0x46 && (nr == 0x2b || nr == 0x27)) {
        uint32_t *w = p;
        fprintf(stderr, "IOC rm nr=0x%x class=0x%x\n", nr, w[3]);
    } else if (!strcmp(dst, "/dev/nvidia-uvm")) {
        fprintf(stderr, "IOC uvm req=0x%lx\n", req);
    }
    return real(fd, req, p);
}
