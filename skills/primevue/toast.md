# Toast

Toast is used to display messages in an overlay.

## ToastService

Toast component is controlled via the ToastService that needs to be installed as an application plugin.

## Basic

Toasts are displayed by calling the add method provided by the useToast function. A single toast is specified by the Message interface that defines various properties such as severity , summary and detail .

```vue
<template>
    <div class="flex justify-center">
        <Toast />
        <Button variant="outlined" @click="show()">Create toast</Button>
    </div>
</template>

<script setup>
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const show = () => {
    toast.add({ summary: 'Successfully completed', detail: 'The task was completed successfully. You can now view the details.', life: 3000 });
};
<\/script>
```

## Severity

The severity option specifies the type of the message. There are four types of messages: success , info , warn and error . The severity of the message is used to display the icon and the color of the toast.

```vue
<template>
    <div class="flex flex-wrap justify-center gap-2">
        <Toast />
        <Button severity="info" variant="outlined" @click="showInfo">Info</Button>
        <Button severity="success" variant="outlined" @click="showSuccess">Success</Button>
        <Button severity="warn" variant="outlined" @click="showWarn">Warn</Button>
        <Button severity="danger" variant="outlined" @click="showError">Error</Button>
        <Button severity="secondary" variant="outlined" @click="showSecondary">Secondary</Button>
        <Button severity="contrast" variant="outlined" @click="showContrast">Contrast</Button>
    </div>
</template>

<script setup>
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const showInfo = () => {
    toast.add({ severity: 'info', summary: 'Heads up', detail: 'There’s something you might want to check.', life: 3000 });
};

const showSuccess = () => {
    toast.add({ severity: 'success', summary: 'Saved successfully', detail: 'Your changes have been saved.', life: 3000 });
};

const showWarn = () => {
    toast.add({ severity: 'warn', summary: 'Check this', detail: 'Some fields may need your attention.', life: 3000 });
};

const showError = () => {
    toast.add({ severity: 'error', summary: 'Something went wrong', detail: 'We couldn’t complete the action. Please try again.', life: 3000 });
};

const showSecondary = () => {
    toast.add({ severity: 'secondary', summary: 'For your information', detail: 'This is a secondary toast message.', life: 3000 });
};

const showContrast = () => {
    toast.add({ severity: 'contrast', summary: 'High contrast', detail: 'This is a contrast toast message.', life: 3000 });
};
<\/script>
```

## Promise

A sticky loading toast can be shown while an async task runs, then removed and replaced with a success or error toast based on the result.

```vue
<template>
    <div class="flex flex-wrap items-center justify-center gap-4">
        <Toast group="promise" />
        <Button variant="outlined" @click="runPromise">Run promise</Button>
    </div>
</template>

<script setup>
import Spinner from '@primeicons/vue/spinner';
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const fakeApiCall = () =>
    new Promise((resolve, reject) => {
        setTimeout(() => {
            Math.random() < 0.5 ? resolve('Success!') : reject(new Error('Something went wrong'));
        }, 2000);
    });

const runPromise = () => {
    const loading = {
        severity: 'secondary',
        summary: 'Please wait...',
        detail: 'Your request is being processed. This may take a moment.',
        icon: markRaw({
            render: () => h(Spinner, { spin: true })
        }),
        group: 'promise',
        sticky: true
    };

    toast.add(loading);

    fakeApiCall()
        .then((result) => {
            toast.remove(loading);
            toast.add({ severity: 'success', summary: 'Success!', detail: \`\${result}. Everything went smoothly. Thank you for your patience.\`, group: 'promise', life: 3000 });
        })
        .catch((error) => {
            toast.remove(loading);
            toast.add({ severity: 'error', summary: 'Oops, something went wrong', detail: \`Error: \${error.message}. Please try again or contact support if the problem persists.\`, group: 'promise', life: 3000 });
        });
};
<\/script>
```

## Sticky

A toast disappears after the time defined by the life option, set sticky option true on the message to override this and not hide the toast automatically.

