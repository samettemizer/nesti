# ConfirmPopup

ConfirmPopup displays a confirmation overlay displayed relatively to its target.

## Service

ConfirmPopup is controlled via the ConfirmationService that needs to be installed as an application plugin. The service is available with the useConfirm function for Composition API or using the $confirm property of the application for Options API.

## Basic

ConfirmPopup is displayed by calling the require method of the $confirm instance by passing the options to customize the Popup. The target attribute is mandatory to align the popup to its referrer.

```vue
<template>
    <Toast />
    <ConfirmPopup></ConfirmPopup>
    <div class="flex justify-center gap-2">
        <Button @click="confirm1($event)" variant="outlined">Save</Button>
        <Button @click="confirm2($event)" severity="danger" variant="outlined">Delete</Button>
    </div>
</template>

<script setup>
import ExclamationTriangle from '@primeicons/vue/exclamation-triangle';
import InfoCircle from '@primeicons/vue/info-circle';
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

const confirm = useConfirm();
const toast = useToast();

const confirm1 = (event) => {
    confirm.require({
        target: event.currentTarget,
        message: 'Are you sure you want to proceed?',
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

const confirm2 = (event) => {
    confirm.require({
        target: event.currentTarget,
        message: 'Do you want to delete this record?',
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

## Template

The message section can be customized using the message template.

```vue
<template>
    <Toast />
    <ConfirmPopup group="templating">
        <template #message="{ message, icon }">
            <div class="flex flex-col items-center w-full gap-4 border-b border-surface-200 dark:border-surface-700 p-4 mb-4 pb-0">
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
    </ConfirmPopup>
    <div class="flex justify-center">
        <Button @click="showTemplate($event)">Save</Button>
    </div>
</template>

<script setup>
import Check from '@primeicons/vue/check';
import ExclamationCircle from '@primeicons/vue/exclamation-circle';
import Times from '@primeicons/vue/times';
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

const confirm = useConfirm();
const toast = useToast();

const showTemplate = (event) => {
    confirm.require({
        target: event.currentTarget,
        group: 'templating',
        message: 'Please confirm to proceed moving forward.',
        icon: ExclamationCircle,
        rejectProps: {
            label: 'Cancel',
            outlined: true
        },
        acceptProps: {
            label: 'Confirm'
        },
        accept: () => {
            toast.add({severity:'info', summary:'Confirmed', detail:'You have accepted', life: 3000});
        },
        reject: () => {
            toast.add({severity:'error', summary:'Rejected', detail:'You have rejected', life: 3000});
        }
    });
}
<\/script>
```

## Headless

Headless mode is enabled by defining a container slot that lets you implement entire confirmation UI instead of the default elements.

```vue
<template>
    <Toast />
    <ConfirmPopup group="headless">
        <template #container="{ message, acceptCallback, rejectCallback }">
            <div class="rounded-sm p-4">
                <span class="text-sm">{{ message.message }}</span>
                <div class="flex items-center gap-2 mt-4">
                    <Button @click="acceptCallback" size="small">Save</Button>
                    <Button variant="outlined" @click="rejectCallback" severity="secondary" size="small" text>Cancel</Button>
                </div>
            </div>
        </template>
    </ConfirmPopup>
    <div class="flex justify-center">
        <Button @click="requireConfirmation($event)">Save</Button>
    </div>
</template>

<script setup>
import { useConfirm } from "primevue/useconfirm";
import { useToast } from "primevue/usetoast";

const confirm = useConfirm();
const toast = useToast();

const requireConfirmation = (event) => {
    confirm.require({
        target: event.currentTarget,
        group: 'headless',
        message: 'Save your current process?',
        accept: () => {
            toast.add({severity:'info', summary:'Confirmed', detail:'You have accepted', life: 3000});
        },
        reject: () => {
            toast.add({severity:'error', summary:'Rejected', detail:'You have rejected', life: 3000});
        }
    });
}
<\/script>
```

## Accessibility

Screen Reader ConfirmPopup component uses alertdialog role and since any attribute is passed to the root element you may define attributes like aria-label or aria-labelledby to describe the popup contents. In addition aria-modal is added since focus is kept within the popup. When require method of the $confirm instance is used and a trigger is passed as a parameter, ConfirmPopup adds aria-expanded state attribute and aria-controls to the trigger so that the relation between the trigger and the dialog is defined. Overlay Keyboard Support Key Function tab Moves focus to the next the focusable element within the popup. shift + tab Moves focus to the previous the focusable element within the popup. escape Closes the popup and moves focus to the trigger. Buttons Keyboard Support Key Function enter Triggers the action, closes the popup and moves focus to the trigger. space Triggers the action, closes the popup and moves focus to the trigger.

## Confirm Popup API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| group | string | - | Optional key to match the key of the confirmation, useful to target a specific confirm dialog instance. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ConfirmPopupPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| content | ConfirmPopupPassThroughOptionType | Used to pass attributes to the content's DOM element. |
| icon | ConfirmPopupPassThroughOptionType | Used to pass attributes to the icon's DOM element. |
| message | ConfirmPopupPassThroughOptionType | Used to pass attributes to the message's DOM element. |
| footer | ConfirmPopupPassThroughOptionType | Used to pass attributes to the footer's DOM element. |
| pcRejectButton | any | Used to pass attributes to the Button component. |
| pcAcceptButton | any | Used to pass attributes to the Button component. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | ConfirmPopupPassThroughTransitionType | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-confirmpopup | Class name of the root element |
| p-confirmpopup-content | Class name of the content element |
| p-confirmpopup-icon | Class name of the icon element |
| p-confirmpopup-message | Class name of the message element |
| p-confirmpopup-footer | Class name of the footer element |
| p-confirmpopup-reject-button | Class name of the reject button element |
| p-confirmpopup-accept-button | Class name of the accept button element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| confirmpopup.background | --p-confirmpopup-background | Background of root |
| confirmpopup.border.color | --p-confirmpopup-border-color | Border color of root |
| confirmpopup.color | --p-confirmpopup-color | Color of root |
| confirmpopup.border.radius | --p-confirmpopup-border-radius | Border radius of root |
| confirmpopup.shadow | --p-confirmpopup-shadow | Shadow of root |
| confirmpopup.gutter | --p-confirmpopup-gutter | Gutter of root |
| confirmpopup.arrow.offset | --p-confirmpopup-arrow-offset | Arrow offset of root |
| confirmpopup.content.padding | --p-confirmpopup-content-padding | Padding of content |
| confirmpopup.content.gap | --p-confirmpopup-content-gap | Gap of content |
| confirmpopup.icon.size | --p-confirmpopup-icon-size | Size of icon |
| confirmpopup.icon.color | --p-confirmpopup-icon-color | Color of icon |
| confirmpopup.message.color | --p-confirmpopup-message-color | Color of message |
| confirmpopup.message.font.weight | --p-confirmpopup-message-font-weight | Font weight of message |
| confirmpopup.message.font.size | --p-confirmpopup-message-font-size | Font size of message |
| confirmpopup.footer.gap | --p-confirmpopup-footer-gap | Gap of footer |
| confirmpopup.footer.padding | --p-confirmpopup-footer-padding | Padding of footer |

## Confirmation Service Use Confirm API

## Confirmation Options API
