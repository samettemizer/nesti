# Fluid

Fluid is a layout component to make descendant components span full width of their container.

## Basic

Components with the fluid option like InputText have the ability to span the full width of their component. Enabling the fluid for each component individually may be cumbersome so wrap the content with Fluid instead for an easier alternative.

```vue
<template>
    <div>
        <Fluid>
            <Label for="with-fluid" class="font-bold! mb-2 block">With Fluid</Label>
            <InputText id="with-fluid" placeholder="Type..." />
        </Fluid>
    </div>
</template>

<script setup>
import Fluid from 'primevue/fluid';
import InputText from 'primevue/inputtext';
import Label from 'primevue/label';
<\/script>
```

## Comparison

The fluid property can be enabled per component, or applied to a group of components by wrapping them with Fluid . A child component's own fluid property takes precedence over the container, as shown in the last sample.

```vue
<template>
    <div class="flex flex-col gap-6">
        <div>
            <Label for="non-fluid" class="font-bold! mb-2 block">Non-Fluid</Label>
            <InputText id="non-fluid" />
        </div>

        <div>
            <Label for="fluid" class="font-bold! mb-2 block">Fluid Prop</Label>
            <InputText id="fluid" fluid />
        </div>

        <Fluid>
            <span class="font-bold mb-2 block">Fluid Container</span>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <InputText />
                </div>
                <div>
                    <InputText />
                </div>
                <div class="col-span-full">
                    <InputText />
                </div>
                <div>
                    <InputText :fluid="false" placeholder="Non-Fluid" />
                </div>
            </div>
        </Fluid>
    </div>
</template>

<script setup>
import Fluid from 'primevue/fluid';
import InputText from 'primevue/inputtext';
import Label from 'primevue/label';
<\/script>
```

## Accessibility

Screen Reader Fluid does not require any roles and attributes. Keyboard Support Component does not include any interactive elements.

## Fluid API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Slots

| Name |Parameters |Description |
| --- | --- | --- |
| default | Function |  |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | FluidPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-fluid | Class name of the root element |
