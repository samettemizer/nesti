# StyleClass

StyleClass manages CSS classes declaratively to during enter/leave animations or just to toggle classes on an element.

## Basic

StyleClass applies enter and leave animations to a target element declaratively. The target is resolved with the selector option, here @next referring to the next sibling.

```vue
<template>
    <div class="flex flex-col items-center gap-4 h-32">
        <button
            type="button"
            v-styleclass="{
                selector: '@next',
                enterFromClass: 'hidden',
                enterActiveClass: 'animate-scalein',
                leaveToClass: 'hidden',
                leaveActiveClass: 'animate-fadeout',
                hideOnOutsideClick: true
            }"
            class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-contrast hover:bg-primary/90 transition-colors cursor-pointer text-sm font-medium"
        >
            Toggle Panel
            <ChevronDown class="w-3.5 h-3.5" />
        </button>
        <div class="hidden relative w-full max-w-md p-4 rounded-lg border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900 shadow-md origin-top">
            <p class="text-sm text-surface-700 dark:text-surface-200 leading-relaxed m-0">This panel is toggled using StyleClass with scale-in and fade-out animations. Click the button again or click outside to dismiss.</p>
        </div>
    </div>
</template>

<script setup>
import ChevronDown from '@primeicons/vue/chevron-down';
<\/script>
```

## Animation

Classes to apply during enter and leave animations are specified using the enterFromClass , enterActiveClass , enterToClass , leaveFromClass , leaveActiveClass , leaveToClass properties. In addition in case the target is an overlay, hideOnOutsideClick would be handy to hide the target if outside of the popup is clicked, or enable hideOnEscape to close the popup by listening escape key.

```vue
<template>
    <div class="flex items-center justify-center gap-7">
        <div class="flex flex-col items-center">
            <div>
                <Button v-styleclass="{ selector: '.box1', enterFromClass: 'my-hidden', enterActiveClass: 'my-fadein' }" class="mr-2">FadeIn</Button>
                <Button v-styleclass="{ selector: '.box1', leaveActiveClass: 'my-fadeout', leaveToClass: 'my-hidden' }" severity="secondary">FadeOut</Button>
            </div>
            <div class="h-32">
                <div class="my-hidden animate-duration-500 box1">
                    <div class="flex bg-primary text-primary-contrast items-center justify-center py-3 rounded-md mt-4 font-bold text-sm w-28 h-28">Custom</div>
                </div>
            </div>
        </div>
        <div class="flex flex-col items-center">
            <div>
                <Button v-styleclass="{ selector: '.box2', enterFromClass: 'hidden', enterActiveClass: 'animate-slidedown' }" class="mr-2">SlideDown</Button>
                <Button v-styleclass="{ selector: '.box2', leaveActiveClass: 'animate-slideup', leaveToClass: 'hidden' }" severity="secondary">SlideUp</Button>
            </div>
            <div class="h-32">
                <div class="hidden animate-duration-500 box2 overflow-hidden">
                    <div class="flex bg-primary text-primary-contrast items-center justify-center py-3 rounded-md mt-4 font-bold text-sm w-28 h-28">Content</div>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
@keyframes my-fadein {
    0% {
        opacity: 0;
    }
    100% {
        opacity: 1;
    }
}

@keyframes my-fadeout {
    0% {
        opacity: 1;
    }
    100% {
        opacity: 0;
    }
}

.my-hidden {
    display: none;
}

.my-fadein {
    animation: my-fadein 150ms linear;
}

.my-fadeout {
    animation: my-fadeout 150ms linear;
}
<\/style>
```

## Toggle Class

StyleClass has two modes, toggleClass to simply add-remove a class and enter/leave animations. The target element to change the styling is defined with the selector property that accepts any valid CSS selector or keywords including &#64;next , prev , parent , grandparent .

```vue
<template>
    <div class="flex flex-col items-center gap-4 h-40">
        <button
            type="button"
            v-styleclass="{ selector: '@next', toggleClass: 'hidden' }"
            class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-contrast hover:bg-primary/90 transition-colors cursor-pointer text-sm font-medium"
        >
            Toggle
        </button>
        <div class="w-full max-w-md p-4 rounded-lg border border-surface-200 dark:border-surface-700 bg-surface-0 dark:bg-surface-900 shadow-md">
            <p class="text-sm text-surface-700 dark:text-surface-200 leading-relaxed m-0">
                This panel is toggled instantly using <code class="text-xs bg-surface-100 dark:bg-surface-800 px-1.5 py-0.5 rounded">toggleClass</code> without any enter/leave animations.
            </p>
        </div>
    </div>
</template>

<script setup>
<\/script>
```

## Selector

