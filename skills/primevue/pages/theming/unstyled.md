# Unstyled Mode

Theming PrimeVue with alternative styling approaches.

## Architecture

The term unstyled is used to define an alternative styling approach instead of the default theming with design tokens. In unstyled mode the css variables of the design tokens and the css rule sets that utilize them are not included. Here is an example of an Unstyled Select, the core functionality and accessibility is provided whereas styling is not included. Unstyled components still need to be styled on your end, in the next sections, we'll cover the styling solutions for both modes.

## Setup

Unstyled mode is enabled for the whole suite by enabling unstyled option during PrimeVue installation. Alternatively even in the default styled mode, a particular component can still be used as unstyled by adding the unstyled prop of the component. Check

## Example

Here is a sample that styles a button component with Tailwind CSS using pass through attributes. Before beginning, head over to the pass through section at button documentation to learn more about the components internals section. We'll style the root element with pass through attributes, and apply utility classes directly to the icon and label placed in the default slot. Search

```vue
<template>
    <Button unstyled pt:root="bg-teal-500 hover:bg-teal-700 active:bg-teal-900 cursor-pointer py-2 px-4 rounded-full border-0 flex items-center gap-2">
        <Search class="text-white" :size="20" />
        <span class="text-white font-bold text-lg">Search</span>
    </Button>
</template>

<script setup>
import Search from '@primeicons/vue/search';
<\/script>
```

## Global

A global configuration can be created at application level to avoid repetition via the global pt option so that the styles can be shared from a single location. A particular component can still override a global configuration with its own pt property.

```vue
import { createApp } from "vue";
import PrimeVue from "primevue/config";
const app = createApp(App);

app.use(PrimeVue, {
    unstyled: true,
    pt: {
        button: {
            root: 'bg-teal-500 hover:bg-teal-700 active:bg-teal-900 cursor-pointer py-2 px-4 rounded-full border-0 flex gap-2',
            label: 'text-white font-bold text-lg',
            icon: 'text-white text-xl'
        },
        panel: {
            header: 'bg-primary text-primary-contrast border-primary',
            content: 'border-primary text-lg text-primary-700',
            title: 'bg-primary text-primary-contrast text-xl',
            pcToggleButton: {
                root: 'bg-primary text-primary-contrast hover:text-primary hover:bg-primary-contrast'
            }
        }
    }
});
```
