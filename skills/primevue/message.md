# Message

Message component is used to display inline messages.

## Basic

An inline message for informational, success, warning, or error feedback.

```vue
<template>
    <div class="max-w-sm mx-auto">
        <Message severity="info" closable>
            <template #icon>
                <Sparkles />
            </template>
            Upgrade now and save %5.
        </Message>
    </div>
</template>

<script setup>
import Sparkles from '@primeicons/vue/sparkles';
<\/script>
```

## Severity

The severity option specifies the type of the message.

```vue
<template>
    <div class="max-w-md mx-auto space-y-4">
        <Message severity="success" closable>
            <template #icon>
                <Check />
            </template>
            Your account is now ready.
        </Message>
        <Message severity="info" closable>
            <template #icon>
                <Sparkles />
            </template>
            Upgrade now and save %5.
        </Message>
        <Message severity="warn" closable>
            <template #icon>
                <Receipt />
            </template>
            Your subscription is about to expire.
        </Message>
        <Message severity="error" closable>
            <template #icon>
                <ExclamationTriangle />
            </template>
            Something went wrong.
        </Message>
        <Message severity="secondary" closable>
            <template #icon>
                <Spinner spin />
            </template>
            Processing may take a few moments.
        </Message>
        <Message severity="contrast" closable>
            <template #icon>
                <Wifi />
            </template>
            You're currently in offline mode.
        </Message>
    </div>
</template>

<script setup>
import Check from '@primeicons/vue/check';
import ExclamationTriangle from '@primeicons/vue/exclamation-triangle';
import Receipt from '@primeicons/vue/receipt';
import Sparkles from '@primeicons/vue/sparkles';
import Spinner from '@primeicons/vue/spinner';
import Wifi from '@primeicons/vue/wifi';
<\/script>
```

## Icon

The icon of a message is specified with the icon property or the icon template.

```vue
<template>
    <div class="max-w-sm mx-auto space-y-4">
        <Message severity="warn">
            <template #icon>
                <Receipt />
            </template>
            Your subscription is about to expire.
        </Message>
        <Message severity="info">
            <template #icon>
                <Avatar image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" shape="circle" />
            </template>
            <span class="ms-2">How may I help you?</span>
        </Message>
    </div>
</template>

<script setup>
import Receipt from '@primeicons/vue/receipt';
<\/script>
```

## Variant

Configure the variant value as outlined or simple .

```vue
<template>
    <div class="space-y-8 max-w-sm mx-auto">
        <div class="space-y-4">
            <h3 class="text-lg font-semibold mb-2">Outlined</h3>
            <Message severity="success" variant="outlined" closable>
                <template #icon>
                    <Check />
                </template>
                Your account is now ready.
            </Message>
            <Message severity="info" variant="outlined" closable>
                <template #icon>
                    <Sparkles />
                </template>
                <a href="" class="decoration-1! underline!">Upgrade</a> now and save %5.
            </Message>
            <Message severity="warn" variant="outlined" closable>
                <template #icon>
                    <Receipt />
                </template>
                Your subscription is about to expire. <a href="" class="decoration-1! underline!">Renew</a>
            </Message>
            <Message severity="error" variant="outlined" closable>
                <template #icon>
                    <ExclamationTriangle />
                </template>
                Something went wrong. Please <a href="" class="decoration-1! underline!">try again</a>.
            </Message>
            <Message severity="secondary" variant="outlined" closable>
                <template #icon>
                    <Spinner spin />
                </template>
                Processing may take a few moments.
            </Message>
            <Message severity="contrast" variant="outlined" closable>
                <template #icon>
                    <Wifi />
                </template>
                You're currently in offline mode.
            </Message>
        </div>
        <div class="space-y-4">
            <h3 class="text-lg font-semibold mb-2">Simple</h3>
            <Message severity="success" variant="simple" closable>
                <template #icon>
                    <Check />
                </template>
                Your account is now ready.
            </Message>
            <Message severity="info" variant="simple" closable>
                <template #icon>
                    <Sparkles />
                </template>
                <a href="" class="decoration-1! underline!">Upgrade</a> now and save %5.
            </Message>
            <Message severity="warn" variant="simple" closable>
                <template #icon>
                    <Receipt />
                </template>
                Your subscription is about to expire. <a href="" class="decoration-1! underline!">Renew</a>
            </Message>
            <Message severity="error" variant="simple" closable>
                <template #icon>
                    <ExclamationTriangle />
                </template>
                Something went wrong. Please <a href="" class="decoration-1! underline!">try again</a>.
            </Message>
            <Message severity="secondary" variant="simple" closable>
                <template #icon>
                    <Spinner spin />
                </template>
                Processing may take a few moments.
            </Message>
            <Message severity="contrast" variant="simple" closable>
                <template #icon>
                    <Wifi />
                </template>
                You're currently in offline mode.
            </Message>
        </div>
    </div>
</template>

<script setup>
import Check from '@primeicons/vue/check';
import ExclamationTriangle from '@primeicons/vue/exclamation-triangle';
import Receipt from '@primeicons/vue/receipt';
import Sparkles from '@primeicons/vue/sparkles';
import Spinner from '@primeicons/vue/spinner';
import Wifi from '@primeicons/vue/wifi';
<\/script>
```

