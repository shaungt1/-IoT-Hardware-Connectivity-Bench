#include <stdint.h>

extern uint32_t _stack_top;

static void reset_handler(void);

__attribute__((section(".vectors")))
const uintptr_t vectors[] = {
    (uintptr_t)&_stack_top,
    (uintptr_t)reset_handler,
};

static void reset_handler(void) {
    volatile uint32_t *const proof = (uint32_t *)0x20000000u;
    *proof = 0xC0DEC0DEu;
    for (;;) {
        __asm volatile("wfi");
    }
}