```vue
<template>
    <div class="flex justify-center">
        <Toast />
        <div class="flex flex-wrap gap-2">
            <Button variant="outlined" @click="show()">Create toast</Button>
            <Button variant="outlined" severity="secondary" @click="clear()">Dismiss toast</Button>
        </div>
    </div>
</template>

<script setup>
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const show = () => {
    toast.add({ severity: 'info', summary: 'Sticky toast', detail: 'This toast stays until you dismiss it manually.', sticky: true });
};

const clear = () => {
    toast.removeAllGroups();
};
<\/script>
```

## Custom

The toast content can be fully customized with a template to render any markup, such as links and action buttons.

```vue
<template>
    <div class="flex justify-center">
        <Toast group="custom" :pt="{ closeButton: { class: 'hidden!' } }">
            <template #message>
                <div class="space-y-2 w-full">
                    <div>
                        <h1 class="text-sm! m-0! font-medium! text-surface-900 dark:text-surface-0 leading-6">
                            Purchase complete!
                            <a class="cursor-pointer underline! hover:opacity-75">View receipt</a>
                        </h1>
                        <p class="text-surface-500 mt-1 text-sm">
                            Your order is being processed. Track all orders or
                            <a class="cursor-pointer underline! hover:opacity-75">learn about returns</a>
                        </p>
                    </div>
                    <div class="flex items-center mt-3 gap-2">
                        <button
                            type="button"
                            @click="dismiss()"
                            class="font-medium px-2 py-1.5 text-xs rounded-md border border-surface-200 dark:border-surface-700 hover:bg-surface-50 active:bg-surface-100 dark:hover:bg-surface-800 dark:active:bg-surface-700 text-surface-500 dark:text-surface-400"
                        >
                            Dismiss
                        </button>
                        <button
                            type="button"
                            @click="dismiss()"
                            class="font-medium px-2 py-1.5 text-xs rounded-md border border-indigo-500/25 bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-950/75 dark:hover:bg-indigo-950 text-indigo-500 dark:text-indigo-400"
                        >
                            Track all orders
                        </button>
                    </div>
                </div>
            </template>
        </Toast>
        <Button variant="outlined" @click="show()">Custom toast</Button>
    </div>
</template>

<script setup>
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const show = () => {
    toast.add({ group: 'custom', life: 6000, summary: 'Purchase complete', styleClass: 'bg-surface-0! dark:bg-surface-900! border-surface!' });
};

const dismiss = () => {
    toast.removeGroup('custom');
};
<\/script>
```

## Position

Location of the toast is customized with the position property. Valid values are top-left , top-center , top-right , bottom-left , bottom-center , bottom-right and center .

```vue
<template>
    <div class="flex justify-center">
        <Toast position="top-left" group="top-left" />
        <Toast position="top-center" group="top-center" />
        <Toast position="top-right" group="top-right" />
        <Toast position="bottom-left" group="bottom-left" />
        <Toast position="bottom-center" group="bottom-center" />
        <Toast position="bottom-right" group="bottom-right" />
        <Toast position="center" group="center" />
        <div class="flex flex-wrap gap-2">
            <Button variant="outlined" @click="createToast('top-left')">Top Left</Button>
            <Button variant="outlined" @click="createToast('top-center')">Top Center</Button>
            <Button variant="outlined" @click="createToast('top-right')">Top Right</Button>
            <Button variant="outlined" @click="createToast('bottom-left')">Bottom Left</Button>
            <Button variant="outlined" @click="createToast('bottom-center')">Bottom Center</Button>
            <Button variant="outlined" @click="createToast('bottom-right')">Bottom Right</Button>
            <Button variant="outlined" @click="createToast('center')">Center</Button>
        </div>
    </div>
</template>

<script setup>
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const createToast = (group) => {
    toast.add({ summary: 'Successfully completed', detail: 'The task was completed successfully. You can now view the details.', group, life: 3000 });
};
<\/script>
```

## Expanded Mode

Setting mode to expanded always renders the stack expanded; the stacked mode stacks toasts collapsed and expands them on hover. Auto-dismiss timers still pause while the toasts are hovered.

```vue
<template>
    <div class="flex justify-center">
        <Toast group="expanded" mode="expanded" :limit="7" />
        <Button variant="outlined" @click="show()">Create toast</Button>
    </div>
</template>

<script setup>
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const show = () => {
    toast.add({ group: 'expanded', summary: 'Successfully completed', detail: 'The task was completed successfully. You can now view the details.', life: 3000 });
};
<\/script>
```

## Action

An interactive button can be added to the toast content with a custom template, for example to let the user confirm an action.

```vue
<template>
    <div class="flex justify-center">
        <Toast group="action">
            <template #message="slotProps">
                <Check v-if="slotProps.message.severity === 'success'" />
                <div class="p-toast-message-text">
                    <div class="p-toast-summary">{{ slotProps.message.summary }}</div>
                    <div class="p-toast-detail">{{ slotProps.message.detail }}</div>
                    <Button v-if="slotProps.message.severity !== 'success'" size="small" class="mt-3 self-start" @click="enableCamera()">Enable camera</Button>
                </div>
            </template>
        </Toast>
        <Button variant="outlined" @click="show()">Create toast with action</Button>
    </div>
</template>

<script setup>
import { useToast } from 'primevue/usetoast';
import Check from '@primeicons/vue/check';

const toast = useToast();

const show = () => {
    toast.add({ group: 'action', summary: 'Allow camera access', detail: 'We need access to your camera to scan QR codes.' });
};

const enableCamera = () => {
    toast.removeGroup('action');
    toast.add({ group: 'action', severity: 'success', summary: 'Camera access granted', detail: 'You can now scan QR codes.', life: 3000 });
};
<\/script>
```

## Accessibility

Screen Reader Toast component use alert role that implicitly defines aria-live as "assertive" and aria-atomic as "true". Close element is a button with an aria-label that refers to the aria.close property of the locale API by default, you may use closeButtonProps to customize the element and override the default aria-label . In stacked mode, moving keyboard focus into the toast group expands the stack so hidden close buttons remain reachable. Close Button Keyboard Support Key Function enter Closes the message. space Closes the message.