## Sizes

Message provides small and large sizes as alternatives to the base.

```vue
<template>
    <div class="flex flex-col items-center gap-4">
        <Message severity="info" size="small" closable>
            <template #icon>
                <Sparkles />
            </template>
            Upgrade now and save %5.
        </Message>
        <Message severity="info" closable>
            <template #icon>
                <Sparkles />
            </template>
            Upgrade now and save %5.
        </Message>
        <Message severity="info" size="large" closable>
            <template #icon>
                <Sparkles />
            </template>
            Upgrade now and save %5.
        </Message>
    </div>
</template>

<script setup>
import Sparkles from '@primeicons/vue/sparkles';
<\/script>
```

## Dynamic

Multiple messages can be displayed using the standard v-for directive.

```vue
<template>
    <div class="flex flex-col items-center justify-center gap-4">
        <div class="flex gap-2">
            <Button @click="addMessages()">Add Messages</Button>
            <Button severity="secondary" @click="clearMessages()">Clear Messages</Button>
        </div>
        <div class="flex flex-col">
            <Message v-for="(message, index) of messages" :key="message.severity" :severity="message.severity" :class="{ 'mt-4': index !== 0 }" :closable="message.closable">{{ message.content }}</Message>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const messages = ref([]);

const addMessages = () => {
    messages.value = [
        { severity: 'info', content: 'Dynamic Info Message' },
        { severity: 'success', content: 'Dynamic Success Message' },
        { severity: 'warn', content: 'Dynamic Warn Message' }
    ];
};

const clearMessages = () => {
    messages.value = [];
};
<\/script>
```

## Closable

Enable closable option to display an icon to remove a message.

```vue
<template>
    <div class="max-w-xs mx-auto">
        <Message closable>This is a closable message.</Message>
    </div>
</template>

<script setup>
<\/script>
```

## Life

Messages can disappear automatically by defined the life in milliseconds.

```vue
<template>
    <div class="flex flex-col items-center justify-center gap-4">
        <Button :disabled="visible" @click="showMessage">Show Message</Button>
        <Message v-if="visible" :life="3000" severity="success">
            <template #icon>
                <Check />
            </template>
            Your account is now ready.
        </Message>
    </div>
</template>

<script setup>
import Check from '@primeicons/vue/check';
import { ref } from 'vue';

const visible = ref(false);

const showMessage = () => {
    visible.value = true;

    setTimeout(() => {
        visible.value = false;
    }, 3000);
};
<\/script>
```

## Forms

Validation errors in a form are displayed with the error severity.

```vue
<template>
    <div class="flex justify-center">
        <div class="flex flex-col gap-4">
            <Message severity="error" class="mb-2">
                <template #icon>
                    <TimesCircle />
                </template>
                Validation Failed
            </Message>
            <div class="flex flex-col gap-1">
                <InputText v-model="username" placeholder="Username" aria-label="username" :invalid="!username" />
                <Message v-if="!username" severity="error" variant="simple" size="small">Username is required</Message>
            </div>
            <div class="flex flex-col gap-1">
                <InputMask v-model="phone" mask="(999) 999-9999" placeholder="Phone" :invalid="!phone" />
                <Message v-if="!phone" severity="error" variant="simple" size="small">Phone number is required</Message>
            </div>
        </div>
    </div>
</template>

<script setup>
import TimesCircle from '@primeicons/vue/times-circle';
import { ref } from 'vue';

const username = ref(null);
const phone = ref(null);
<\/script>
```

## Accessibility

Screen Reader Message component uses alert role that implicitly defines aria-live as "assertive" and aria-atomic as "true". Since any attribute is passed to the root element, attributes like aria-labelledby and aria-label can optionally be used as well. Close element is a button with an aria-label that refers to the aria.close property of the locale API by default, you may use closeButtonProps to customize the element and override the default aria-label . Close Button Keyboard Support Key Function enter Closes the message. space Closes the message.

