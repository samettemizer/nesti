# ConfirmDialog

ConfirmDialog is backed by a service utilizing Observables to display confirmation windows easily that can be shared by multiple actions on the same component.

## Service

ConfirmDialog is controlled via the ConfirmationService that needs to be installed as an application plugin. The service is available with the useConfirm function for Composition API or using the $confirm property of the application for Options API.

## Basic

ConfirmDialog is defined using the ConfirmDialog component and an instance of ConfirmationService is required to display it by calling the require method.

```vue
<template>
    <Toast />
    <ConfirmDialog></ConfirmDialog>
    <div class="flex flex-wrap gap-2 justify-center">
        <Button @click="confirm1()" variant="outlined">Save</Button>
        <Button @click="confirm2()" severity="danger" variant="outlined">Delete</Button>
    </div>
</template>

<script setup>
import ExclamationTriangle from '@primeicons/vue/exclamation-triangle';
import InfoCircle from '@primeicons/vue/info-circle';
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

const confirm = useConfirm();
const toast = useToast();

const confirm1 = () => {
    confirm.require({
        message: 'Are you sure that you want to proceed?',
        header: 'Confirmation',
        icon: ExclamationTriangle,
        rejectProps: {
            label: 'Cancel',
            severity: 'secondary',
            outlined: true
        },
        acceptProps: {
            label: 'Save'
        },
        accept: () => {
            toast.add({ severity: 'info', summary: 'Confirmed', detail: 'You have accepted', life: 3000 });
        },
        reject: () => {
            toast.add({ severity: 'error', summary: 'Rejected', detail: 'You have rejected', life: 3000 });
        }
    });
};

const confirm2 = () => {
    confirm.require({
        message: 'Do you want to delete this record?',
        header: 'Danger Zone',
        icon: InfoCircle,
        rejectProps: {
            label: 'Cancel',
            severity: 'secondary',
            outlined: true
        },
        acceptProps: {
            label: 'Delete',
            severity: 'danger'
        },
        accept: () => {
            toast.add({ severity: 'info', summary: 'Confirmed', detail: 'Record deleted', life: 3000 });
        },
        reject: () => {
            toast.add({ severity: 'error', summary: 'Rejected', detail: 'You have rejected', life: 3000 });
        }
    });
};
<\/script>
```

## Position

The position property of the confirm options is used to display a Dialog at all edges and corners of the screen.

```vue
<template>
    <Toast />
    <ConfirmDialog group="positioned"></ConfirmDialog>
    <div>
        <div class="flex flex-wrap justify-center gap-2 mb-4">
            <Button @click="confirmPosition('left')" severity="secondary" class="min-w-40"> Left </Button>
            <Button @click="confirmPosition('right')" severity="secondary" class="min-w-40"> Right </Button>
        </div>
        <div class="flex flex-wrap justify-center gap-2 mb-4">
            <Button @click="confirmPosition('topleft')" severity="secondary" class="min-w-40"> TopLeft </Button>
            <Button @click="confirmPosition('top')" severity="secondary" class="min-w-40"> Top </Button>
            <Button @click="confirmPosition('topright')" severity="secondary" class="min-w-40"> TopRight </Button>
        </div>
        <div class="flex flex-wrap justify-center gap-2">
            <Button @click="confirmPosition('bottomleft')" severity="secondary" class="min-w-40"> BottomLeft </Button>
            <Button @click="confirmPosition('bottom')" severity="secondary" class="min-w-40"> Bottom </Button>
            <Button @click="confirmPosition('bottomright')" severity="secondary" class="min-w-40"> BottomRight </Button>
        </div>
    </div>
</template>

<script setup>
import InfoCircle from '@primeicons/vue/info-circle';
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

const confirm = useConfirm();
const toast = useToast();

const confirmPosition = (position) => {
    confirm.require({
        group: 'positioned',
        message: 'Are you sure you want to proceed?',
        header: 'Confirmation',
        icon: InfoCircle,
        position: position,
        rejectProps: {
            label: 'Cancel',
            severity: 'secondary',
            text: true
        },
        acceptProps: {
            label: 'Save',
            text: true
        },
        accept: () => {
            toast.add({ severity: 'info', summary: 'Confirmed', detail: 'Request submitted', life: 3000 });
        },
        reject: () => {
            toast.add({ severity: 'error', summary: 'Rejected', detail: 'Process incomplete', life: 3000 });
        }
    });
};
<\/script>
```

## Template

Properties of the dialog are defined in two ways, message , icon and header properties can either be defined using the require method or declaratively with the message and icon slots. If these values are unlikely to change then the declarative approach would be useful, still properties defined with the require method call would override the slot values. In addition, the footer section can be customized by passing your own UI via the container slot, an important note to make confirmation work with a custom UI is assigning the accept and reject callbacks to your own buttons.

```vue
<template>
    <ConfirmDialog group="templating">
        <template #message="{ message, icon }">
            <div class="flex flex-col items-center w-full gap-4 border-b border-surface-200 dark:border-surface-700">
                <component :is="icon" :size="60" class="text-primary-500" />
                <p class="text-sm">{{ message.message }}</p>
            </div>
        </template>
        <template #rejecticon>
            <Times />
        </template>
        <template #accepticon>
            <Check />
        </template>
    </ConfirmDialog>
    <div class="flex justify-center">
        <Button @click="showTemplate()">Save</Button>
    </div>
    <Toast />
</template>

<script setup>
import Check from '@primeicons/vue/check';
import ExclamationCircle from '@primeicons/vue/exclamation-circle';
import Times from '@primeicons/vue/times';
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

const confirm = useConfirm();
const toast = useToast();

const showTemplate = () => {
    confirm.require({
        group: 'templating',
        header: 'Confirmation',
        message: 'Please confirm to proceed moving forward.',
        icon: ExclamationCircle,
        rejectProps: {
            label: 'Cancel',
            outlined: true,
            size: 'small'
        },
        acceptProps: {
            label: 'Save',
            size: 'small'
        },
        accept: () => {
            toast.add({ severity: 'info', summary: 'Confirmed', detail: 'You have accepted', life: 3000 });
        },
        reject: () => {
            toast.add({ severity: 'error', summary: 'Rejected', detail: 'You have rejected', life: 3000 });
        }
    });
};
<\/script>
```

## Headless

Headless mode is enabled by defining a container slot that lets you implement entire confirmation UI instead of the default elements.

```vue
<template>
    <ConfirmDialog group="headless">
        <template #container="{ message, acceptCallback, rejectCallback }">
            <div class="flex flex-col items-center p-7 bg-surface-0 dark:bg-surface-900 rounded-sm">
                <div class="rounded-full bg-primary text-primary-contrast inline-flex justify-center items-center h-24 w-24 -mt-20">
                    <Question :size="48" />
                </div>
                <span class="font-bold text-xl block mb-2 mt-5">{{ message.header }}</span>
                <p class="mb-0 text-sm">{{ message.message }}</p>
                <div class="flex items-center gap-2 mt-5">
                    <Button @click="acceptCallback" class="w-32">Save</Button>
                    <Button variant="outlined" @click="rejectCallback" class="w-32">Cancel</Button>
                </div>
            </div>
        </template>
    </ConfirmDialog>
    <div class="flex justify-center">
        <Button @click="requireConfirmation()">Save</Button>
    </div>
    <Toast />
</template>

<script setup>
import Question from '@primeicons/vue/question';
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

const confirm = useConfirm();
const toast = useToast();

const requireConfirmation = () => {
    confirm.require({
        group: 'headless',
        header: 'Are you sure?',
        message: 'Please confirm to proceed.',
        accept: () => {
            toast.add({ severity: 'info', summary: 'Confirmed', detail: 'You have accepted', life: 3000 });
        },
        reject: () => {
            toast.add({ severity: 'error', summary: 'Rejected', detail: 'You have rejected', life: 3000 });
        }
    });
};
<\/script>
```

## Accessibility

Screen Reader ConfirmDialog component uses alertdialog role along with aria-labelledby referring to the header element however any attribute is passed to the root element so you may use aria-labelledby to override this default behavior. In addition aria-modal is added since focus is kept within the popup. It is recommended to use a trigger component that can be accessed with keyboard such as a button, if not adding tabIndex would be necessary. When require method of the $confirm instance is used and a trigger is passed as a parameter, ConfirmDialog adds aria-expanded state attribute and aria-controls to the trigger so that the relation between the trigger and the dialog is defined. If the dialog is controlled with the visible property aria-expanded and aria-controls need to be handled explicitly. Overlay Keyboard Support Key Function tab Moves focus to the next the focusable element within the dialog. shift + tab Moves focus to the previous the focusable element within the dialog. escape Closes the dialog. Buttons Keyboard Support Key Function enter Closes the dialog. space Closes the dialog.

## Confirm Dialog API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| group | string | - | Optional key to match the key of the confirmation, useful to target a specific confirm dialog instance. |
| breakpoints | ConfirmDialogBreakpoints | - | Object literal to define widths per screen size. |
| draggable | boolean | true | Enables dragging to change the position using header. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ConfirmDialogPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| header | ConfirmDialogPassThroughOptionType | Used to pass attributes to the header's DOM element. |
| title | ConfirmDialogPassThroughOptionType | Used to pass attributes to the header title's DOM element. |
| headerActions | ConfirmDialogPassThroughOptionType | Used to pass attributes to the header actions' DOM element. |
| pcCloseButton | ConfirmDialogPassThroughOptionType | Used to pass attributes to the close button's component. |
| content | ConfirmDialogPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| icon | ConfirmDialogPassThroughOptionType | Used to pass attributes to the icon's DOM element. |
| message | ConfirmDialogPassThroughOptionType | Used to pass attributes to the message's DOM element. |
| footer | ConfirmDialogPassThroughOptionType | Used to pass attributes to the footer's DOM element. |
| mask | ConfirmDialogPassThroughOptionType | Used to pass attributes to the mask's DOM element. |
| pcRejectButton | any | Used to pass attributes to the Button component. |
| pcAcceptButton | any | Used to pass attributes to the Button component. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | ConfirmDialogPassThroughOptionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-confirmdialog | Class name of the root element |
| p-confirmdialog-icon | Class name of the icon element |
| p-confirmdialog-message | Class name of the message element |
| p-confirmdialog-reject-button | Class name of the reject button element |
| p-confirmdialog-accept-button | Class name of the accept button element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| confirmdialog.icon.size | --p-confirmdialog-icon-size | Size of icon |
| confirmdialog.icon.color | --p-confirmdialog-icon-color | Color of icon |
| confirmdialog.content.gap | --p-confirmdialog-content-gap | Gap of content |
| confirmdialog.message.color | --p-confirmdialog-message-color | Color of message |
| confirmdialog.message.font.weight | --p-confirmdialog-message-font-weight | Font weight of message |
| confirmdialog.message.font.size | --p-confirmdialog-message-font-size | Font size of message |

## Confirmation Service Use Confirm API

## Confirmation Options API
