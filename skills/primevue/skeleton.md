# Skeleton

Skeleton is a placeholder to display instead of the actual content.

## Basic

Placeholder shapes that mimic content layout during loading.

```vue
<template>
    <div class="flex gap-4 max-w-xs mx-auto">
        <Skeleton shape="circle" size="2.5rem" />
        <div class="flex-1 flex flex-col gap-1.5 py-0.5">
            <Skeleton width="100%" borderRadius="4px" class="h-auto! flex-1" />
            <Skeleton width="90%" borderRadius="4px" class="h-auto! flex-1" />
        </div>
    </div>
</template>

<script setup>
import Skeleton from 'primevue/skeleton';
<\/script>
```

## Card

Sample Card implementation using different Skeleton components and Tailwind CSS utilities.

```vue
<template>
    <div class="flex items-center justify-center">
        <div class="max-w-sm w-full space-y-4">
            <div class="flex items-start gap-4">
                <Skeleton shape="circle" size="3.5rem" />
                <div class="flex-1">
                    <div class="flex items-center justify-between">
                        <Skeleton width="40%" height="1.5rem" />
                    </div>
                    <div class="space-y-1.5 mt-3">
                        <Skeleton width="100%" borderRadius="4px" />
                        <Skeleton width="90%" borderRadius="4px" />
                    </div>
                    <Skeleton class="mt-4 aspect-video w-full h-auto!" />
                    <div class="flex items-center gap-4 mt-4">
                        <Skeleton width="4rem" height="1.75rem" />
                        <Skeleton width="4rem" height="1.75rem" />
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import Skeleton from 'primevue/skeleton';
<\/script>
```

## Shapes

Various shapes and sizes can be created using styling properties like shape , width , height , borderRadius and class .

```vue
<template>
    <div class="flex flex-col items-start gap-8 max-w-sm">
        <div class="w-full">
            <h5>Circle</h5>
            <div class="flex items-end gap-4">
                <Skeleton shape="circle" size="5rem" />
                <Skeleton shape="circle" size="4rem" />
                <Skeleton shape="circle" size="3rem" />
                <Skeleton shape="circle" size="2rem" />
            </div>
        </div>
        <div class="w-full">
            <h5>Square</h5>
            <div class="flex items-end gap-4">
                <Skeleton size="5rem" />
                <Skeleton size="4rem" />
                <Skeleton size="3rem" />
                <Skeleton size="2rem" />
            </div>
        </div>
        <div class="w-full">
            <h5>Rectangle</h5>
            <div class="flex flex-col gap-2 w-full">
                <Skeleton />
                <Skeleton width="12rem" />
                <Skeleton width="7rem" />
                <Skeleton height="4rem" />
                <Skeleton width="12rem" height="4rem" />
            </div>
        </div>
        <div class="w-full">
            <h5>Rounded</h5>
            <div class="flex flex-col gap-2 w-full">
                <Skeleton borderRadius="16px" />
                <Skeleton width="12rem" borderRadius="16px" />
                <Skeleton width="7rem" borderRadius="16px" />
                <Skeleton height="4rem" borderRadius="16px" />
                <Skeleton width="12rem" height="4rem" borderRadius="16px" />
            </div>
        </div>
    </div>
</template>

<script setup>
import Skeleton from 'primevue/skeleton';
<\/script>
```

## Color

Customize the background color of the skeleton.

```vue
<template>
    <div class="flex items-center justify-center">
        <div class="max-w-sm w-full space-y-4">
            <Skeleton borderRadius="4px" class="bg-blue-500! dark:bg-blue-700!" />
            <Skeleton borderRadius="4px" class="bg-red-500! dark:bg-red-700!" />
            <Skeleton
                borderRadius="4px"
                class="bg-blue-100! dark:bg-blue-950! after:bg-[linear-gradient(90deg,rgba(255,255,255,0.01)_0%,oklch(0.82_0.18_260)_50%,rgba(255,255,255,0.01)_100%)] dark:after:bg-[linear-gradient(90deg,rgba(255,255,255,0)_0%,oklch(0.42_0.18_260)_50%,rgba(255,255,255,0)_100%)]"
            />
            <Skeleton
                borderRadius="4px"
                class="bg-red-100! dark:bg-red-950! after:bg-[linear-gradient(90deg,rgba(255,255,255,0.01)_0%,oklch(63.7%_0.237_25.331)_50%,rgba(255,255,255,0.01)_100%)] dark:after:bg-[linear-gradient(90deg,rgba(255,255,255,0)_0%,oklch(63.7%_0.237_25.331)_50%,rgba(255,255,255,0)_100%)]"
            />
        </div>
    </div>
</template>

<script setup>
import Skeleton from 'primevue/skeleton';
<\/script>
```

## Grid