## Toast API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| group | string | - | Unique identifier of a message group. |
| position | "center" \| "top-left" \| "top-center" \| "top-right" \| "bottom-left" \| "bottom-center" \| "bottom-right" | top-right | Position of the toast in viewport. |
| mode | "stacked" \| "expanded" | stacked | Display mode of the toast. In stacked mode, toasts overlap and expand on hover. |
| gap | number | 12 | Gap between stacked toast items in pixels.     * |
| limit | number | 3 | Maximum number of visible toasts in the stack.     * |
| autoZIndex | boolean | true | Whether to automatically manage layering. |
| baseZIndex | number | 0 | Base zIndex value to use in layering. |
| breakpoints | ToastBreakpointsType | - | Object literal to define styles per screen size. |
| closeIcon | string | - | Icon to display in the toast close button. |
| infoIcon | string | - | Icon to display in the toast with info severity. |
| warnIcon | string | - | Icon to display in the toast with warn severity. |
| errorIcon | string | - | Icon to display in the toast with error severity. |
| successIcon | string | - | Icon to display in the toast with success severity. |
| secondaryIcon | string | - | Icon to display in the toast with secondary severity. |
| contrastIcon | string | - | Icon to display in the toast with contrast severity. |
| closeButtonProps | ButtonHTMLAttributes | - | Used to pass all properties of the HTMLButtonElement to the close button. |
| message | ToastMessageOptions | - | Used to access message options. |
| onMouseEnter | Function | - | Used to specify a callback function to be run when the mouseenter event is fired on the message component. |
| onMouseLeave | Function | - | Used to specify a callback function to be run when the mouseleave event is fired on the message component. |
| onClick | Function | - | Used to specify a callback function to be run when the click event is fired on the message component. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ToastPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| message | ToastPassThroughOptionType | Used to pass attributes to the message's DOM element. |
| messageContent | ToastPassThroughOptionType | Used to pass attributes to the message content's DOM element. |
| messageIcon | ToastPassThroughOptionType | Used to pass attributes to the message icon's DOM element. |
| messageText | ToastPassThroughOptionType | Used to pass attributes to the message text's DOM element. |
| summary | ToastPassThroughOptionType | Used to pass attributes to the summary's DOM element. |
| detail | ToastPassThroughOptionType | Used to pass attributes to the detail's DOM element. |
| buttonContainer | ToastPassThroughOptionType | Used to pass attributes to the button container's DOM element. |
| closeButton | ToastPassThroughOptionType | Used to pass attributes to the button's DOM element. |
| closeIcon | ToastPassThroughOptionType | Used to pass attributes to the button icon's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-toast | Class name of the root element |
| p-toast-message | Class name of the message element |
| p-toast-message-content | Class name of the message content element |
| p-toast-message-icon | Class name of the message icon element |
| p-toast-message-text | Class name of the message text element |
| p-toast-summary | Class name of the summary element |
| p-toast-detail | Class name of the detail element |
| p-toast-close-button | Class name of the close button element |
| p-toast-close-icon | Class name of the close icon element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| toast.width | --p-toast-width | Width of root |
| toast.border.radius | --p-toast-border-radius | Border radius of root |
| toast.border.width | --p-toast-border-width | Border width of root |
| toast.transition.duration | --p-toast-transition-duration | Transition duration of root |
| toast.blur | --p-toast-blur | Used to pass tokens of the blur section |
| toast.focus.ring.width | --p-toast-focus-ring-width | Focus ring width of root |
| toast.focus.ring.style | --p-toast-focus-ring-style | Focus ring style of root |
| toast.focus.ring.color | --p-toast-focus-ring-color | Focus ring color of root |
| toast.focus.ring.offset | --p-toast-focus-ring-offset | Focus ring offset of root |
| toast.focus.ring.shadow | --p-toast-focus-ring-shadow | Focus ring shadow of root |
| toast.icon.size | --p-toast-icon-size | Size of icon |
| toast.icon.margin | --p-toast-icon-margin | Margin of icon |
| toast.content.padding | --p-toast-content-padding | Padding of content |
| toast.content.gap | --p-toast-content-gap | Gap of content |
| toast.text.gap | --p-toast-text-gap | Gap of text |
| toast.summary.font.weight | --p-toast-summary-font-weight | Font weight of summary |
| toast.summary.font.size | --p-toast-summary-font-size | Font size of summary |
| toast.detail.font.weight | --p-toast-detail-font-weight | Font weight of detail |
| toast.detail.font.size | --p-toast-detail-font-size | Font size of detail |
| toast.close.button.width | --p-toast-close-button-width | Width of close button |
| toast.close.button.height | --p-toast-close-button-height | Height of close button |
| toast.close.button.border.radius | --p-toast-close-button-border-radius | Border radius of close button |
| toast.close.button.focus.ring.width | --p-toast-close-button-focus-ring-width | Focus ring width of close button |
| toast.close.button.focus.ring.style | --p-toast-close-button-focus-ring-style | Focus ring style of close button |
| toast.close.button.focus.ring.offset | --p-toast-close-button-focus-ring-offset | Focus ring offset of close button |
| toast.close.icon.size | --p-toast-close-icon-size | Size of close icon |
| toast.normal.background | --p-toast-normal-background | Background of normal |
| toast.normal.border.color | --p-toast-normal-border-color | Border color of normal |
| toast.normal.color | --p-toast-normal-color | Color of normal |
| toast.normal.detail.color | --p-toast-normal-detail-color | Detail color of normal |
| toast.normal.shadow | --p-toast-normal-shadow | Shadow of normal |
| toast.normal.close.button.hover.background | --p-toast-normal-close-button-hover-background | Close button hover background of normal |
| toast.normal.close.button.focus.ring.color | --p-toast-normal-close-button-focus-ring-color | Close button focus ring color of normal |
| toast.normal.close.button.focus.ring.shadow | --p-toast-normal-close-button-focus-ring-shadow | Close button focus ring shadow of normal |
| toast.info.background | --p-toast-info-background | Background of info |
| toast.info.border.color | --p-toast-info-border-color | Border color of info |
| toast.info.color | --p-toast-info-color | Color of info |
| toast.info.detail.color | --p-toast-info-detail-color | Detail color of info |
| toast.info.shadow | --p-toast-info-shadow | Shadow of info |
| toast.info.close.button.hover.background | --p-toast-info-close-button-hover-background | Close button hover background of info |
| toast.info.close.button.focus.ring.color | --p-toast-info-close-button-focus-ring-color | Close button focus ring color of info |
| toast.info.close.button.focus.ring.shadow | --p-toast-info-close-button-focus-ring-shadow | Close button focus ring shadow of info |
| toast.success.background | --p-toast-success-background | Background of success |
| toast.success.border.color | --p-toast-success-border-color | Border color of success |
| toast.success.color | --p-toast-success-color | Color of success |
| toast.success.detail.color | --p-toast-success-detail-color | Detail color of success |
| toast.success.shadow | --p-toast-success-shadow | Shadow of success |
| toast.success.close.button.hover.background | --p-toast-success-close-button-hover-background | Close button hover background of success |
| toast.success.close.button.focus.ring.color | --p-toast-success-close-button-focus-ring-color | Close button focus ring color of success |
| toast.success.close.button.focus.ring.shadow | --p-toast-success-close-button-focus-ring-shadow | Close button focus ring shadow of success |
| toast.warn.background | --p-toast-warn-background | Background of warn |
| toast.warn.border.color | --p-toast-warn-border-color | Border color of warn |
| toast.warn.color | --p-toast-warn-color | Color of warn |
| toast.warn.detail.color | --p-toast-warn-detail-color | Detail color of warn |
| toast.warn.shadow | --p-toast-warn-shadow | Shadow of warn |
| toast.warn.close.button.hover.background | --p-toast-warn-close-button-hover-background | Close button hover background of warn |
| toast.warn.close.button.focus.ring.color | --p-toast-warn-close-button-focus-ring-color | Close button focus ring color of warn |
| toast.warn.close.button.focus.ring.shadow | --p-toast-warn-close-button-focus-ring-shadow | Close button focus ring shadow of warn |
| toast.error.background | --p-toast-error-background | Background of error |
| toast.error.border.color | --p-toast-error-border-color | Border color of error |
| toast.error.color | --p-toast-error-color | Color of error |
| toast.error.detail.color | --p-toast-error-detail-color | Detail color of error |
| toast.error.shadow | --p-toast-error-shadow | Shadow of error |
| toast.error.close.button.hover.background | --p-toast-error-close-button-hover-background | Close button hover background of error |
| toast.error.close.button.focus.ring.color | --p-toast-error-close-button-focus-ring-color | Close button focus ring color of error |
| toast.error.close.button.focus.ring.shadow | --p-toast-error-close-button-focus-ring-shadow | Close button focus ring shadow of error |
| toast.secondary.background | --p-toast-secondary-background | Background of secondary |
| toast.secondary.border.color | --p-toast-secondary-border-color | Border color of secondary |
| toast.secondary.color | --p-toast-secondary-color | Color of secondary |
| toast.secondary.detail.color | --p-toast-secondary-detail-color | Detail color of secondary |
| toast.secondary.shadow | --p-toast-secondary-shadow | Shadow of secondary |
| toast.secondary.close.button.hover.background | --p-toast-secondary-close-button-hover-background | Close button hover background of secondary |
| toast.secondary.close.button.focus.ring.color | --p-toast-secondary-close-button-focus-ring-color | Close button focus ring color of secondary |
| toast.secondary.close.button.focus.ring.shadow | --p-toast-secondary-close-button-focus-ring-shadow | Close button focus ring shadow of secondary |
| toast.contrast.background | --p-toast-contrast-background | Background of contrast |
| toast.contrast.border.color | --p-toast-contrast-border-color | Border color of contrast |
| toast.contrast.color | --p-toast-contrast-color | Color of contrast |
| toast.contrast.detail.color | --p-toast-contrast-detail-color | Detail color of contrast |
| toast.contrast.shadow | --p-toast-contrast-shadow | Shadow of contrast |
| toast.contrast.close.button.hover.background | --p-toast-contrast-close-button-hover-background | Close button hover background of contrast |
| toast.contrast.close.button.focus.ring.color | --p-toast-contrast-close-button-focus-ring-color | Close button focus ring color of contrast |
| toast.contrast.close.button.focus.ring.shadow | --p-toast-contrast-close-button-focus-ring-shadow | Close button focus ring shadow of contrast |

## Toast Service Use Toast API