The target element is resolved with the selector option, which accepts keywords such as &#64;next , &#64;prev , &#64;parent and &#64;grandparent , or any valid CSS selector.

```vue
<template>
    <div class="flex flex-col gap-8">
        <div class="flex flex-col gap-2">
            <span class="text-sm font-medium text-surface-500 dark:text-surface-400">@next</span>
            <div class="flex items-center gap-4">
                <button
                    type="button"
                    v-styleclass="{ selector: '@next', enterFromClass: 'hidden', enterActiveClass: 'animate-fadein', leaveActiveClass: 'animate-fadeout', leaveToClass: 'hidden' }"
                    class="px-4 py-2 rounded-lg bg-primary text-primary-contrast hover:bg-primary/90 transition-colors cursor-pointer text-sm font-medium shrink-0"
                >
                    @next
                </button>
                <div class="hidden px-4 py-2 rounded-lg bg-primary/10 text-primary text-sm font-medium">Next Sibling</div>
            </div>
        </div>
        <div class="flex flex-col gap-2">
            <span class="text-sm font-medium text-surface-500 dark:text-surface-400">@prev</span>
            <div class="flex items-center gap-4">
                <div class="hidden px-4 py-2 rounded-lg bg-primary/10 text-primary text-sm font-medium">Previous Sibling</div>
                <button
                    type="button"
                    v-styleclass="{ selector: '@prev', enterFromClass: 'hidden', enterActiveClass: 'animate-fadein', leaveActiveClass: 'animate-fadeout', leaveToClass: 'hidden' }"
                    class="px-4 py-2 rounded-lg bg-primary text-primary-contrast hover:bg-primary/90 transition-colors cursor-pointer text-sm font-medium shrink-0"
                >
                    @prev
                </button>
            </div>
        </div>
        <div class="flex flex-col gap-2">
            <span class="text-sm font-medium text-surface-500 dark:text-surface-400">CSS Selector</span>
            <div class="flex items-center gap-4">
                <button
                    type="button"
                    v-styleclass="{ selector: '#remote-target', enterFromClass: 'hidden', enterActiveClass: 'animate-scalein', leaveActiveClass: 'animate-fadeout', leaveToClass: 'hidden' }"
                    class="px-4 py-2 rounded-lg bg-primary text-primary-contrast hover:bg-primary/90 transition-colors cursor-pointer text-sm font-medium shrink-0"
                >
                    #remote-target
                </button>
            </div>
            <div id="remote-target" class="hidden px-4 py-2 rounded-lg bg-primary/10 text-primary text-sm font-medium origin-top w-fit">Remote Target</div>
        </div>
    </div>
</template>

<script setup>
<\/script>
```

## Hide On Resize

When hideOnResize is enabled, the leave animation is triggered automatically when resizing occurs. Use the resizeSelector property to specify whether to listen to window resize events or element-specific resize events. Set resizeSelector to "window" (default) or "document" for browser resize, or a CSS selector to observe the target element's dimensions.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-4">
        <div class="flex flex-col items-center gap-4 w-100">
            <Button v-styleclass="{ selector: '.window-responsive-box', enterFromClass: 'hidden', enterActiveClass: 'animate-fadein', leaveActiveClass: 'animate-fadeout', leaveToClass: 'hidden', hideOnResize: true, resizeSelector: 'window' }">Show Window Responsive Content</Button>
            <div class="window-responsive-box hidden animate-duration-300 border border-lg border-surface">
                <div class="p-3 flex flex-col gap-2">
                    <h3 class="text-lg font-bold">Window Responsive Panel</h3>
                    <p class="text-sm">This panel will hide when you resize the browser window.</p>
                    <p class="text-sm">Try resizing your browser window to see the effect.</p>
                </div>
            </div>
        </div>

        <div class="flex flex-col items-center gap-4 w-100">
            <Button v-styleclass="{ selector: '.resizable-container', enterFromClass: 'hidden', enterActiveClass: 'animate-fadein', leaveActiveClass: 'animate-fadeout', leaveToClass: 'hidden', hideOnResize: true, resizeSelector: '.resizable-container' }">Show Resizable Panel</Button>

            <div class="resizable-container hidden animate-duration-300 border border-lg border-surface w-xs w-max-[25rem] w-min-[15rem] overflow-auto resize">
                <div class="p-4 h-full flex flex-col gap-2">
                    <h3 class="text-lg font-bold">Resizable Panel</h3>
                    <p class="text-sm">Drag the resize handle in the bottom-right corner to resize this panel.</p>
                    <p class="text-sm">The panel will hide when you resize it.</p>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
<\/script>
```

## Style Class API

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| hooks | DirectiveHooks<any, any> | Used to manage all lifecycle hooks. |

### Theming