Sample Grid implementation using different Skeleton components and Tailwind CSS utilities.

```vue
<template>
    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-8">
        <div v-for="(item, index) in items" :key="index" class="p-4 rounded-lg bg-surface-50 dark:bg-surface-800/75">
            <Skeleton width="100%" height="10rem" />
            <div class="mt-4 flex items-start gap-3">
                <Skeleton shape="circle" size="2.5rem" />
                <div class="flex-1 flex flex-col gap-2">
                    <Skeleton width="100%" borderRadius="4px" />
                    <Skeleton width="90%" borderRadius="4px" />
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue';
import Skeleton from 'primevue/skeleton';

const items = ref(Array.from({ length: 6 }));
<\/script>
```

## List

Sample List implementation using different Skeleton components and Tailwind CSS utilities.

```vue
<template>
    <div class="rounded-sm border border-surface-200 dark:border-surface-700 p-6 bg-surface-0 dark:bg-surface-900">
        <ul class="m-0 p-0 list-none">
            <li class="mb-4">
                <div class="flex">
                    <Skeleton shape="circle" size="4rem" class="mr-2" />
                    <div class="self-center" style="flex: 1">
                        <Skeleton width="100%" class="mb-2" />
                        <Skeleton width="75%" />
                    </div>
                </div>
            </li>
            <li class="mb-4">
                <div class="flex">
                    <Skeleton shape="circle" size="4rem" class="mr-2" />
                    <div class="self-center" style="flex: 1">
                        <Skeleton width="100%" class="mb-2" />
                        <Skeleton width="75%" />
                    </div>
                </div>
            </li>
            <li class="mb-4">
                <div class="flex">
                    <Skeleton shape="circle" size="4rem" class="mr-2" />
                    <div class="self-center" style="flex: 1">
                        <Skeleton width="100%" class="mb-2" />
                        <Skeleton width="75%" />
                    </div>
                </div>
            </li>
            <li>
                <div class="flex">
                    <Skeleton shape="circle" size="4rem" class="mr-2" />
                    <div class="self-center" style="flex: 1">
                        <Skeleton width="100%" class="mb-2" />
                        <Skeleton width="75%" />
                    </div>
                </div>
            </li>
        </ul>
    </div>
</template>

<script setup>
import Skeleton from 'primevue/skeleton';
<\/script>
```

## DataTable

Sample DataTable implementation using different Skeleton components and Tailwind CSS utilities.

```vue
<template>
    <DataTable :value="products" :tableStyle="{ 'min-width': '50rem' }">
        <Column header="Code">
            <template #body>
                <Skeleton />
            </template>
        </Column>
        <Column header="Name">
            <template #body>
                <Skeleton />
            </template>
        </Column>
        <Column header="Category">
            <template #body>
                <Skeleton />
            </template>
        </Column>
        <Column header="Quantity">
            <template #body>
                <Skeleton />
            </template>
        </Column>
    </DataTable>
</template>

<script setup>
import { ref } from 'vue';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Skeleton from 'primevue/skeleton';

const products = ref(Array.from({ length: 5 }).map((_, i) => \`Item #\${i}\`));
<\/script>
```

## Accessibility

Screen Reader Skeleton uses aria-hidden as "true" so that it gets ignored by screen readers, any valid attribute is passed to the root element so you may customize it further if required. If multiple skeletons are grouped inside a container, you may use aria-busy on the container element as well to indicate the loading process. Keyboard Support Component does not include any interactive elements.

## Skeleton API

### Props

| Name |Type |Default |Description |
| --- | --- | --- | --- |
| shape | any | rectangle | Shape of the element. |
| size | string | - | Size of the Circle or Square. |
| width | string | 100% | Width of the element. |
| height | string | 1rem | Height of the element. |
| borderRadius | string | - | Border radius of the element, defaults to value from theme. |
| animation | any | wave | Type of the animation. |
| dt | any | - | It generates scoped CSS variables using design tokens for the component. |
| pt | any | - | Used to pass attributes to DOM elements inside the component. |
| ptOptions | any | - | Used to configure passthrough(pt) options of the component. |
| unstyled | boolean | false | When enabled, it removes component related styles in the core. |

### Pass Through Options

| Name |Type |Description |
| --- | --- | --- |
| root | SkeletonPassThroughOptionType | Used to pass attributes to the root's DOM element. |
| hooks | any | Used to manage all lifecycle hooks. |

### Theming

### CSS Classes

| Class |Description |
| --- | --- |
| p-skeleton | Class name of the root element |

### Design Tokens

| Token |CSS Variable |Description |
| --- | --- | --- |
| skeleton.border.radius | --p-skeleton-border-radius | Border radius of root |
| skeleton.background | --p-skeleton-background | Background of root |
| skeleton.animation.background | --p-skeleton-animation-background | Animation background of root |
