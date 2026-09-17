# Chip

Chip represents entities using icons, labels and images.

## Basic

Displays compact information with an optional remove action.

```vue
<template>
    <div class="flex items-center justify-center">
        <Chip label="GitHub">
            <template #icon>
                <Github />
            </template>
        </Chip>
    </div>
</template>

<script setup>
import Chip from 'primevue/chip';
import Github from '@primeicons/vue/github';
<\/script>
```

## Icon

A font icon next to the label can be displayed with the icon property. Use removable to add a remove action.

```vue
<template>
    <div class="flex items-center justify-center flex-wrap gap-2">
        <Chip label="Apple">
            <template #icon>
                <Apple />
            </template>
        </Chip>
        <Chip label="Facebook">
            <template #icon>
                <Facebook />
            </template>
        </Chip>
        <Chip label="Google">
            <template #icon>
                <Google />
            </template>
        </Chip>
        <Chip label="Microsoft">
            <template #icon>
                <Microsoft />
            </template>
        </Chip>
        <Chip label="GitHub" removable>
            <template #icon>
                <Github />
            </template>
        </Chip>
    </div>
</template>

<script setup>
import Chip from 'primevue/chip';
import Apple from '@primeicons/vue/apple';
import Facebook from '@primeicons/vue/facebook';
import Github from '@primeicons/vue/github';
import Google from '@primeicons/vue/google';
import Microsoft from '@primeicons/vue/microsoft';
<\/script>
```

## Image

The image property is used to display an image like an avatar.

```vue
<template>
    <div class="flex items-center justify-center flex-wrap gap-2">
        <Chip label="Amy Elsner" image="https://primefaces.org/cdn/primevue/images/avatar/amyelsner.png" />
        <Chip label="Asiya Javayant" image="https://primefaces.org/cdn/primevue/images/avatar/asiyajavayant.png" />
        <Chip label="Onyama Limba" image="https://primefaces.org/cdn/primevue/images/avatar/onyamalimba.png" />
        <Chip label="Xuxue Feng" image="https://primefaces.org/cdn/primevue/images/avatar/xuxuefeng.png" removable />
    </div>
</template>

<script setup>
import Chip from 'primevue/chip';
<\/script>
```

## Template

Chip also allows displaying custom content inside itself.

```vue
<template>
    <div class="flex items-center justify-center flex-wrap gap-2">
        <Chip label="Apple" class="bg-neutral-900! dark:bg-neutral-50! text-neutral-50! dark:text-neutral-900!">
            <template #icon>
                <Apple />
            </template>
        </Chip>
        <Chip label="Facebook" class="bg-blue-50! dark:bg-blue-950! text-blue-700! dark:text-blue-300!">
            <template #icon>
                <Facebook />
            </template>
        </Chip>
        <Chip label="Google" class="bg-red-50! dark:bg-red-950! text-red-700! dark:text-red-300!">
            <template #icon>
                <Google />
            </template>
        </Chip>
        <Chip label="Microsoft" class="bg-green-50! dark:bg-green-950! text-green-700! dark:text-green-300!">
            <template #icon>
                <Microsoft />
            </template>
        </Chip>
        <Chip label="GitHub" removable class="bg-purple-50! dark:bg-purple-950! text-purple-700! dark:text-purple-300!">
            <template #icon>
                <Github />
            </template>
        </Chip>
    </div>
</template>

<script setup>
import Chip from 'primevue/chip';
import Apple from '@primeicons/vue/apple';
import Facebook from '@primeicons/vue/facebook';
import Github from '@primeicons/vue/github';
import Google from '@primeicons/vue/google';
import Microsoft from '@primeicons/vue/microsoft';
<\/script>
```

## Style

List of class names used in the styled mode.

## Accessibility

Screen Reader Chip uses the label property as the default aria-label , since any attribute is passed to the root element aria-labelledby or aria-label can be used to override the default behavior. Removable chips have a tabindex and focusable with the tab key. Keyboard Support Key Function backspace Hides removable. enter Hides removable.

## Chip API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| label | string \| number | - | Defines the text to display. |
| icon | string | - | Defines the icon to display. |
| image | string | - | Defines the image to display. |
| removable | boolean | false | Whether to display a remove icon. |
| removeIcon | string | - | Icon of the remove element. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | ChipPassThroughOptionType<T> | Used to pass attributes to the root's DOM element. |
| image | ChipPassThroughOptionType<T> | Used to pass attributes to the image's DOM element. |
| icon | ChipPassThroughOptionType<T> | Used to pass attributes to the icon's DOM element. |
| label | ChipPassThroughOptionType<T> | Used to pass attributes to the label' DOM element. |
| removeIcon | ChipPassThroughOptionType<T> | Used to pass attributes to the removeIcon's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-chip | Class name of the root element |
| p-chip-image | Class name of the image element |
| p-chip-icon | Class name of the icon element |
| p-chip-label | Class name of the label element |
| p-chip-remove-icon | Class name of the remove icon element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| chip.border.radius | --p-chip-border-radius | Border radius of root |
| chip.padding.x | --p-chip-padding-x | Padding x of root |
| chip.padding.y | --p-chip-padding-y | Padding y of root |
| chip.gap | --p-chip-gap | Gap of root |
| chip.transition.duration | --p-chip-transition-duration | Transition duration of root |
| chip.background | --p-chip-background | Background of root |
| chip.focus.background | --p-chip-focus-background | Focus background of root |
| chip.color | --p-chip-color | Color of root |
| chip.image.width | --p-chip-image-width | Width of image |
| chip.image.height | --p-chip-image-height | Height of image |
| chip.icon.size | --p-chip-icon-size | Size of icon |
| chip.icon.color | --p-chip-icon-color | Color of icon |
| chip.label.font.weight | --p-chip-label-font-weight | Font weight of label |
| chip.label.font.size | --p-chip-label-font-size | Font size of label |
| chip.remove.icon.size | --p-chip-remove-icon-size | Size of remove icon |
| chip.remove.icon.focus.ring.width | --p-chip-remove-icon-focus-ring-width | Focus ring width of remove icon |
| chip.remove.icon.focus.ring.style | --p-chip-remove-icon-focus-ring-style | Focus ring style of remove icon |
| chip.remove.icon.focus.ring.color | --p-chip-remove-icon-focus-ring-color | Focus ring color of remove icon |
| chip.remove.icon.focus.ring.offset | --p-chip-remove-icon-focus-ring-offset | Focus ring offset of remove icon |
| chip.remove.icon.focus.ring.shadow | --p-chip-remove-icon-focus-ring-shadow | Focus ring shadow of remove icon |
| chip.remove.icon.color | --p-chip-remove-icon-color | Color of remove icon |