## Message API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| severity | any | info | Severity level of the message. |
| closable | boolean | false | Whether the message can be closed manually using the close icon. |
| life | number | null | Delay in milliseconds to close the message automatically. |
| icon | string | - | Display a custom icon for the message. |
| closeIcon | string | - | Icon to display in the message close button. |
| closeButtonProps | ButtonHTMLAttributes | - | Used to pass all properties of the HTMLButtonElement to the close button. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |
| size | any | - | Defines the size of the component. |
| variant | any | undefined | Specifies the variant of the component. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | MessagePassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| contentWrapper | MessagePassThroughOptionType<T> | Used to pass attributes to the content wrapper DOM element. |
| content | MessagePassThroughOptionType<T> | Used to pass attributes to the content's DOM element. |
| icon | MessagePassThroughOptionType<T> | Used to pass attributes to the icon's DOM element. |
| text | MessagePassThroughOptionType<T> | Used to pass attributes to the text's DOM element. |
| closeButton | MessagePassThroughOptionType<T> | Used to pass attributes to the button's DOM element. |
| closeIcon | MessagePassThroughOptionType<T> | Used to pass attributes to the button icon's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |
| transition | MessagePassThroughTransitionType<T> | Used to control Vue Transition API. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-message | Class name of the root element |
| p-message-content | Class name of the content element |
| p-message-icon | Class name of the icon element |
| p-message-text | Class name of the text element |
| p-message-close-button | Class name of the close button element |
| p-message-close-icon | Class name of the close icon element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| message.border.radius | --p-message-border-radius | Border radius of root |
| message.border.width | --p-message-border-width | Border width of root |
| message.transition.duration | --p-message-transition-duration | Transition duration of root |
| message.content.padding | --p-message-content-padding | Padding of content |
| message.content.gap | --p-message-content-gap | Gap of content |
| message.content.sm.padding | --p-message-content-sm-padding | Sm padding of content |
| message.content.lg.padding | --p-message-content-lg-padding | Lg padding of content |
| message.text.font.size | --p-message-text-font-size | Font size of text |
| message.text.font.weight | --p-message-text-font-weight | Font weight of text |
| message.text.sm.font.size | --p-message-text-sm-font-size | Sm font size of text |
| message.text.lg.font.size | --p-message-text-lg-font-size | Lg font size of text |
| message.icon.size | --p-message-icon-size | Size of icon |
| message.icon.sm.size | --p-message-icon-sm-size | Sm size of icon |
| message.icon.lg.size | --p-message-icon-lg-size | Lg size of icon |
| message.close.button.width | --p-message-close-button-width | Width of close button |
| message.close.button.height | --p-message-close-button-height | Height of close button |
| message.close.button.border.radius | --p-message-close-button-border-radius | Border radius of close button |
| message.close.button.focus.ring.width | --p-message-close-button-focus-ring-width | Focus ring width of close button |
| message.close.button.focus.ring.style | --p-message-close-button-focus-ring-style | Focus ring style of close button |
| message.close.button.focus.ring.offset | --p-message-close-button-focus-ring-offset | Focus ring offset of close button |
| message.close.icon.size | --p-message-close-icon-size | Size of close icon |
| message.close.icon.sm.size | --p-message-close-icon-sm-size | Sm size of close icon |
| message.close.icon.lg.size | --p-message-close-icon-lg-size | Lg size of close icon |
| message.outlined.border.width | --p-message-outlined-border-width | Root border width of outlined |
| message.simple.content.padding | --p-message-simple-content-padding | Content padding of simple |
| message.info.background | --p-message-info-background | Background of info |
| message.info.border.color | --p-message-info-border-color | Border color of info |
| message.info.color | --p-message-info-color | Color of info |
| message.info.shadow | --p-message-info-shadow | Shadow of info |
| message.info.close.button.hover.background | --p-message-info-close-button-hover-background | Close button hover background of info |
| message.info.close.button.focus.ring.color | --p-message-info-close-button-focus-ring-color | Close button focus ring color of info |
| message.info.close.button.focus.ring.shadow | --p-message-info-close-button-focus-ring-shadow | Close button focus ring shadow of info |
| message.info.outlined.color | --p-message-info-outlined-color | Outlined color of info |
| message.info.outlined.border.color | --p-message-info-outlined-border-color | Outlined border color of info |
| message.info.simple.color | --p-message-info-simple-color | Simple color of info |
| message.success.background | --p-message-success-background | Background of success |
| message.success.border.color | --p-message-success-border-color | Border color of success |
| message.success.color | --p-message-success-color | Color of success |
| message.success.shadow | --p-message-success-shadow | Shadow of success |
| message.success.close.button.hover.background | --p-message-success-close-button-hover-background | Close button hover background of success |
| message.success.close.button.focus.ring.color | --p-message-success-close-button-focus-ring-color | Close button focus ring color of success |
| message.success.close.button.focus.ring.shadow | --p-message-success-close-button-focus-ring-shadow | Close button focus ring shadow of success |
| message.success.outlined.color | --p-message-success-outlined-color | Outlined color of success |
| message.success.outlined.border.color | --p-message-success-outlined-border-color | Outlined border color of success |
| message.success.simple.color | --p-message-success-simple-color | Simple color of success |
| message.warn.background | --p-message-warn-background | Background of warn |
| message.warn.border.color | --p-message-warn-border-color | Border color of warn |
| message.warn.color | --p-message-warn-color | Color of warn |
| message.warn.shadow | --p-message-warn-shadow | Shadow of warn |
| message.warn.close.button.hover.background | --p-message-warn-close-button-hover-background | Close button hover background of warn |
| message.warn.close.button.focus.ring.color | --p-message-warn-close-button-focus-ring-color | Close button focus ring color of warn |
| message.warn.close.button.focus.ring.shadow | --p-message-warn-close-button-focus-ring-shadow | Close button focus ring shadow of warn |
| message.warn.outlined.color | --p-message-warn-outlined-color | Outlined color of warn |
| message.warn.outlined.border.color | --p-message-warn-outlined-border-color | Outlined border color of warn |
| message.warn.simple.color | --p-message-warn-simple-color | Simple color of warn |
| message.error.background | --p-message-error-background | Background of error |
| message.error.border.color | --p-message-error-border-color | Border color of error |
| message.error.color | --p-message-error-color | Color of error |
| message.error.shadow | --p-message-error-shadow | Shadow of error |
| message.error.close.button.hover.background | --p-message-error-close-button-hover-background | Close button hover background of error |
| message.error.close.button.focus.ring.color | --p-message-error-close-button-focus-ring-color | Close button focus ring color of error |
| message.error.close.button.focus.ring.shadow | --p-message-error-close-button-focus-ring-shadow | Close button focus ring shadow of error |
| message.error.outlined.color | --p-message-error-outlined-color | Outlined color of error |
| message.error.outlined.border.color | --p-message-error-outlined-border-color | Outlined border color of error |
| message.error.simple.color | --p-message-error-simple-color | Simple color of error |
| message.secondary.background | --p-message-secondary-background | Background of secondary |
| message.secondary.border.color | --p-message-secondary-border-color | Border color of secondary |
| message.secondary.color | --p-message-secondary-color | Color of secondary |
| message.secondary.shadow | --p-message-secondary-shadow | Shadow of secondary |
| message.secondary.close.button.hover.background | --p-message-secondary-close-button-hover-background | Close button hover background of secondary |
| message.secondary.close.button.focus.ring.color | --p-message-secondary-close-button-focus-ring-color | Close button focus ring color of secondary |
| message.secondary.close.button.focus.ring.shadow | --p-message-secondary-close-button-focus-ring-shadow | Close button focus ring shadow of secondary |
| message.secondary.outlined.color | --p-message-secondary-outlined-color | Outlined color of secondary |
| message.secondary.outlined.border.color | --p-message-secondary-outlined-border-color | Outlined border color of secondary |
| message.secondary.simple.color | --p-message-secondary-simple-color | Simple color of secondary |
| message.contrast.background | --p-message-contrast-background | Background of contrast |
| message.contrast.border.color | --p-message-contrast-border-color | Border color of contrast |
| message.contrast.color | --p-message-contrast-color | Color of contrast |
| message.contrast.shadow | --p-message-contrast-shadow | Shadow of contrast |
| message.contrast.close.button.hover.background | --p-message-contrast-close-button-hover-background | Close button hover background of contrast |
| message.contrast.close.button.focus.ring.color | --p-message-contrast-close-button-focus-ring-color | Close button focus ring color of contrast |
| message.contrast.close.button.focus.ring.shadow | --p-message-contrast-close-button-focus-ring-shadow | Close button focus ring shadow of contrast |
| message.contrast.outlined.color | --p-message-contrast-outlined-color | Outlined color of contrast |
| message.contrast.outlined.border.color | --p-message-contrast-outlined-border-color | Outlined border color of contrast |
| message.contrast.simple.color | --p-message-contrast-simple-color | Simple color of contrast |
