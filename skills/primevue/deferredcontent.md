# DeferredContent

DeferredContent postpones the loading the content that is initially not in the viewport until it becomes visible on scroll.

## Basic

DeferredContent is used by wrapping the target.

```vue
<template>
    <div>
        <Toast />
        <div style="height: 1000px">Scroll down to lazy load an image.</div>

        <DeferredContent @load="onImageLoad">
            <img src="https://primefaces.org/cdn/primevue/images/nature/nature4.jpg" alt="Nature" class="rounded-xl w-full md:w-96 block sm:mx-auto" />
        </DeferredContent>
    </div>
</template>

<script setup>
import { useToast } from 'primevue/usetoast';

const toast = useToast();

const onImageLoad = () => {
    toast.add({ severity: 'success', summary: 'Success', detail: 'Image loaded', life: 2000 });
};
<\/script>
```

## DataTable

A practical example that triggers a fetch when the table becomes visible in viewport.

```vue
<template>
    <div>
        <Toast />
        <div style="height: 800px">Scroll down to lazy load a DataTable.</div>

        <DeferredContent @load="onDataLoad" role="region" aria-live="polite" aria-label="Content loaded after page scrolled down">
            <DataTable :value="products">
                <Column field="code" header="Code"></Column>
                <Column field="name" header="Name"></Column>
                <Column field="category" header="Category"></Column>
                <Column field="quantity" header="Quantity"></Column>
            </DataTable>
        </DeferredContent>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import { ProductService } from '@/service/ProductService';

const products = ref(null);

const onDataLoad = () => {
    ProductService.getProductsSmall().then((data) => (products.value = data));
    toast.add({ severity: 'success', summary: 'Data Initialized', detail: 'Render Completed', life: 2000 });
};
<\/script>
```

## Accessibility

Screen Reader DeferredContent can be utilized in many use cases as a result no role is enforced, in fact a role may not be necessary if the card is used for presentational purposes only. Any valid attribute is passed to the container element so you have full control over the roles like landmark and attributes like aria-live . Keyboard Support Component does not include any interactive elements.

```vue
<template>
    <DeferredContent role="region" aria-live="polite" aria-label="Content loaded after page scrolled down">
        Content
    </DeferredContent>
</template>
```

## Deferred Content API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | DeferredContentPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming
