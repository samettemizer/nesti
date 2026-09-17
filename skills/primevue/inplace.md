# Inplace

Inplace provides an easy to do editing and display at the same time where clicking the output displays the actual content.

## Basic

Inplace component requires display and content templates to define the content of each state.

```vue
<template>
    <div class="max-w-3xs mx-auto w-full">
        <div class="font-mono uppercase text-xs opacity-50 pl-2 mb-1">Name</div>
        <Inplace :pt="{ display: 'w-full' }">
            <template #display>
                <span class="w-full text-sm">John Doe</span>
            </template>
            <template #content="{ closeCallback }">
                <InputGroup class="flex items-center">
                    <InputText v-model="name" placeholder="Enter name" class="flex-1" fluid autofocus />
                    <InputGroupAddon>
                        <Button text severity="success">
                            <Check />
                        </Button>
                    </InputGroupAddon>
                    <InputGroupAddon>
                        <Button text severity="danger" @click="closeCallback">
                            <Times />
                        </Button>
                    </InputGroupAddon>
                </InputGroup>
            </template>
        </Inplace>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Check from '@primeicons/vue/check';
import Times from '@primeicons/vue/times';

const name = ref('');
<\/script>
```

## Controlled

The active state can be controlled programmatically with two-way binding on the active property.

```vue
<template>
    <div class="max-w-3xs mx-auto w-full">
        <div class="font-mono uppercase text-xs opacity-50 pl-2 mb-1">Name</div>
        <Inplace v-model:active="active" :pt="{ display: 'w-full' }">
            <template #display>
                <span class="w-full text-sm">John Doe</span>
            </template>
            <template #content>
                <InputText v-model="name" placeholder="Enter name" class="flex-1" fluid autofocus />
            </template>
        </Inplace>
        <div class="flex items-center gap-2 mt-2">
            <Button class="flex-1" variant="outlined" severity="secondary" @click="active = !active">{{ active ? 'Cancel' : 'Edit Name' }}</Button>
            <Button v-if="active" class="flex-1" variant="outlined" fluid @click="active = false">Save</Button>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';

const active = ref(false);
const name = ref('');
<\/script>
```

## Image

Any content such as an image can be placed inside an Inplace.

```vue
<template>
    <Inplace>
        <template #display>
            <span class="inline-flex items-center gap-2">
                <ImageIcon style="vertical-align: middle" />
                <span class="ml-2 text-sm">View Photo</span>
            </span>
        </template>
        <template #content>
            <img class="w-full sm:w-80 shadow-md" src="https://primefaces.org/cdn/primeng/images/demo/galleria/galleria5.jpg" alt="Nature" />
        </template>
    </Inplace>
</template>

<script setup>
import ImageIcon from "@primeicons/vue/image";
<\/script>
```

## Lazy

Using the open event, data can be loaded in a lazy manner before displaying it in a table.

```vue
<template>
    <Inplace @open="loadData">
        <template #display>
            <span class="text-sm">View Data</span>
        </template>
        <template #content>
            <DataTable :value="products">
                <Column field="code" header="Code"></Column>
                <Column field="name" header="Name"></Column>
                <Column field="category" header="Category"></Column>
                <Column field="quantity" header="Quantity"></Column>
            </DataTable>
        </template>
    </Inplace>
</template>

<script setup>
import { ref } from "vue";
import { ProductService } from "@/service/ProductService";

const products = ref(null);

const loadData = () => {
    ProductService.getProductsMini().then((data) => (products.value = data));
};
<\/script>
```

## Accessibility

Screen Reader Inplace component defines aria-live as "polite" by default, since any valid attribute is passed to the main container aria roles and attributes of the root element can be customized easily. Display element uses button role in view mode by default, displayProps can be used for customizations like adding aria-label or aria-labelledby attributes to describe the content of the view mode or even overriding the default role. Closable inplace components displays a button with an aria-label that refers to the aria.close property of the locale API by default, you may use closeButtonProps to customize the element and override the default aria-label . View Mode Keyboard Support Key Function enter Switches to content. Close Button Keyboard Support Key Function enter Switches to display. space Switches to display.

## Inplace API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| active | boolean | false | Whether the content is displayed or not. |
| disabled | boolean | false | When present, it specifies that the element should be disabled. |
| displayProps | HTMLAttributes | - | Used to pass all properties of the HTMLDivElement to display container. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | InplacePassThroughOptionType | Used to pass attributes to the root's DOM element. |
| display | InplacePassThroughOptionType | Used to pass attributes to the display's DOM element. |
| content | InplacePassThroughOptionType | Used to pass attributes to the content's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-inplace | Class name of the root element |
| p-inplace-display | Class name of the display element |
| p-inplace-content | Class name of the content element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| inplace.padding | --p-inplace-padding | Padding of root |
| inplace.border.radius | --p-inplace-border-radius | Border radius of root |
| inplace.focus.ring.width | --p-inplace-focus-ring-width | Focus ring width of root |
| inplace.focus.ring.style | --p-inplace-focus-ring-style | Focus ring style of root |
| inplace.focus.ring.color | --p-inplace-focus-ring-color | Focus ring color of root |
| inplace.focus.ring.offset | --p-inplace-focus-ring-offset | Focus ring offset of root |
| inplace.focus.ring.shadow | --p-inplace-focus-ring-shadow | Focus ring shadow of root |
| inplace.transition.duration | --p-inplace-transition-duration | Transition duration of root |
| inplace.display.hover.background | --p-inplace-display-hover-background | Hover background of display |
| inplace.display.hover.color | --p-inplace-display-hover-color | Hover color of display |
